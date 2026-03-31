from flask import Flask, jsonify, render_template, send_from_directory
from flask_cors import CORS
from extensions import db
import os

app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rent_management.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
db.init_app(app)

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory('uploads', filename)

@app.route('/contracts/<path:filename>')
def serve_contract(filename):
    return send_from_directory('contracts', filename)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/old')
def old_index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>租金管理系统</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            h1 { color: #333; }
            .endpoint { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }
            .method { display: inline-block; padding: 3px 8px; border-radius: 3px; color: white; font-weight: bold; }
            .post { background: #28a745; }
            .get { background: #007bff; }
            code { background: #e9ecef; padding: 2px 5px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <h1>🏠 租金管理系统 API</h1>
        <h2>可用端点：</h2>
        <div class="endpoint">
            <span class="method post">POST</span> <code>/properties</code> - 添加房产
        </div>
        <div class="endpoint">
            <span class="method post">POST</span> <code>/properties/bulk</code> - 批量导入房产
        </div>
        <div class="endpoint">
            <span class="method post">POST</span> <code>/tenants</code> - 添加租客
        </div>
        <div class="endpoint">
            <span class="method post">POST</span> <code>/payments</code> - 添加付款记录
        </div>
        <div class="endpoint">
            <span class="method post">POST</span> <code>/contracts</code> - 上传合同
        </div>
        <div class="endpoint">
            <span class="method get">GET</span> <code>/analysis/annual_profit/&lt;property_id&gt;</code> - 年度利润分析
        </div>
    </body>
    </html>
    '''

from routes.property import property_bp
from routes.tenant import tenant_bp
from routes.payment import payment_bp
from routes.lease import lease_bp
from routes.analysis import analysis_bp
from routes.upload import upload_bp
from routes.contract import contract_bp

app.register_blueprint(property_bp)
app.register_blueprint(tenant_bp)
app.register_blueprint(payment_bp)
app.register_blueprint(lease_bp)
app.register_blueprint(analysis_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(contract_bp)

if __name__ == '__main__':
    app.run(debug=True, port=5001)

from models import *