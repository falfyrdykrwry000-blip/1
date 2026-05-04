"""
FM API - خادم تحقق متطور مع دعم CORS وعرض الأخطاء
"""

from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from datetime import datetime, timedelta
import random
import string
import smtplib
import os
import traceback
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fm-api-secret-key-2026')

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

# ========== إعدادات ==========
MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtppro.zoho.com')
MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'verification@krar.qzz.io')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
MAIL_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'verification@krar.qzz.io')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'H6XzkY9cOH$s8md')

verification_codes = {}
email_templates = {
    'verification': {
        'subject': 'رمز التحقق - FM API',
        'body': '<div style="font-family:Tajawal,sans-serif;text-align:center;background:#1a1a2e;padding:40px;border-radius:20px;max-width:400px;margin:0 auto"><h1 style="color:#667eea;font-size:48px;letter-spacing:10px;margin:20px 0;background:#0f0f1a;padding:20px;border-radius:15px">{code}</h1><p style="color:#a0a0b0">هذا الرمز صالح لمدة 10 دقائق</p></div>'
    }
}
usage_stats = {'sent': 0, 'verified': 0, 'failed': 0, 'errors': []}

def generate_code():
    return ''.join(random.choices(string.digits, k=6))

def send_email(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = MAIL_SENDER
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        server = smtplib.SMTP(MAIL_SERVER, MAIL_PORT, timeout=10)
        server.starttls()
        server.login(MAIL_USERNAME, MAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True, None
    except Exception as e:
        error_msg = str(e)
        usage_stats['errors'].append({'time': str(datetime.now()), 'error': error_msg})
        return False, error_msg

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

# ========== الصفحة الرئيسية ==========
@app.route('/')
def home():
    return jsonify({
        'service': 'FM API',
        'version': '2.0',
        'status': 'running',
        'endpoints': {
            'send_code': '/api/send-code',
            'verify_code': '/api/verify-code',
            'stats': '/api/stats',
            'admin': '/admin'
        }
    })

# ========== API ==========
@app.route('/api/send-code', methods=['POST'])
def api_send_code():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'البيانات مطلوبة بصيغة JSON'}), 400
        
        email = data.get('email', '')
        if not email:
            return jsonify({'success': False, 'error': 'البريد الإلكتروني مطلوب'}), 400
        
        code = generate_code()
        verification_codes[email] = {
            'code': code,
            'expires': datetime.now() + timedelta(minutes=10)
        }
        
        template = email_templates['verification']
        body = template['body'].replace('{code}', code)
        
        success, error = send_email(email, template['subject'], body)
        
        if success:
            usage_stats['sent'] += 1
            return jsonify({'success': True, 'message': 'تم إرسال رمز التحقق'})
        else:
            usage_stats['failed'] += 1
            return jsonify({
                'success': False,
                'error': 'فشل إرسال البريد',
                'details': error,
                'hint': 'تأكد من صحة كلمة المرور وإعدادات SMTP'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'خطأ داخلي في الخادم',
            'details': str(e)
        }), 500

@app.route('/api/verify-code', methods=['POST'])
def api_verify_code():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'البيانات مطلوبة بصيغة JSON'}), 400
        
        email = data.get('email', '')
        code = data.get('code', '')
        
        if not email or not code:
            return jsonify({'success': False, 'error': 'البريد والرمز مطلوبان'}), 400
        
        stored = verification_codes.get(email)
        if not stored:
            return jsonify({'success': False, 'error': 'لم يتم إرسال رمز لهذا البريد'}), 404
        
        if datetime.now() > stored['expires']:
            del verification_codes[email]
            return jsonify({'success': False, 'error': 'انتهت صلاحية الرمز'}), 410
        
        if stored['code'] == code:
            del verification_codes[email]
            usage_stats['verified'] += 1
            return jsonify({'success': True, 'message': 'تم التحقق بنجاح'})
        
        return jsonify({'success': False, 'error': 'الرمز غير صحيح'}), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'خطأ داخلي في الخادم',
            'details': str(e)
        }), 500

@app.route('/api/stats')
def api_stats():
    return jsonify({
        'sent': usage_stats['sent'],
        'verified': usage_stats['verified'],
        'failed': usage_stats['failed'],
        'pending': len(verification_codes),
        'last_errors': usage_stats['errors'][-5:] if usage_stats['errors'] else []
    })

# ========== Admin ==========
ADMIN_LOGIN_HTML = '<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>FM API</title><link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;900&display=swap" rel="stylesheet"><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css"><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:Tajawal,sans-serif;background:linear-gradient(135deg,#0f172a,#1e1b4b);min-height:100vh;display:flex;align-items:center;justify-content:center}.card{background:#1e293b;padding:3rem;border-radius:20px;box-shadow:0 25px 50px rgba(0,0,0,0.5);width:100%;max-width:400px;text-align:center}.icon{width:70px;height:70px;background:linear-gradient(135deg,#667eea,#764ba2);border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 1.5rem;font-size:2rem;color:white}h1{color:white;margin-bottom:0.5rem}p{color:#94a3b8;margin-bottom:2rem}input{width:100%;padding:1rem;border:2px solid #334155;border-radius:12px;background:#0f172a;color:white;font-family:Tajawal,sans-serif;font-size:1rem;text-align:center;margin-bottom:1rem}input:focus{outline:none;border-color:#667eea}button{width:100%;padding:1rem;background:linear-gradient(135deg,#667eea,#764ba2);color:white;border:none;border-radius:12px;font-size:1.1rem;font-weight:700;cursor:pointer;font-family:Tajawal,sans-serif}button:hover{opacity:0.9}.error{color:#ef4444;margin-top:1rem}</style></head><body><div class="card"><div class="icon"><i class="fas fa-shield-alt"></i></div><h1>FM API</h1><p>لوحة تحكم خادم التحقق</p><form method="POST" action="/admin/login"><input type="password" name="password" placeholder="كلمة المرور" required><button type="submit"><i class="fas fa-sign-in-alt"></i> دخول</button></form>{% if error %}<p class="error">{{ error }}</p>{% endif %}</div></body></html>'

