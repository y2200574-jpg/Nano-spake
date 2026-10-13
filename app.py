import os
import re
import sqlite3
import secrets
import json
import urllib.request
import urllib.error
from datetime import datetime
from functools import wraps
from flask import Flask, request, redirect, url_for, session, render_template_string, flash, g, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

# NEON SPACE - a mobile-friendly Flask website
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "users.db")
SECRET_FILE = os.path.join(BASE_DIR, ".neon_secret_key")
AI_KEY_FILE = os.path.join(BASE_DIR, "gemini_key.txt")
AI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")


def load_secret_key():
    """Keep the session key stable between app restarts on this device."""
    env_key = os.environ.get("FLASK_SECRET_KEY")
    if env_key:
        return env_key
    try:
        if os.path.isfile(SECRET_FILE):
            with open(SECRET_FILE, "r", encoding="utf-8") as f:
                key = f.read().strip()
                if len(key) >= 32:
                    return key
        key = secrets.token_hex(32)
        with open(SECRET_FILE, "w", encoding="utf-8") as f:
            f.write(key)
        return key
    except OSError:
        # Fallback for read-only folders. Sessions won't survive a full restart.
        return secrets.token_hex(32)


app = Flask(__name__)
app.config.update(
    SECRET_KEY=load_secret_key(),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    MAX_CONTENT_LENGTH=32 * 1024,
    PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 14,
)

