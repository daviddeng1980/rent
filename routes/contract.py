from flask import Blueprint, request, jsonify, send_from_directory
from models import Lease
from extensions import db
import os
import uuid
import json

contract_bp = Blueprint('contract', __name__)

CONTRACT_FOLDER = 'contracts'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def ensure_contract_dir(lease_id):
    dir_path = os.path.join(CONTRACT_FOLDER, str(lease_id))
    os.makedirs(dir_path, exist_ok=True)
    return dir_path

@contract_bp.route('/leases/<int:lease_id>/contracts', methods=['GET'])
def get_contracts(lease_id):
    lease = Lease.query.get(lease_id)
    if not lease:
        return jsonify({'error': 'Lease not found'}), 404
    files = json.loads(lease.contract_files or '[]')
    return jsonify(files), 200

@contract_bp.route('/leases/<int:lease_id>/contracts', methods=['POST'])
def upload_contract(lease_id):
    lease = Lease.query.get(lease_id)
    if not lease:
        return jsonify({'error': 'Lease not found'}), 404

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    if file.content_length and file.content_length > MAX_FILE_SIZE:
        return jsonify({'error': f'文件太大，最大 {MAX_FILE_SIZE // 1024 // 1024}MB'}), 400

    ensure_contract_dir(lease_id)
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(CONTRACT_FOLDER, str(lease_id), filename)
    file.save(filepath)

    files = json.loads(lease.contract_files or '[]')
    file_info = {
        'id': len(files) + 1,
        'filename': filename,
        'original_name': file.filename,
        'path': filepath,
        'size': os.path.getsize(filepath)
    }
    files.append(file_info)
    lease.contract_files = json.dumps(files)
    db.session.commit()

    return jsonify(file_info), 200

@contract_bp.route('/contracts/<lease_id>/<filename>', methods=['GET'])
def serve_contract(lease_id, filename):
    dir_path = os.path.join(CONTRACT_FOLDER, lease_id)
    return send_from_directory(dir_path, filename)

@contract_bp.route('/contracts/<int:lease_id>/<int:file_id>', methods=['DELETE'])
def delete_contract(lease_id, file_id):
    lease = Lease.query.get(lease_id)
    if not lease:
        return jsonify({'error': 'Lease not found'}), 404

    files = json.loads(lease.contract_files or '[]')
    file_to_delete = None
    for f in files:
        if f['id'] == file_id:
            file_to_delete = f
            break

    if not file_to_delete:
        return jsonify({'error': 'File not found'}), 404

    filepath = file_to_delete['path']
    if os.path.exists(filepath):
        os.remove(filepath)

    files = [f for f in files if f['id'] != file_id]
    lease.contract_files = json.dumps(files)
    db.session.commit()

    return jsonify({'message': 'File deleted'}), 200
