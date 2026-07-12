from flask import Flask, jsonify, render_template, send_from_directory, request, redirect, session, make_response
from flask_cors import CORS
from extensions import db
import os

app = Flask(__name__)
app.secret_key = 'daviddeng-rent-secret-key-2024'
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rent_management.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'

USERNAME = 'daviddeng'
PASSWORD = '810123'

db.init_app(app)

@app.route('/rent/uploads/<path:filename>')
def serve_upload(filename):
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    return send_from_directory('uploads', filename)

@app.route('/rent/contracts/<path:filename>')
def serve_contract(filename):
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    return send_from_directory('contracts', filename)

@app.route('/rent/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '')
    password = data.get('password', '')
    if username == USERNAME and password == PASSWORD:
        session['logged_in'] = True
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': '账号或密码错误'}), 401

@app.route('/rent/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/rent/check-auth', methods=['GET'])
def check_auth():
    return jsonify({'logged_in': session.get('logged_in', False)})

@app.route('/rent/')
def index():
    if not session.get('logged_in'):
        return '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>租房管理系统 - 登录</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif; min-height: 100vh; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; }
        .login-container { background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); overflow: hidden; max-width: 420px; width: 100%; }
        .login-header { background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%); color: white; padding: 40px 30px; text-align: center; }
        .login-header h1 { font-size: 1.8rem; margin-bottom: 8px; display: flex; align-items: center; justify-content: center; gap: 10px; }
        .login-header p { opacity: 0.9; font-size: 0.95rem; }
        .login-body { padding: 40px 30px; }
        .form-group { margin-bottom: 24px; }
        .form-group label { display: block; margin-bottom: 8px; color: #2c3e50; font-weight: 500; }
        .form-group input { width: 100%; padding: 14px 16px; border: 2px solid #e0e6ed; border-radius: 10px; font-size: 1rem; transition: all 0.3s; }
        .form-group input:focus { outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102,126,234,0.1); }
        .btn-login { width: 100%; padding: 16px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 10px; font-size: 1.1rem; font-weight: 600; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; }
        .btn-login:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(102,126,234,0.4); }
        .error-msg { background: #fee; color: #c00; padding: 12px 16px; border-radius: 8px; margin-bottom: 20px; display: none; text-align: center; }
        .login-footer { text-align: center; padding: 20px 30px; background: #f8f9fa; color: #888; font-size: 0.85rem; }
        .house-icon { font-size: 3rem; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-header">
            <div class="house-icon">🏠</div>
            <h1>租房管理系统</h1>
            <p>请输入您的账号信息登录</p>
        </div>
        <div class="login-body">
            <div class="error-msg" id="errorMsg">账号或密码错误，请重试</div>
            <div class="form-group"><label>账号</label><input type="text" id="username" placeholder="请输入账号"></div>
            <div class="form-group"><label>密码</label><input type="password" id="password" placeholder="请输入密码"></div>
            <button class="btn-login" onclick="handleLogin()">登 录</button>
        </div>
        <div class="login-footer">© 2024 租房管理系统</div>
    </div>
    <script>
        function handleLogin() {
            var u = document.getElementById('username').value;
            var p = document.getElementById('password').value;
            fetch('/rent/login', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({username:u, password:p})})
            .then(function(res){ if(res.ok) window.location.href='/rent/'; else document.getElementById('errorMsg').style.display='block'; })
            .catch(function(){ document.getElementById('errorMsg').style.display='block'; });
        }
        document.getElementById('password').addEventListener('keypress', function(e){ if(e.key==='Enter') handleLogin(); });
    </script>
</body>
</html>
        '''

    else:
        return redirect('/rent/m/')

@app.route('/rent/m/')
def mobile_index():
    if not session.get('logged_in'):
        return '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>租房管理系统 - 登录</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif; min-height: 100vh; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; }
        .login-container { background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); overflow: hidden; max-width: 420px; width: 100%; }
        .login-header { background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%); color: white; padding: 40px 30px; text-align: center; }
        .login-header h1 { font-size: 1.8rem; margin-bottom: 8px; display: flex; align-items: center; justify-content: center; gap: 10px; }
        .login-header p { opacity: 0.9; font-size: 0.95rem; }
        .login-body { padding: 40px 30px; }
        .form-group { margin-bottom: 24px; }
        .form-group label { display: block; margin-bottom: 8px; color: #2c3e50; font-weight: 500; }
        .form-group input { width: 100%; padding: 14px 16px; border: 2px solid #e0e6ed; border-radius: 10px; font-size: 1rem; transition: all 0.3s; }
        .form-group input:focus { outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102,126,234,0.1); }
        .btn-login { width: 100%; padding: 16px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 10px; font-size: 1.1rem; font-weight: 600; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; }
        .btn-login:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(102,126,234,0.4); }
        .error-msg { background: #fee; color: #c00; padding: 12px 16px; border-radius: 8px; margin-bottom: 20px; display: none; text-align: center; }
        .login-footer { text-align: center; padding: 20px 30px; background: #f8f9fa; color: #888; font-size: 0.85rem; }
        .house-icon { font-size: 3rem; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-header">
            <div class="house-icon">🏠</div>
            <h1>租房管理系统</h1>
            <p>移动端请登录</p>
        </div>
        <div class="login-body">
            <div class="error-msg" id="errorMsg">账号或密码错误，请重试</div>
            <div class="form-group"><label>账号</label><input type="text" id="username" placeholder="请输入账号" autocomplete="off"></div>
            <div class="form-group"><label>密码</label><input type="password" id="password" placeholder="请输入密码"></div>
            <button class="btn-login" onclick="handleLogin()">登 录</button>
        </div>
        <div class="login-footer">© 2024 租房管理系统</div>
    </div>
    <script>
        function handleLogin() {
            var u = document.getElementById('username').value;
            var p = document.getElementById('password').value;
            fetch('/rent/login', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({username:u, password:p})})
            .then(function(res){ if(res.ok) window.location.href='/rent/m/'; else document.getElementById('errorMsg').style.display='block'; })
            .catch(function(){ document.getElementById('errorMsg').style.display='block'; });
        }
        document.getElementById('password').addEventListener('keypress', function(e){ if(e.key==='Enter') handleLogin(); });
    </script>
</body>
</html>
        '''
    return render_template('index_mobile.html')

    return render_template('index.html')

from routes.property import property_bp
from routes.tenant import tenant_bp
from routes.payment import payment_bp
from routes.lease import lease_bp
from routes.analysis import analysis_bp
from routes.upload import upload_bp
from routes.contract import contract_bp

app.register_blueprint(property_bp, url_prefix='/rent')
app.register_blueprint(tenant_bp, url_prefix='/rent')
app.register_blueprint(payment_bp, url_prefix='/rent')
app.register_blueprint(lease_bp, url_prefix='/rent')
app.register_blueprint(analysis_bp, url_prefix='/rent')
app.register_blueprint(upload_bp, url_prefix='/rent')
app.register_blueprint(contract_bp, url_prefix='/rent')

if __name__ == '__main__':
    app.run(debug=True, port=5001)

from models import *
