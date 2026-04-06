from flask import Blueprint, request, jsonify
from models import Tenant
from extensions import db
import re

tenant_bp = Blueprint('tenant', __name__)

def validate_phone(phone):
    """验证手机号：11位数字，以1开头"""
    if not phone:
        return False, "手机号不能为空"
    pattern = r'^1[3-9]\d{9}$'
    if not re.match(pattern, phone):
        return False, "手机号格式错误，应为11位数字（以1开头）"
    return True, None

def validate_id_card(id_card):
    """验证身份证号：18位，最后一位可以是X"""
    if not id_card:
        return True, None  # 身份证可选
    pattern = r'^[1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$'
    if not re.match(pattern, id_card):
        return False, "身份证号格式错误，应为18位"
    # 校验最后一位
    if len(id_card) == 18:
        weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        check_codes = '10X98765432'
        total = sum(int(id_card[i]) * weights[i] for i in range(17))
        expected = check_codes[total % 11]
        if id_card[-1].upper() != expected:
            return False, "身份证号校验失败，请检查是否正确"
    return True, None

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

    # 验证手机号
    valid, error = validate_phone(data.get('phone'))
    if not valid:
        return jsonify({"error": error}), 400

    # 验证身份证号
    if data.get('id_card'):
        valid, error = validate_id_card(data.get('id_card'))
        if not valid:
            return jsonify({"error": error}), 400

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

    # 验证手机号
    if 'phone' in data:
        valid, error = validate_phone(data['phone'])
        if not valid:
            return jsonify({"error": error}), 400

    # 验证身份证号
    if 'id_card' in data and data.get('id_card'):
        valid, error = validate_id_card(data['id_card'])
        if not valid:
            return jsonify({"error": error}), 400

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

@tenant_bp.route('/tenants/<int:id>/lease_status', methods=['GET'])
def tenant_lease_status(id):
    """检查租客是否有进行中的租约"""
    t = Tenant.query.get(id)
    if not t:
        return jsonify({"error": "Tenant not found"}), 404

    active_leases = [l for l in t.leases if l.status == 'active']
    if active_leases:
        lease = active_leases[0]
        return jsonify({
            "has_active_lease": True,
            "lease_id": lease.id,
            "lease_name": lease.name,
            "property_name": lease.property.name if lease.property else None,
            "message": f"该租客已有进行中的租约：{lease.property.name if lease.property else ''}"
        }), 200
    return jsonify({"has_active_lease": False}), 200
