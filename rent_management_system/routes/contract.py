from flask import Blueprint, request, jsonify
import os
from datetime import datetime

contract_bp = Blueprint('contract', __name__)

@contract_bp.route('/contracts', methods=['POST'])
def upload_contract():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    property_id = request.form['property_id']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    version = 1
    while os.path.exists(f"contracts/{property_id}_v{version}.pdf"):
        version += 1
    
    file.save(f"contracts/{property_id}_v{version}.pdf")
    return jsonify({"message": "Contract uploaded successfully"}), 201