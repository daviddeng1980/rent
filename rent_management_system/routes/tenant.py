from flask import Blueprint, request, jsonify
from models import Tenant, db
from datetime import datetime

tenant_bp = Blueprint('tenant', __name__)

@tenant_bp.route('/tenants', methods=['POST'])
def add_tenant():
    data = request.get_json()
    new_tenant = Tenant(
        name=data['name'],
        phone=data['phone'],
        property_id=data['property_id'],
        emergency_contact=data['emergency_contact']
    )
    db.session.add(new_tenant)
    db.session.commit()
    return jsonify({"message": "Tenant added successfully"}), 201