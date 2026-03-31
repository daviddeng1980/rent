from flask import Blueprint, request, jsonify
from models import Tenant
from extensions import db

tenant_bp = Blueprint('tenant', __name__)

@tenant_bp.route('/tenants', methods=['GET'])
def get_tenants():
    tenants = Tenant.query.all()
    return jsonify([{
        'id': t.id,
        'name': t.name,
        'phone': t.phone,
        'id_card': t.id_card,
        'emergency_contact': t.emergency_contact,
        'emergency_phone': t.emergency_phone,
        'remark': t.remark
    } for t in tenants]), 200

@tenant_bp.route('/tenants/<int:id>', methods=['GET'])
def get_tenant(id):
    t = Tenant.query.get(id)
    if not t:
        return jsonify({"error": "Tenant not found"}), 404
    return jsonify({
        'id': t.id,
        'name': t.name,
        'phone': t.phone,
        'id_card': t.id_card,
        'emergency_contact': t.emergency_contact,
        'emergency_phone': t.emergency_phone,
        'remark': t.remark
    }), 200

@tenant_bp.route('/tenants', methods=['POST'])
def add_tenant():
    data = request.get_json()
    t = Tenant(
        name=data['name'],
        phone=data['phone'],
        id_card=data.get('id_card'),
        emergency_contact=data.get('emergency_contact'),
        emergency_phone=data.get('emergency_phone'),
        remark=data.get('remark')
    )
    db.session.add(t)
    db.session.commit()
    return jsonify({"message": "Tenant added", "id": t.id}), 201

@tenant_bp.route('/tenants/<int:id>', methods=['PUT'])
def update_tenant(id):
    t = Tenant.query.get(id)
    if not t:
        return jsonify({"error": "Tenant not found"}), 404
    data = request.get_json()
    t.name = data.get('name', t.name)
    t.phone = data.get('phone', t.phone)
    t.id_card = data.get('id_card', t.id_card)
    t.emergency_contact = data.get('emergency_contact', t.emergency_contact)
    t.emergency_phone = data.get('emergency_phone', t.emergency_phone)
    t.remark = data.get('remark', t.remark)
    db.session.commit()
    return jsonify({"message": "Tenant updated"}), 200

@tenant_bp.route('/tenants/<int:id>', methods=['DELETE'])
def delete_tenant(id):
    t = Tenant.query.get(id)
    if not t:
        return jsonify({"error": "Tenant not found"}), 404
    if t.leases:
        return jsonify({"error": "Cannot delete tenant with active lease"}), 400
    db.session.delete(t)
    db.session.commit()
    return jsonify({"message": "Tenant deleted"}), 200
