"""
FM API - خادم تحقق مع SendGrid
للرفع على Render
"""

from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from datetime import datetime, timedelta
import random
import string
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = 'fm-api-secret-key-2026'

# ========== CORS ==========
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response

@app.route('/api/send-code', methods=['OPTIONS'])
@app.route('/api/verify-code', methods=['OPTIONS'])
def handle_options():
    return '', 200

# ========== الإعدادات ==========
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '')
MAIL_SENDER = 'verification@krar.qzz.io'
ADMIN_PASSWORD = 'H6XzkY9cOH$s8md'

verification_codes = {}
email_templates = {
    'verification': {
        'subject': 'رمز التحقق - FM API',
        'body': '<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;900&display=swap" rel="stylesheet"></head><body style="margin:0;padding:0;background:#f1f5f9;font-family:Tajawal,sans-serif;"><table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:30px 0;"><tr><td align="center"><table width="100%" cellpadding="0" cellspacing="0" style="max-width:500px;background:white;border-radius:20px;overflow:hidden;box-shadow:0 10px 40px rgba(0,0,0,0.1);"><tr><td style="background:linear-gradient(135deg,#667eea,#764ba2);padding:30px 20px;text-align:center;"><img src="https://raw.githubusercontent.com/falfyrdykrwry000-blip/photo/refs/heads/main/Gemini_Generated_Image_u27f02u27f02u27f.png" alt="FM AI" style="width:70px;height:70px;border-radius:50%;border:3px solid white;margin-bottom:12px;"><h1 style="color:white;font-size:22px;margin:0;">FM AI</h1><p style="color:rgba(255,255,255,0.8);font-size:14px;margin:5px 0 0;">منصة عربية طموحة من إنتاج FM AI</p></td></tr><tr><td style="padding:35px 25px;"><table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;border-radius:15px;padding:25px;text-align:center;border:2px dashed #667eea;"><tr><td><p style="color:#64748b;font-size:14px;margin:0 0 10px;">رمز التحقق الخاص بك</p><h1 style="color:#667eea;font-size:42px;letter-spacing:12px;margin:0;font-weight:900;">{code}</h1><p style="color:#94a3b8;font-size:12px;margin:10px 0 0;">صالح لمدة 10 دقائق</p></td></tr></table><table width="100%" cellpadding="0" cellspacing="0" style="margin-top:25px;"><tr><td style="color:#475569;font-size:14px;line-height:1.8;"><p style="margin:0 0 10px;">مرحباً بك،</p><p style="margin:0 0 10px;">تم طلب رمز تحقق لحسابك. استخدم الرمز أعلاه لإكمال العملية.</p><p style="margin:0;color:#94a3b8;font-size:13px;">إذا لم تطلب هذا الرمز، يرجى تجاهل هذه الرسالة.</p></td></tr></table></td></tr><tr><td style="border-top:1px solid #e2e8f0;"></td></tr><tr><td style="padding:20px 25px;text-align:center;background:#f8fafc;"><table width="100%" cellpadding="0" cellspacing="0"><tr><td style="text-align:center;"><a href="https://krar.qzz.io" style="text-decoration:none;margin:0 8px;" target="_blank"><img src="https://img.shields.io/badge/المدونة-667eea?style=flat-square" alt="المدونة" style="height:22px;"></a><a href="https://kruri.qzz.io" style="text-decoration:none;margin:0 8px;" target="_blank"><img src="https://img.shields.io/badge/FM_AI-764ba2?style=flat-square" alt="FM AI" style="height:22px;"></a></td></tr><tr><td style="padding-top:12px;color:#94a3b8;font-size:11px;">© 2026 FM AI | جميع الحقوق محفوظة<br><a href="https://krar.qzz.io" style="color:#667eea;text-decoration:none;" target="_blank">krar.qzz.io</a></td></tr></table></td></tr></table></td></tr></table></body></html>'
    }
}
usage_stats = {'sent': 0, 'verified': 0, 'failed': 0, 'errors': []}

def generate_code():
    return ''.join(random.choices(string.digits, k=6))