ADMIN_DASHBOARD_HTML = '<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>لوحة تحكم FM API</title><link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;900&display=swap" rel="stylesheet"><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css"><style>:root{--bg:#0f172a;--card:#1e293b;--text:#e2e8f0;--gray:#94a3b8;--primary:#667eea;--border:#334155;--danger:#ef4444}*{margin:0;padding:0;box-sizing:border-box}body{font-family:Tajawal,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}.header{background:var(--card);padding:1rem 2rem;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border)}.logo{font-size:1.3rem;font-weight:900}.logo i{color:#fbbf24}.btn{background:var(--primary);color:white;border:none;padding:0.5rem 1.2rem;border-radius:20px;cursor:pointer;font-family:Tajawal,sans-serif;text-decoration:none;font-size:0.9rem;display:inline-flex;align-items:center;gap:6px}.btn-danger{background:var(--danger)}.container{max-width:1200px;margin:2rem auto;padding:0 1.5rem}.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:1rem;margin-bottom:2rem}.stat{background:var(--card);padding:1.2rem;border-radius:12px;text-align:center;border:1px solid var(--border)}.stat-num{font-size:1.8rem;font-weight:900}.stat-label{color:var(--gray);font-size:0.8rem;margin-top:0.3rem}.card{background:var(--card);border-radius:15px;padding:1.5rem;border:1px solid var(--border);margin-bottom:1.5rem}.card h2{font-size:1.1rem;margin-bottom:1rem}.form-group{margin-bottom:1rem}label{display:block;margin-bottom:0.4rem;font-weight:500;font-size:0.9rem}input,textarea{width:100%;padding:0.7rem;background:var(--bg);border:1px solid var(--border);border-radius:10px;color:var(--text);font-family:Tajawal,sans-serif}textarea{min-height:150px;resize:vertical;font-family:monospace}input:focus,textarea:focus{outline:none;border-color:var(--primary)}.errors{margin-top:1rem}.err-item{background:rgba(239,68,68,0.1);padding:0.7rem;border-radius:8px;margin-bottom:0.5rem;font-size:0.8rem;color:#fca5a5}@media(max-width:768px){.stats{grid-template-columns:1fr 1fr}.container{padding:0 1rem}}</style></head><body><header class="header"><div class="logo"><i class="fas fa-shield-alt"></i> FM API - لوحة التحكم</div><a href="/admin/logout" class="btn btn-danger"><i class="fas fa-sign-out-alt"></i> خروج</a></header><div class="container"><div class="stats"><div class="stat"><div class="stat-num">{{ stats.sent }}</div><div class="stat-label">📤 تم الإرسال</div></div><div class="stat"><div class="stat-num">{{ stats.verified }}</div><div class="stat-label">✅ تم التحقق</div></div><div class="stat"><div class="stat-num">{{ stats.failed }}</div><div class="stat-label">❌ فشل</div></div><div class="stat"><div class="stat-num">{{ pending }}</div><div class="stat-label">⏳ قيد الانتظار</div></div></div><div class="card"><h2><i class="fas fa-palette"></i> تخصيص القالب</h2><form onsubmit="saveTemplate(event)"><div class="form-group"><label>عنوان الرسالة</label><input type="text" id="subject" value="{{ template.subject }}"></div><div class="form-group"><label>محتوى HTML</label><textarea id="body">{{ template.body }}</textarea></div><button type="submit" class="btn"><i class="fas fa-save"></i> حفظ</button></form></div><div class="card"><h2><i class="fas fa-bug"></i> آخر الأخطاء</h2><div class="errors">{% if errors %}{% for e in errors %}<div class="err-item">{{ e.time }} - {{ e.error }}</div>{% endfor %}{% else %}<p style="color:var(--gray)">لا توجد أخطاء</p>{% endif %}</div></div></div><script>function saveTemplate(e){e.preventDefault();fetch("/admin/template",{method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},body:"subject="+encodeURIComponent(document.getElementById("subject").value)+"&body="+encodeURIComponent(document.getElementById("body").value)}).then(r=>r.json()).then(d=>alert(d.message))}</script></body></html>'

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
    return render_template_string(ADMIN_DASHBOARD_HTML,
                                 stats=usage_stats,
                                 pending=len(verification_codes),
                                 template=email_templates['verification'],
                                 errors=usage_stats['errors'][-10:])

@app.route('/admin/template', methods=['POST'])
@admin_required
def update_template():
    email_templates['verification'] = {
        'subject': request.form.get('subject', ''),
        'body': request.form.get('body', '')
    }
    return jsonify({'success': True, 'message': 'تم تحديث القالب'})

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)