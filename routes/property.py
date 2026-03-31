from flask import Blueprint, request, jsonify
from models import Property
from extensions import db
from datetime import datetime
import json

property_bp = Blueprint('property', __name__)

def serialize_property(p):
    images = []
    try:
        images = json.loads(p.images) if p.images else []
    except:
        images = []

    return {
        'id': p.id,
        'name': p.name,
        'address': p.address,
        'area': p.area,
        'property_type': p.property_type,
        'decoration': p.decoration,
        'furniture': p.furniture,
        'rent_guide': p.rent_guide,
        'purchase_date': p.purchase_date.strftime('%Y-%m-%d') if p.purchase_date else None,
        'purchase_price': p.purchase_price,
        'loan_amount': p.loan_amount,
        'loan_rate': p.loan_rate,
        'property_fee': p.property_fee,
        'remark': p.remark,
        'images': images,
        'status': p.status
    }

@property_bp.route('/properties', methods=['GET'])
def get_properties():
    properties = Property.query.all()
    return jsonify([serialize_property(p) for p in properties]), 200

@property_bp.route('/properties/<int:id>', methods=['GET'])
def get_property(id):
    p = Property.query.get(id)
    if not p:
        return jsonify({"error": "Property not found"}), 404
    return jsonify(serialize_property(p)), 200

@property_bp.route('/properties', methods=['POST'])
def add_property():
    data = request.get_json()
    try:
        p = Property(
            name=data['name'],
            address=data['address'],
            area=data.get('area'),
            property_type=data.get('property_type'),
            decoration=data.get('decoration'),
            furniture=data.get('furniture'),
            rent_guide=data.get('rent_guide'),
            purchase_price=data.get('purchase_price', 0),
            loan_amount=data.get('loan_amount', 0),
            loan_rate=data.get('loan_rate', 0),
            property_fee=data.get('property_fee', 0),
            remark=data.get('remark'),
            images=json.dumps(data.get('images', []))
        )
        if data.get('purchase_date'):
            try:
                p.purchase_date = datetime.strptime(data['purchase_date'], '%Y-%m-%d').date()
            except ValueError as e:
                return jsonify({"error": f"日期格式错误: {data['purchase_date']}，正确格式：YYYY-MM-DD"}), 400
        db.session.add(p)
        db.session.commit()
        return jsonify({"message": "Property added", "id": p.id, "status": p.status}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"添加房产失败: {str(e)}"}), 500

@property_bp.route('/properties/<int:id>', methods=['PUT'])
def update_property(id):
    p = Property.query.get(id)
    if not p:
        return jsonify({"error": "Property not found"}), 404
    data = request.get_json()
    try:
        p.name = data.get('name', p.name)
        p.address = data.get('address', p.address)
        p.area = data.get('area', p.area)
        p.property_type = data.get('property_type', p.property_type)
        p.decoration = data.get('decoration', p.decoration)
        p.furniture = data.get('furniture', p.furniture)
        p.rent_guide = data.get('rent_guide', p.rent_guide)
        p.purchase_price = data.get('purchase_price', p.purchase_price)
        p.loan_amount = data.get('loan_amount', p.loan_amount)
        p.loan_rate = data.get('loan_rate', p.loan_rate)
        p.property_fee = data.get('property_fee', p.property_fee)
        p.remark = data.get('remark', p.remark)
        if 'images' in data:
            p.images = json.dumps(data['images'])
        if data.get('purchase_date'):
            try:
                p.purchase_date = datetime.strptime(data['purchase_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({"error": f"日期格式错误: {data['purchase_date']}，正确格式：YYYY-MM-DD"}), 400
        db.session.commit()
        return jsonify({"message": "Property updated", "status": p.status}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"更新房产失败: {str(e)}"}), 500

@property_bp.route('/properties/<int:id>', methods=['DELETE'])
def delete_property(id):
    p = Property.query.get(id)
    if not p:
        return jsonify({"error": "Property not found"}), 404
    if p.leases:
        return jsonify({"error": "Cannot delete property with active lease"}), 400
    db.session.delete(p)
    db.session.commit()
    return jsonify({"message": "Property deleted"}), 200