def send_email(to_email, subject, body):
    try:
        import requests
        url = 'https://api.sendgrid.com/v3/mail/send'
        headers = {
            'Authorization': f'Bearer {SENDGRID_API_KEY}',
            'Content-Type': 'application/json'
        }
        data = {
            'personalizations': [{'to': [{'email': to_email}]}],
            'from': {'email': MAIL_SENDER},
            'subject': subject,
            'content': [{'type': 'text/html', 'value': body}]
        }
        r = requests.post(url, headers=headers, json=data)
        if r.status_code in [200, 201, 202]:
            return True, None
        else:
            return False, r.text
    except Exception as e:
        return False, str(e)

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def home():
    return jsonify({'service': 'FM API', 'status': 'running'})

@app.route('/api/send-code', methods=['POST'])
def api_send_code():
    try:
        data = request.get_json()
        email = data.get('email', '')
        if not email:
            return jsonify({'success': False, 'error': 'البريد مطلوب'}), 400
        
        code = generate_code()
        verification_codes[email] = {'code': code, 'expires': datetime.now() + timedelta(minutes=10)}
        
        template = email_templates['verification']
        body = template['body'].replace('{code}', code)
        
        success, error = send_email(email, template['subject'], body)
        
        if success:
            usage_stats['sent'] += 1
            return jsonify({'success': True, 'message': 'تم الإرسال'})
        else:
            usage_stats['failed'] += 1
            usage_stats['errors'].append({'time': str(datetime.now()), 'error': str(error)[:200]})
            return jsonify({'success': False, 'error': 'فشل الإرسال', 'details': str(error)[:200]}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/verify-code', methods=['POST'])
def api_verify_code():
    data = request.get_json()
    email = data.get('email', '')
    code = data.get('code', '')
    stored = verification_codes.get(email)
    if not stored:
        return jsonify({'success': False, 'error': 'لا يوجد رمز'}), 404
    if datetime.now() > stored['expires']:
        del verification_codes[email]
        return jsonify({'success': False, 'error': 'منتهي'}), 410
    if stored['code'] == code:
        del verification_codes[email]
        usage_stats['verified'] += 1
        return jsonify({'success': True, 'message': 'تم التحقق'})
    return jsonify({'success': False, 'error': 'رمز خاطئ'}), 400

@app.route('/api/stats')
def api_stats():
    return jsonify({'sent': usage_stats['sent'], 'verified': usage_stats['verified'], 'failed': usage_stats['failed'], 'pending': len(verification_codes), 'last_errors': usage_stats['errors'][-5:]})

ADMIN_LOGIN_HTML = '<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>FM API</title><link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;900&display=swap" rel="stylesheet"><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:Tajawal,sans-serif;background:linear-gradient(135deg,#0f172a,#1e1b4b);min-height:100vh;display:flex;align-items:center;justify-content:center}.card{background:#1e293b;padding:3rem;border-radius:20px;width:100%;max-width:400px;text-align:center;color:white}h1{margin-bottom:1rem}input{width:100%;padding:1rem;background:#0f172a;border:2px solid #334155;border-radius:12px;color:white;font-family:Tajawal,sans-serif;text-align:center;margin-bottom:1rem}input:focus{outline:none;border-color:#667eea}button{width:100%;padding:1rem;background:linear-gradient(135deg,#667eea,#764ba2);color:white;border:none;border-radius:12px;font-weight:700;cursor:pointer;font-family:Tajawal,sans-serif}.error{color:#ef4444;margin-top:1rem}</style></head><body><div class="card"><div style="font-size:3rem;margin-bottom:1rem">🔐</div><h1>FM API</h1><form method="POST" action="/admin/login"><input type="password" name="password" placeholder="كلمة المرور" required><button type="submit">دخول</button></form>{% if error %}<p class="error">{{ error }}</p>{% endif %}</div></body></html>'

ADMIN_DASHBOARD_HTML = '<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>لوحة تحكم FM API</title><link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;900&display=swap" rel="stylesheet"><style>:root{--bg:#0f172a;--card:#1e293b;--text:#e2e8f0;--gray:#94a3b8;--primary:#667eea;--border:#334155}*{margin:0;padding:0;box-sizing:border-box}body{font-family:Tajawal,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}.header{background:var(--card);padding:1rem 2rem;display:flex;justify-content:space-between;align-items:center}.logo{font-weight:900;font-size:1.2rem}.btn{background:var(--primary);color:white;border:none;padding:0.5rem 1.2rem;border-radius:20px;cursor:pointer;font-family:Tajawal,sans-serif;text-decoration:none;font-size:0.9rem}.btn-danger{background:#ef4444}.container{max-width:1000px;margin:2rem auto;padding:0 1rem}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin-bottom:2rem}.stat{background:var(--card);padding:1.2rem;border-radius:12px;text-align:center}.stat-num{font-size:1.8rem;font-weight:900}.stat-label{color:var(--gray);font-size:0.8rem}.card{background:var(--card);border-radius:15px;padding:1.5rem;margin-bottom:1.5rem}.card h2{margin-bottom:1rem}input,textarea{width:100%;padding:0.7rem;background:var(--bg);border:1px solid var(--border);border-radius:10px;color:var(--text);font-family:Tajawal,sans-serif;margin-bottom:0.8rem}textarea{min-height:120px;resize:vertical}@media(max-width:768px){.stats{grid-template-columns:1fr 1fr}}</style></head><body><header class="header"><div class="logo">🔐 FM API</div><a href="/admin/logout" class="btn btn-danger">خروج</a></header><div class="container"><div class="stats"><div class="stat"><div class="stat-num">{{ stats.sent }}</div><div class="stat-label">📤 تم الإرسال</div></div><div class="stat"><div class="stat-num">{{ stats.verified }}</div><div class="stat-label">✅ تم التحقق</div></div><div class="stat"><div class="stat-num">{{ stats.failed }}</div><div class="stat-label">❌ فشل</div></div><div class="stat"><div class="stat-num">{{ pending }}</div><div class="stat-label">⏳ قيد الانتظار</div></div></div><div class="card"><h2>تخصيص القالب</h2><form onsubmit="saveTemplate(event)"><input type="text" id="subject" value="{{ template.subject }}"><textarea id="body">{{ template.body }}</textarea><button type="submit" class="btn">حفظ</button></form></div><div class="card"><h2>آخر الأخطاء</h2>{% if errors %}{% for e in errors %}<div style="background:rgba(239,68,68,0.1);padding:0.7rem;border-radius:8px;margin-bottom:0.5rem;font-size:0.8rem;color:#fca5a5">{{ e.time }} - {{ e.error }}</div>{% endfor %}{% else %}<p style="color:var(--gray)">لا توجد أخطاء</p>{% endif %}</div></div><script>function saveTemplate(e){e.preventDefault();fetch("/admin/template",{method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},body:"subject="+encodeURIComponent(document.getElementById("subject").value)+"&body="+encodeURIComponent(document.getElementById("body").value)}).then(r=>r.json()).then(d=>alert(d.message))}</script></body></html>'

@app.route('/admin')
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        return render_template_string(ADMIN_LOGIN_HTML, error='كلمة المرور غير صحيحة')
    return render_template_string(ADMIN_LOGIN_HTML, error='')

@app.route('/admin/login', methods=['POST'])
def admin_login_post():
    if request.form.get('password') == ADMIN_PASSWORD:
        session['admin_logged_in'] = True
        return redirect(url_for('admin_dashboard'))
    return render_template_string(ADMIN_LOGIN_HTML, error='كلمة المرور غير صحيحة')

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    return render_template_string(ADMIN_DASHBOARD_HTML, stats=usage_stats, pending=len(verification_codes), template=email_templates['verification'], errors=usage_stats['errors'][-10:])

@app.route('/admin/template', methods=['POST'])
@admin_required
def update_template():
    email_templates['verification'] = {'subject': request.form.get('subject', ''), 'body': request.form.get('body', '')}
    return jsonify({'success': True})

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)