PAGE = r'''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#080b18"><meta name="csrf-token" content="{{ csrf_token() }}"><title>{{ title }} | NEON SPACE</title>
<style>
:root{color-scheme:dark;--bg:#080b18;--panel:#10172b;--panel2:#0b1122;--cyan:#48f2ff;--pink:#ff4bd8;--purple:#a17aff;--muted:#a7b4d2;--line:rgba(93,220,255,.2);--good:#6dffc2}
*{box-sizing:border-box}html{min-height:100%;background:var(--bg)}body{margin:0;min-height:100vh;font-family:system-ui,-apple-system,"Segoe UI",Tahoma,sans-serif;color:#f4f7ff;background:radial-gradient(ellipse at 12% 10%,rgba(125,56,255,.18),transparent 35%),radial-gradient(ellipse at 92% 80%,rgba(0,222,255,.12),transparent 38%),var(--bg);overflow-x:hidden}
body:before,body:after{content:"";position:fixed;width:270px;height:270px;border-radius:50%;filter:blur(80px);opacity:.16;pointer-events:none;z-index:0;animation:glow 10s ease-in-out infinite alternate}body:before{background:#913dff;top:-110px;right:-90px}body:after{background:#00dcff;bottom:-120px;left:-80px;animation-delay:-4s}
.grid{position:fixed;inset:0;z-index:0;pointer-events:none;opacity:.14;background-image:linear-gradient(rgba(76,181,255,.14) 1px,transparent 1px),linear-gradient(90deg,rgba(76,181,255,.14) 1px,transparent 1px);background-size:36px 36px;mask-image:linear-gradient(to bottom,#000,transparent 95%)}
a{color:inherit}.shell{position:relative;z-index:1;width:min(1160px,100%);margin:auto;padding:18px 16px 34px}.topbar{display:flex;align-items:center;justify-content:space-between;gap:14px;padding:10px 2px 22px}.brand{display:flex;align-items:center;gap:11px;text-decoration:none}.brand-mark{width:44px;height:44px;display:grid;place-items:center;border:1px solid rgba(72,242,255,.6);border-radius:15px;color:var(--cyan);font-size:23px;text-shadow:0 0 14px var(--cyan);box-shadow:0 0 22px rgba(72,242,255,.13),inset 0 0 15px rgba(72,242,255,.09);animation:pulse 3s infinite}.brand-name{font-weight:900;letter-spacing:1.8px;font-size:17px}.brand-name span{color:var(--cyan)}.brand-tag{font-size:11px;color:var(--muted);margin-top:2px}.top-actions{display:flex;align-items:center;gap:10px}.user-chip,.pill{border:1px solid var(--line);background:rgba(14,24,47,.75);border-radius:999px;padding:9px 13px;font-size:12px;color:#dce7ff}.user-chip b{color:var(--cyan)}.nav{display:flex;gap:7px;flex-wrap:wrap;border:1px solid var(--line);border-radius:17px;background:rgba(10,17,35,.72);padding:7px;margin-bottom:22px}.nav a{font-size:13px;color:var(--muted);text-decoration:none;padding:10px 14px;border-radius:11px;transition:.2s}.nav a:hover,.nav a.active{background:rgba(72,242,255,.1);color:var(--cyan);box-shadow:inset 0 0 0 1px rgba(72,242,255,.13)}
.card{position:relative;border:1px solid var(--line);border-radius:24px;background:linear-gradient(145deg,rgba(17,27,53,.92),rgba(8,14,30,.93));box-shadow:0 20px 60px rgba(0,0,0,.27),0 0 28px rgba(39,211,255,.045);overflow:hidden;animation:enter .5s ease both}.card:before{content:"";position:absolute;top:0;right:12%;left:12%;height:1px;background:linear-gradient(90deg,transparent,var(--cyan),var(--pink),transparent)}.pad{padding:25px}.eyebrow{color:var(--cyan);font-size:11px;letter-spacing:1.8px;font-weight:850;margin:0 0 9px}.title{font-size:clamp(23px,4vw,34px);line-height:1.35;margin:0 0 8px}.muted{color:var(--muted);line-height:1.9;font-size:13px}.flash{border:1px solid rgba(255,80,140,.4);background:rgba(255,50,110,.1);color:#ffd8e5;border-radius:12px;padding:11px 13px;font-size:13px;margin:0 0 14px}.flash.ok{border-color:rgba(72,242,255,.3);color:#c8fcff;background:rgba(72,242,255,.07)}
.auth-layout{min-height:calc(100vh - 70px);display:grid;place-items:center}.auth-wrap{width:min(100%,470px)}.auth-brand{text-align:center;margin-bottom:20px}.auth-brand .brand-mark{margin:0 auto 12px;width:60px;height:60px;font-size:29px;border-radius:20px}.auth-brand h1{font-size:23px;margin:0;letter-spacing:3px}.auth-brand h1 span{color:var(--cyan)}.auth-brand p{color:var(--muted);font-size:13px;margin:8px 0 0}.field{margin:15px 0}.field label{display:block;font-size:13px;color:#dce6ff;margin-bottom:8px}.input-wrap{position:relative}.field input{width:100%;height:49px;border:1px solid rgba(142,164,221,.23);border-radius:13px;background:rgba(4,9,23,.65);color:#fff;padding:0 14px;outline:none;font:inherit;font-size:14px;transition:.2s}.field input:focus{border-color:var(--cyan);box-shadow:0 0 0 3px rgba(72,242,255,.09)}.field input::placeholder{color:#6c7898}.toggle{position:absolute;left:8px;top:7px;border:0;background:transparent;color:var(--muted);height:35px;padding:0 8px;cursor:pointer;font:inherit;font-size:12px}.btn{min-height:47px;display:inline-flex;align-items:center;justify-content:center;gap:8px;border:1px solid rgba(72,242,255,.62);border-radius:13px;background:linear-gradient(100deg,rgba(0,209,232,.16),rgba(153,73,255,.2));color:#f8ffff;text-decoration:none;font:inherit;font-size:13px;font-weight:800;padding:12px 17px;cursor:pointer;transition:transform .18s,box-shadow .2s}.btn:hover{transform:translateY(-2px);box-shadow:0 0 23px rgba(72,242,255,.15)}.btn.full{width:100%;margin-top:10px}.btn.secondary{border-color:rgba(158,177,220,.22);background:rgba(255,255,255,.035);color:#dce6ff}.btn.danger{border-color:rgba(255,92,142,.4);color:#ffc5d8;background:rgba(255,60,120,.07)}.switch{text-align:center;color:var(--muted);font-size:13px;margin:19px 0 0}.switch a,.link{color:var(--cyan);text-decoration:none;font-weight:750}.fine{text-align:center;color:#7280a5;font-size:11px;margin-top:18px}
.hero{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(220px,.8fr);gap:20px;align-items:stretch}.hero-copy{padding:29px}.hero-copy .title span{color:var(--cyan);text-shadow:0 0 23px rgba(72,242,255,.18)}.hero-art{display:grid;place-items:center;min-height:250px;position:relative;background:radial-gradient(ellipse,rgba(72,242,255,.1),transparent 65%)}.hero-art:before,.hero-art:after{content:"";position:absolute;border:1px solid rgba(72,242,255,.16);border-radius:50%;width:180px;height:180px;animation:orbit 16s linear infinite}.hero-art:after{width:225px;height:225px;border-color:rgba(255,75,216,.12);animation-direction:reverse;animation-duration:22s}.robot{position:relative;width:118px;height:135px;z-index:1;animation:botfloat 3s ease-in-out infinite;filter:drop-shadow(0 0 22px rgba(72,242,255,.2))}.robot-head{position:absolute;top:12px;left:16px;width:86px;height:68px;border:2px solid #6ef5ff;border-radius:25px 25px 29px 29px;background:linear-gradient(145deg,#263e69,#111b36);box-shadow:inset 0 0 19px rgba(72,242,255,.17),0 0 18px rgba(72,242,255,.18)}.robot-head:before{content:"";position:absolute;left:19px;top:25px;width:11px;height:13px;border-radius:50%;background:var(--cyan);box-shadow:0 0 12px var(--cyan),31px 0 0 var(--cyan),31px 0 12px var(--cyan);animation:eyes 4s infinite}.robot-mouth{position:absolute;left:31px;bottom:10px;width:22px;height:5px;border-radius:9px;background:#ff6bdd;box-shadow:0 0 9px #ff6bdd}.robot-ear{position:absolute;top:34px;width:12px;height:23px;border:2px solid var(--pink);border-radius:7px;background:#18213e}.robot-ear.left{left:5px}.robot-ear.right{right:5px}.robot-body{position:absolute;left:32px;bottom:0;width:54px;height:53px;border:2px solid #6ef5ff;border-radius:18px 18px 14px 14px;background:linear-gradient(145deg,#263e69,#10182d)}.robot-core{position:absolute;left:17px;top:15px;width:16px;height:16px;border:2px solid var(--pink);border-radius:50%;box-shadow:0 0 14px rgba(255,75,216,.6);animation:pulse 2s infinite}.robot-arm{position:absolute;top:78px;width:13px;height:36px;border:2px solid #6ef5ff;border-radius:9px;background:#1a2949;transform-origin:top center}.robot-arm.left{left:20px;transform:rotate(18deg);animation:wave 2.8s infinite}.robot-arm.right{right:18px;transform:rotate(-17deg)}.assistant-label{position:absolute;bottom:18px;z-index:2;background:rgba(7,15,32,.85);border:1px solid var(--line);padding:7px 12px;border-radius:99px;font-size:11px;color:var(--cyan)}
.section-title{font-size:17px;margin:0 0 15px}.stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:13px;margin:18px 0}.stat{padding:18px;border:1px solid var(--line);border-radius:18px;background:rgba(12,21,42,.72)}.stat .ico{font-size:20px;margin-bottom:11px}.stat strong{display:block;font-size:18px;margin-bottom:4px}.stat span{font-size:12px;color:var(--muted)}.content-grid{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(250px,.8fr);gap:18px}.feature-list{display:grid;gap:10px}.feature{display:flex;align-items:center;gap:12px;padding:14px;border:1px solid rgba(135,162,220,.14);border-radius:15px;background:rgba(7,13,28,.4)}.feature-icon{width:42px;height:42px;flex:0 0 42px;border:1px solid var(--line);border-radius:13px;display:grid;place-items:center;color:var(--cyan);background:rgba(72,242,255,.06);font-size:18px}.feature b{font-size:13px;display:block;margin-bottom:4px}.feature small{font-size:11px;color:var(--muted);line-height:1.6}.profile-row{display:flex;align-items:center;gap:16px;margin:15px 0 22px}.profile-avatar{width:64px;height:64px;border-radius:20px;display:grid;place-items:center;font-size:27px;border:1px solid var(--line);background:linear-gradient(135deg,rgba(72,242,255,.12),rgba(255,75,216,.12));color:var(--cyan)}.info-line{display:flex;justify-content:space-between;gap:12px;padding:13px 0;border-bottom:1px solid rgba(130,158,214,.12);font-size:13px}.info-line span{color:var(--muted)}.info-line b{overflow-wrap:anywhere}.empty-note{padding:17px;border:1px dashed rgba(72,242,255,.22);border-radius:15px;color:var(--muted);font-size:13px;line-height:1.8}
.assistant-launch{position:fixed;z-index:5;bottom:18px;left:17px;width:60px;height:60px;border-radius:22px;border:1px solid rgba(72,242,255,.7);background:linear-gradient(145deg,#172d50,#11152d);box-shadow:0 0 24px rgba(72,242,255,.22);display:grid;place-items:center;cursor:pointer;animation:botfloat 3s ease-in-out infinite}.assistant-launch .mini-bot{position:relative;width:32px;height:35px;border:1.5px solid var(--cyan);border-radius:11px;background:#172743}.mini-bot:before{content:"";position:absolute;top:11px;left:6px;width:5px;height:6px;background:var(--cyan);border-radius:50%;box-shadow:12px 0 var(--cyan),0 0 7px var(--cyan)}.mini-bot:after{content:"";position:absolute;bottom:5px;left:11px;width:8px;height:2px;border-radius:4px;background:var(--pink)}.assistant-panel{display:none;position:fixed;z-index:20;left:12px;bottom:82px;width:min(360px,calc(100vw - 24px));max-height:calc(100vh - 100px);max-height:calc(100dvh - 100px);border:1px solid rgba(72,242,255,.3);border-radius:20px;background:rgba(9,16,35,.98);box-shadow:0 18px 60px rgba(0,0,0,.5),0 0 24px rgba(72,242,255,.08);overflow:hidden;backdrop-filter:blur(18px);flex-direction:column}.assistant-panel.open{display:flex;animation:enter .2s ease}.assistant-head{display:flex;align-items:center;gap:10px;padding:14px;border-bottom:1px solid var(--line);background:rgba(72,242,255,.05);flex:0 0 auto}.assistant-head .mini-bot{flex:0 0 32px}.assistant-head b{font-size:13px}.assistant-head small{display:block;color:var(--good);font-size:10px;margin-top:3px}.assistant-close{margin-right:auto;border:0;background:transparent;color:var(--muted);font-size:21px;cursor:pointer}.chat-log{padding:13px;flex:1 1 auto;min-height:70px;max-height:none;overflow:auto;display:grid;align-content:start;gap:9px}.bubble{font-size:12px;line-height:1.8;padding:10px 12px;border-radius:13px;max-width:92%;overflow-wrap:anywhere}.bubble.bot{background:rgba(72,242,255,.08);border:1px solid rgba(72,242,255,.12);justify-self:start}.bubble.me{background:rgba(161,122,255,.13);border:1px solid rgba(161,122,255,.18);justify-self:end}.quick-questions{display:flex;flex-wrap:wrap;gap:6px;padding:0 13px 10px;flex:0 0 auto;max-height:100px;overflow:auto}.quick-questions button{font:inherit;font-size:11px;color:var(--cyan);background:rgba(72,242,255,.05);border:1px solid rgba(72,242,255,.2);border-radius:99px;padding:7px 9px;cursor:pointer}.chat-compose{display:flex;gap:7px;padding:10px 12px max(13px,env(safe-area-inset-bottom));border-top:1px solid var(--line);flex:0 0 auto;background:rgba(9,16,35,.98)}.chat-compose textarea{flex:1;min-width:0;resize:vertical;min-height:43px;max-height:110px;border:1px solid rgba(142,164,221,.25);border-radius:12px;background:#070d1d;color:#fff;padding:10px;font:inherit;font-size:12px;outline:none}.chat-compose textarea:focus{border-color:var(--cyan)}.chat-compose button{border:1px solid rgba(72,242,255,.5);border-radius:12px;padding:0 13px;background:rgba(72,242,255,.1);color:var(--cyan);font:inherit;font-weight:800;cursor:pointer}.chat-compose button:disabled{opacity:.5;cursor:wait}.footer{text-align:center;color:#637295;font-size:10px;padding:25px 0 4px}
@keyframes glow{to{transform:translate(12px,-12px) scale(1.08)}}@keyframes pulse{0%,100%{box-shadow:0 0 17px rgba(72,242,255,.13)}50%{box-shadow:0 0 27px rgba(72,242,255,.29)}}@keyframes enter{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}@keyframes botfloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-8px)}}@keyframes orbit{to{transform:rotate(360deg)}}@keyframes eyes{0%,45%,49%,100%{transform:scaleY(1)}47%{transform:scaleY(.12)}}@keyframes wave{0%,100%{transform:rotate(18deg)}50%{transform:rotate(48deg)}}
@media(max-width:760px){.shell{padding:12px 12px 25px}.hero{grid-template-columns:1fr}.hero-art{min-height:205px;grid-row:1}.hero-copy{padding:22px}.content-grid{grid-template-columns:1fr}.stats{gap:8px}.stat{padding:13px}.stat strong{font-size:16px}.topbar{align-items:flex-start}.user-chip{display:none}.nav{gap:3px}.nav a{padding:9px 10px;font-size:12px}.pad{padding:20px}.assistant-launch{width:55px;height:55px;left:12px;bottom:12px}}
@media(max-width:390px){.stats{grid-template-columns:1fr}.stat{display:flex;align-items:center;gap:12px}.stat .ico{margin:0}.top-actions .btn{padding:9px 11px}.brand-name{font-size:15px}}
@media(prefers-reduced-motion:reduce){*,*:before,*:after{animation:none!important;transition:none!important}}
</style></head><body><div class="grid"></div>
{% if page in ['login','register'] %}
<main class="shell auth-layout"><div class="auth-wrap"><header class="auth-brand"><div class="brand-mark">✦</div><h1>NEON <span>SPACE</span></h1><p>مساحتك الرقمية — ابدأ من هنا</p></header><section class="card pad">
{% with messages = get_flashed_messages(with_categories=true) %}{% for category,message in messages %}<div class="flash {{ 'ok' if category == 'ok' else '' }}">{{ message }}</div>{% endfor %}{% endwith %}
{% if page == 'login' %}<p class="eyebrow">SECURE ACCESS</p><h2 class="title">رجعت تنوّر المكان 👋</h2><p class="muted">سجّل دخولك حتى تفتح مساحتك الخاصة.</p>
<form method="post" action="{{ url_for('login') }}" autocomplete="on"><input type="hidden" name="csrf_token" value="{{ csrf_token() }}"><div class="field"><label for="username">اسم المستخدم</label><input id="username" name="username" type="text" minlength="3" maxlength="24" autocomplete="username" placeholder="اسم المستخدم" required autofocus></div><div class="field"><label for="password">كلمة المرور</label><div class="input-wrap"><input id="password" name="password" type="password" minlength="8" maxlength="128" autocomplete="current-password" placeholder="كلمة المرور" required><button class="toggle" type="button" data-toggle="password">إظهار</button></div></div><button class="btn full" type="submit">دخول إلى مساحتي　↗</button></form><p class="switch">أول مرة هنا؟ <a href="{{ url_for('register') }}">أنشئ حساب جديد</a></p>
{% else %}<p class="eyebrow">CREATE ACCOUNT</p><h2 class="title">خلّينا نبدي ✨</h2><p class="muted">أنشئ حسابك حتى تحفظ دخولك وملفك الشخصي.</p><form method="post" action="{{ url_for('register') }}" autocomplete="on"><input type="hidden" name="csrf_token" value="{{ csrf_token() }}"><div class="field"><label for="username">اسم المستخدم</label><input id="username" name="username" type="text" minlength="3" maxlength="24" pattern="[A-Za-z0-9_]+" autocomplete="username" placeholder="إنكليزي أو أرقام أو _" required autofocus></div><div class="field"><label for="password">كلمة المرور</label><div class="input-wrap"><input id="password" name="password" type="password" minlength="8" maxlength="128" autocomplete="new-password" placeholder="8 أحرف على الأقل" required><button class="toggle" type="button" data-toggle="password">إظهار</button></div></div><div class="field"><label for="confirm_password">تأكيد كلمة المرور</label><div class="input-wrap"><input id="confirm_password" name="confirm_password" type="password" minlength="8" maxlength="128" autocomplete="new-password" placeholder="أعد كتابة كلمة المرور" required><button class="toggle" type="button" data-toggle="confirm_password">إظهار</button></div></div><button class="btn full" type="submit">إنشاء حسابي　✦</button></form><p class="switch">عندك حساب؟ <a href="{{ url_for('login') }}">سجّل دخولك</a></p>{% endif %}<div class="fine">🔒 حماية للجلسة · NEON SPACE</div></section></div></main>
{% else %}
<div class="shell"><header class="topbar"><a class="brand" href="{{ url_for('dashboard') }}"><div class="brand-mark">✦</div><div><div class="brand-name">NEON <span>SPACE</span></div><div class="brand-tag">مساحتك الرقمية الخاصة</div></div></a><div class="top-actions"><span class="user-chip">أهلاً <b>{{ username }}</b></span><form method="post" action="{{ url_for('logout') }}"><input type="hidden" name="csrf_token" value="{{ csrf_token() }}"><button class="btn secondary" type="submit">خروج ↗</button></form></div></header>
<nav class="nav"><a class="{{ 'active' if page == 'dashboard' else '' }}" href="{{ url_for('dashboard') }}">⌂ الرئيسية</a><a class="{{ 'active' if page == 'profile' else '' }}" href="{{ url_for('profile') }}">♙ ملفي الشخصي</a><a href="#assistant" onclick="openAssistant();return false;">✧ المساعد</a></nav>
{% with messages = get_flashed_messages(with_categories=true) %}{% for category,message in messages %}<div class="flash {{ 'ok' if category == 'ok' else '' }}">{{ message }}</div>{% endfor %}{% endwith %}
{% if page == 'dashboard' %}<section class="card hero"><div class="hero-copy"><p class="eyebrow">YOUR DIGITAL SPACE</p><h1 class="title">أهلاً بيك، <span>{{ username }}</span> ✨</h1><p class="muted">هنا تبدأ مساحتك الخاصة. حسابك محفوظ، وتكدر تتنقل بين صفحات الموقع وتراجع معلوماتك بأي وقت.</p><div style="display:flex;gap:9px;flex-wrap:wrap;margin-top:20px"><a class="btn" href="{{ url_for('profile') }}">عرض ملفي الشخصي　↗</a><button class="btn secondary" type="button" onclick="openAssistant()">احچي ويا المساعد ✧</button></div></div><div class="hero-art"><div class="robot"><div class="robot-ear left"></div><div class="robot-ear right"></div><div class="robot-head"><div class="robot-mouth"></div></div><div class="robot-body"><div class="robot-core"></div></div><div class="robot-arm left"></div><div class="robot-arm right"></div></div><div class="assistant-label">NOVA · مساعدك الرقمي</div></div></section>
<div class="stats"><div class="stat"><div class="ico">🛡️</div><div><strong>محمي</strong><span>كلمة المرور مشفّرة بالتجزئة</span></div></div><div class="stat"><div class="ico">💾</div><div><strong>محفوظ</strong><span>بياناتك في SQLite</span></div></div><div class="stat"><div class="ico">🟢</div><div><strong>نشط</strong><span>أنت مسجّل دخول حالياً</span></div></div></div>
<div class="content-grid"><section class="card pad"><h2 class="section-title">مساحتك بيها شنو؟</h2><div class="feature-list"><div class="feature"><div class="feature-icon">♙</div><div><b>ملفك الشخصي</b><small>شوف اسم المستخدم وتاريخ إنشاء الحساب.</small></div></div><div class="feature"><div class="feature-icon">🔐</div><div><b>حساب مستقل</b><small>تسجيل الدخول والخروج محميان برمز تحقق للطلبات.</small></div></div><div class="feature"><div class="feature-icon">✧</div><div><b>المساعد NOVA</b><small>اضغط على الروبوت أسفل الشاشة حتى يساعدك بالتنقل.</small></div></div></div></section><aside class="card pad"><p class="eyebrow">QUICK ACCESS</p><h2 class="section-title">اختصارات سريعة</h2><p class="muted">اختار الشي اللي تريد تسويه.</p><div class="feature-list"><a class="feature" href="{{ url_for('profile') }}" style="text-decoration:none"><div class="feature-icon">👤</div><div><b>معلومات الحساب</b><small>افتح صفحة ملفك الشخصي ←</small></div></a><button class="feature" onclick="openAssistant()" style="text-align:right;color:inherit;font:inherit;cursor:pointer;width:100%"><div class="feature-icon">💬</div><div><b>اسأل المساعد</b><small>تعرف على صفحات الموقع ←</small></div></button></div></aside></div>
{% else %}<section class="card pad"><p class="eyebrow">YOUR PROFILE</p><h1 class="title">ملفي الشخصي</h1><p class="muted">معلومات حسابك المحفوظة في الموقع.</p><div class="profile-row"><div class="profile-avatar">♙</div><div><h2 style="margin:0 0 5px;font-size:20px">{{ username }}</h2><span class="pill">عضو في NEON SPACE</span></div></div><div class="info-line"><span>اسم المستخدم</span><b>{{ username }}</b></div><div class="info-line"><span>تاريخ إنشاء الحساب</span><b>{{ created_at }}</b></div><div class="info-line"><span>حالة الحساب</span><b style="color:var(--good)">نشط</b></div><div style="margin-top:20px"><a class="btn secondary" href="{{ url_for('dashboard') }}">↩ العودة للرئيسية</a></div></section>{% endif %}
<footer class="footer">NEON SPACE · واجهة متجاوبة للموبايل والكمبيوتر</footer></div>
<button class="assistant-launch" id="assistant-launch" aria-label="فتح المساعد" onclick="openAssistant()"><span class="mini-bot"></span></button><section class="assistant-panel" id="assistant-panel" aria-label="المساعد الرقمي" aria-hidden="true"><header class="assistant-head"><span class="mini-bot"></span><div><b>NOVA · المساعد الرقمي</b><small>● موجود حتى يساعدك</small></div><button class="assistant-close" onclick="closeAssistant()" aria-label="إغلاق">×</button></header><div class="chat-log" id="chat-log"><div class="bubble bot">هلا {{ username }}! ✨ آني NOVA. اختار سؤال من الأسفل وأساعدك.</div></div><div class="quick-questions"><button onclick="askAssistant('اشرح لي شلون أتعلم البرمجة من الصفر')">تعلم البرمجة</button><button onclick="askAssistant('ساعدني أكتب كود بايثون')">كود بايثون</button><button onclick="askAssistant('اشرح لي موضوع علمي بطريقة بسيطة')">سؤال علمي</button><button onclick="askAssistant('شنو تكدر تسوي؟')">قدراتك</button></div><form class="chat-compose" id="chat-form"><textarea id="chat-input" maxlength="5000" rows="2" placeholder="اكتب سؤالك هنا..." aria-label="اكتب سؤالك"></textarea><button id="chat-send" type="submit">إرسال ↗</button></form></section>
{% endif %}
<script>
document.querySelectorAll('[data-toggle]').forEach(function(button){button.addEventListener('click',function(){var input=document.getElementById(button.dataset.toggle);if(!input)return;var show=input.type==='password';input.type=show?'text':'password';button.textContent=show?'إخفاء':'إظهار';});});
function openAssistant(){var p=document.getElementById('assistant-panel');if(p){p.classList.add('open');p.setAttribute('aria-hidden','false')}var i=document.getElementById('chat-input');if(i)setTimeout(function(){i.focus({preventScroll:true})},120)}
function closeAssistant(){var p=document.getElementById('assistant-panel');if(p){p.classList.remove('open');p.setAttribute('aria-hidden','true')}}
var novaHistory=[];
function addBubble(text,who){var log=document.getElementById('chat-log');var b=document.createElement('div');b.className='bubble '+who;b.textContent=text;log.appendChild(b);log.scrollTop=log.scrollHeight;return b}
async function sendToNova(text){text=(text||'').trim();if(!text)return;openAssistant();addBubble(text,'me');var input=document.getElementById('chat-input'),send=document.getElementById('chat-send');if(input)input.value='';if(send)send.disabled=true;var waiting=addBubble('NOVA يفكر...','bot');try{var r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':document.querySelector('meta[name="csrf-token"]')?.content||''},body:JSON.stringify({message:text,history:novaHistory})});var data=await r.json();waiting.remove();if(!r.ok)throw new Error(data.error||'تعذر الحصول على رد.');addBubble(data.reply,'bot');novaHistory.push({role:'user',content:text},{role:'assistant',content:data.reply});if(novaHistory.length>20)novaHistory=novaHistory.slice(-20)}catch(e){waiting.textContent=e.message||'صار خطأ بالاتصال. جرّب مرة ثانية.'}finally{if(send)send.disabled=false;if(input)input.focus()}}
function askAssistant(text){sendToNova(text)}
var chatForm=document.getElementById('chat-form');if(chatForm)chatForm.addEventListener('submit',function(e){e.preventDefault();sendToNova(document.getElementById('chat-input').value)});
var chatInput=document.getElementById('chat-input');if(chatInput)chatInput.addEventListener('keydown',function(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendToNova(chatInput.value)}});
</script></body></html>'''


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE, timeout=10)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create the current schema and safely migrate older versions of users.db.

    Older versions of this project may have required columns (for example email)
    that the current registration form does not submit. CREATE TABLE IF NOT EXISTS
    does not update an existing table, so those old schemas cause every signup to fail.
    A SQLite backup is made before changing an existing incompatible schema.
    """
    os.makedirs(BASE_DIR, exist_ok=True)
    with sqlite3.connect(DATABASE, timeout=15) as db:
        db.execute("PRAGMA busy_timeout = 15000")
        db.execute("PRAGMA journal_mode = WAL")
        table = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchone()
        if not table:
            db.execute("""CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                email TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
            db.commit()
            return

        info = db.execute("PRAGMA table_info(users)").fetchall()
        columns = {row[1]: row for row in info}
        # These columns are needed by the app. Legacy email fields are allowed,
        # but they must be nullable because this version's form doesn't ask for email.
        required = {"id", "username", "password_hash", "created_at"}
        incompatible = not required.issubset(columns)
        if "email" in columns and columns["email"][3] == 1:
            incompatible = True
        allowed = {"id", "username", "email", "password_hash", "created_at"}
        for row in info:
            col_name, not_null, default_value = row[1], row[3], row[4]
            if col_name not in allowed and not_null and default_value is None and row[5] == 0:
                incompatible = True

        if incompatible:
            # Back up the database through SQLite's backup API before migration.
            backup_path = DATABASE + ".backup"
            with sqlite3.connect(backup_path, timeout=15) as backup:
                db.backup(backup)
            old_columns = set(columns)
            if not {"username", "password_hash"}.issubset(old_columns):
                raise RuntimeError(
                    "قاعدة البيانات القديمة ما بيها حقول username و password_hash المطلوبة. "
                    "تم الاحتفاظ بنسخة احتياطية باسم users.db.backup؛ لا تحذفها."
                )
            db.execute("BEGIN IMMEDIATE")
            try:
                db.execute("ALTER TABLE users RENAME TO users_legacy_migration")
                db.execute("""CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    email TEXT UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )""")
                legacy_fields = ["id", "username"]
                new_fields = ["id", "username"]
                if "email" in old_columns:
                    legacy_fields.append("email")
                    new_fields.append("email")
                legacy_fields.append("password_hash")
                new_fields.append("password_hash")
                if "created_at" in old_columns:
                    legacy_fields.append("created_at")
                    new_fields.append("created_at")
                select_sql = ", ".join('"' + f + '"' for f in legacy_fields)
                insert_sql = ", ".join('"' + f + '"' for f in new_fields)
                db.execute(
                    f"INSERT INTO users ({insert_sql}) SELECT {select_sql} FROM users_legacy_migration"
                )
                db.execute("DROP TABLE users_legacy_migration")
                db.commit()
            except Exception:
                db.rollback()
                raise
        else:
            # Add the optional email field if a compatible older table lacks it.
            if "email" not in columns:
                db.execute("ALTER TABLE users ADD COLUMN email TEXT UNIQUE")
            db.commit()


def csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


app.jinja_env.globals["csrf_token"] = csrf_token


def valid_csrf():
    sent = request.form.get("csrf_token", "")
    if not sent and request.is_json:
        sent = request.headers.get("X-CSRF-Token", "")
    expected = session.get("csrf_token", "")
    return bool(sent and expected and secrets.compare_digest(sent, expected))


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("سجّل دخولك أولاً حتى تفتح هذه الصفحة.")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


@app.after_request
def security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.get("/")
def home():
    return redirect(url_for("dashboard" if session.get("user_id") else "login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if not valid_csrf():
            flash("انتهت صلاحية رمز الحماية. حدّث الصفحة وحاول مرة ثانية.")
            return redirect(url_for("register"))
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if not re.fullmatch(r"[A-Za-z0-9_]{3,24}", username):
            flash("اسم المستخدم لازم يكون 3–24 حرف إنكليزي أو رقم أو _. ")
        elif len(password) < 8 or len(password) > 128:
            flash("كلمة المرور لازم تكون من 8 إلى 128 حرف.")
        elif password != confirm:
            flash("كلمتا المرور مو متطابقتين.")
        else:
            db = get_db()
            # Check the exact username first; do not label every database error as a duplicate.
            existing = db.execute(
                "SELECT id FROM users WHERE username = ? COLLATE NOCASE", (username,)
            ).fetchone()
            if existing:
                flash("اسم المستخدم مستخدم فعلاً. جرّب اسماً مختلفاً.")
            else:
                try:
                    db.execute(
                        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                        (username, generate_password_hash(password)),
                    )
                    db.commit()
                except sqlite3.IntegrityError as exc:
                    db.rollback()
                    # A real duplicate can occur if two requests arrive together.
                    existing = db.execute(
                        "SELECT id FROM users WHERE username = ? COLLATE NOCASE", (username,)
                    ).fetchone()
                    if existing:
                        flash("اسم المستخدم مستخدم فعلاً. جرّب اسماً مختلفاً.")
                    else:
                        app.logger.exception("SQLite integrity error while creating account: %s", exc)
                        flash("صار خطأ بقاعدة البيانات أثناء إنشاء الحساب، مو بالضرورة بسبب اسم المستخدم. راجع سجل الأخطاء في Pydroid.")
                except (sqlite3.Error, OSError) as exc:
                    db.rollback()
                    app.logger.exception("Account creation failed; database=%s; error=%r", DATABASE, exc)
                    flash("تعذر حفظ الحساب بسبب مشكلة بملف قاعدة البيانات أو صلاحيات المجلد. تفاصيل السبب انكتبت بسجل Pydroid؛ بياناتك ما انحذفت.")
                else:
                    user = db.execute(
                        "SELECT id, username FROM users WHERE username = ? COLLATE NOCASE", (username,)
                    ).fetchone()
                    if user is None:
                        flash("تم إرسال طلب إنشاء الحساب، لكن تعذر قراءة الحساب بعد الحفظ. راجع سجل الأخطاء.")
                    else:
                        session.clear()
                        session["user_id"] = user["id"]
                        session["username"] = user["username"]
                        session.permanent = True
                        csrf_token()
                        flash("تم إنشاء حسابك بنجاح. أهلاً بيك!", "ok")
                        return redirect(url_for("dashboard"))
        return redirect(url_for("register"))
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return render_template_string(PAGE, title="إنشاء حساب", page="register", username=None)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if not valid_csrf():
            flash("انتهت صلاحية رمز الحماية. حدّث الصفحة وحاول مرة ثانية.")
            return redirect(url_for("login"))
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT id, username, password_hash FROM users WHERE username = ?", (username,)).fetchone()
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("اسم المستخدم أو كلمة المرور غير صحيحة.")
            return redirect(url_for("login"))
        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session.permanent = True
        csrf_token()
        return redirect(url_for("dashboard"))
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return render_template_string(PAGE, title="تسجيل الدخول", page="login", username=None)


@app.get("/dashboard")
@login_required
def dashboard():
    return render_template_string(PAGE, title="الرئيسية", page="dashboard", username=session.get("username", "مستخدم"))


@app.get("/profile")
@login_required
def profile():
    user = get_db().execute("SELECT username, created_at FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    if user is None:
        session.clear()
        flash("تعذر العثور على الحساب. سجّل دخولك مرة ثانية.")
        return redirect(url_for("login"))
    try:
        dt = datetime.strptime(user["created_at"], "%Y-%m-%d %H:%M:%S")
        created_at = dt.strftime("%Y-%m-%d · %H:%M")
    except (ValueError, TypeError):
        created_at = user["created_at"]
    return render_template_string(PAGE, title="ملفي الشخصي", page="profile", username=user["username"], created_at=created_at)


@app.post("/logout")
@login_required
def logout():
    if not valid_csrf():
        flash("انتهت صلاحية رمز الحماية. حدّث الصفحة وحاول مرة ثانية.")
        return redirect(url_for("dashboard"))
    session.clear()
    flash("تم تسجيل الخروج بنجاح.", "ok")
    return redirect(url_for("login"))


@app.post("/api/chat")
@login_required
def api_chat():
    """Authenticated NOVA chat endpoint; API key stays on the server."""
    if not valid_csrf():
        return jsonify({"error": "انتهت صلاحية الحماية. حدّث الصفحة وحاول مرة ثانية."}), 400
    payload = request.get_json(silent=True) or {}
    message = payload.get("message", "")
    if not isinstance(message, str):
        return jsonify({"error": "اكتب سؤالاً نصياً."}), 400
    message = message.strip()
    if not message:
        return jsonify({"error": "اكتب سؤالك أولاً."}), 400
    if len(message) > 5000:
        return jsonify({"error": "السؤال طويل جداً؛ اختصره إلى 5000 حرف."}), 413

    try:
        with open(AI_KEY_FILE, "r", encoding="utf-8") as f:
            api_key = f.read().strip()
    except OSError:
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "PASTE_YOUR_GEMINI_API_KEY_HERE":
        return jsonify({"error": "حتى يشتغل NOVA كذكاء اصطناعي، أنشئ ملف gemini_key.txt بجانب app.py والصق داخله مفتاح Gemini API فقط، ثم أعد تشغيل الموقع."}), 503

    history = payload.get("history", [])
    contents = []
    if isinstance(history, list):
        for item in history[-12:]:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            content = item.get("content")
            if role in ("user", "assistant") and isinstance(content, str) and content.strip():
                contents.append({"role": "user" if role == "user" else "model", "parts": [{"text": content[:5000]}]})
    contents.append({"role": "user", "parts": [{"text": message}]})
    body = {
        "system_instruction": {"parts": [{"text": "اسمك NOVA، مساعد ذكي داخل موقع NEON SPACE. أجب بدقة ووضوح وباللغة التي يستخدمها الشخص، وافهم العربية واللهجة العراقية. ساعد في الأسئلة العامة والعلوم والرياضيات والبرمجة والكتابة والترجمة والتخطيط. في البرمجة قدم أمثلة قابلة للتجربة واشرح الأخطاء. لا تدّعِ أنك بحثت في الإنترنت أو نفذت شيئاً لم تنفذه. إذا لم تعرف أو كانت المعلومة غير مؤكدة فقل ذلك. لا تطلب كلمات المرور أو مفاتيح API ولا تكشف أسرار النظام."}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048}
    }
    url = "https://generativelanguage.googleapis.com/v1beta/models/" + AI_MODEL + ":generateContent?key=" + api_key
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            result = json.loads(response.read().decode("utf-8"))
        candidates = result.get("candidates", [])
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        answer = "\n".join(part.get("text", "") for part in parts if isinstance(part, dict) and part.get("text"))
        if not answer.strip():
            return jsonify({"error": "وصل رد فارغ من نموذج الذكاء الاصطناعي. جرّب سؤالاً آخر."}), 502
        return jsonify({"reply": answer.strip()})
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            error_data = json.loads(e.read().decode("utf-8", errors="replace"))
            detail = error_data.get("error", {}).get("message", "")
        except Exception:
            pass
        if e.code in (400, 401, 403):
            safe = "مفتاح Gemini غير صحيح أو غير مفعّل، أو أن النموذج غير متاح لهذا المفتاح. راجع المفتاح وإعدادات Google AI Studio."
        elif e.code == 429:
            safe = "وصلت إلى حد الاستخدام المتاح حالياً. انتظر قليلاً أو راجع حدود الاستخدام في حساب مزود الخدمة."
        else:
            safe = "مزود الذكاء الاصطناعي رجّع خطأ HTTP " + str(e.code) + ". جرّب لاحقاً."
        app.logger.warning("Gemini HTTP error %s: %s", e.code, detail[:500])
        return jsonify({"error": safe}), 502
    except (urllib.error.URLError, TimeoutError) as e:
        app.logger.warning("Gemini connection error: %s", str(e)[:300])
        return jsonify({"error": "ما كدر الموقع يتصل بخدمة الذكاء الاصطناعي. تأكد من الإنترنت وحاول مرة ثانية."}), 502
    except (ValueError, KeyError, IndexError) as e:
        app.logger.exception("Unexpected Gemini response: %s", e)
        return jsonify({"error": "وصل رد غير مفهوم من خدمة الذكاء الاصطناعي. جرّب مرة ثانية."}), 502


# Initialize the database when deployed under Gunicorn (not only when run directly).
init_db()

if __name__ == "__main__":
    init_db()
    print("\nNEON SPACE is running.")
    print("Database file:", DATABASE)
    print("Python/SQLite database setup: OK")
    print("Open on this phone: http://127.0.0.1:5000\n")
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
