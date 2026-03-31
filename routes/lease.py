from flask import Blueprint, request, jsonify
from models import Lease, Payment, Property
from extensions import db
from datetime import datetime, timedelta
import calendar

lease_bp = Blueprint('lease', __name__)

@lease_bp.route('/leases', methods=['GET'])
def get_leases():
    leases = Lease.query.all()
    return jsonify([{
        'id': l.id,
        'name': l.name,
        'property_id': l.property_id,
        'property_name': l.property.name if l.property else None,
        'property_address': l.property.address if l.property else None,
        'tenant_id': l.tenant_id,
        'tenant_name': l.tenant.name if l.tenant else None,
        'rent_amount': l.rent_amount,
        'rent_day': l.rent_day,
        'deposit': l.deposit,
        'start_date': l.start_date.strftime('%Y-%m-%d') if l.start_date else None,
        'end_date': l.end_date.strftime('%Y-%m-%d') if l.end_date else None,
        'status': l.status,
        'remark': l.remark
    } for l in leases]), 200

@lease_bp.route('/leases/<int:id>', methods=['GET'])
def get_lease(id):
    l = Lease.query.get(id)
    if not l:
        return jsonify({"error": "Lease not found"}), 404
    return jsonify({
        'id': l.id,
        'name': l.name,
        'property_id': l.property_id,
        'property_name': l.property.name if l.property else None,
        'tenant_id': l.tenant_id,
        'tenant_name': l.tenant.name if l.tenant else None,
        'rent_amount': l.rent_amount,
        'rent_day': l.rent_day,
        'deposit': l.deposit,
        'start_date': l.start_date.strftime('%Y-%m-%d') if l.start_date else None,
        'end_date': l.end_date.strftime('%Y-%m-%d') if l.end_date else None,
        'status': l.status,
        'remark': l.remark
    }), 200

@lease_bp.route('/leases', methods=['POST'])
def add_lease():
    data = request.get_json()

    property_id = data['property_id']
    exist_active = Lease.query.filter_by(property_id=property_id, status='active').first()
    if exist_active:
        return jsonify({"error": "该房产已有活跃租约"}), 400

    l = Lease(
        name=data.get('name'),
        property_id=property_id,
        tenant_id=data.get('tenant_id'),
        rent_amount=data['rent_amount'],
        rent_day=data.get('rent_day', 1),
        deposit=data.get('deposit', 0),
        start_date=data['start_date'],
        end_date=data['end_date'],
        status='active',
        remark=data.get('remark')
    )
    db.session.add(l)
    db.session.flush()

    generate_payments(l, data.get('start_date'), data.get('end_date'), data['rent_amount'], data.get('rent_day', 1))

    db.session.commit()
    return jsonify({"message": "Lease created", "id": l.id}), 201

def generate_payments(lease, start_date, end_date, rent_amount, rent_day):
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')

    current = datetime(start.year, start.month, rent_day)
    if current < start:
        current = datetime(start.year, start.month + 1, rent_day) if start.month < 12 else datetime(start.year + 1, 1, rent_day)

    while current <= end:
        payment = Payment(
            lease_id=lease.id,
            due_date=current,
            amount=rent_amount,
            status='pending'
        )
        db.session.add(payment)

        if current.month == 12:
            current = datetime(current.year + 1, 1, rent_day)
        else:
            current = datetime(current.year, current.month + 1, rent_day)

@lease_bp.route('/leases/<int:id>', methods=['PUT'])
def update_lease(id):
    l = Lease.query.get(id)
    if not l:
        return jsonify({"error": "Lease not found"}), 404
    data = request.get_json()

    if 'status' in data and data['status'] != l.status:
        l.status = data['status']

    if 'tenant_id' in data:
        l.tenant_id = data['tenant_id']
    if 'rent_amount' in data:
        l.rent_amount = data['rent_amount']
    if 'rent_day' in data:
        l.rent_day = data['rent_day']
    if 'remark' in data:
        l.remark = data['remark']

    db.session.commit()
    return jsonify({"message": "Lease updated"}), 200

@lease_bp.route('/leases/<int:id>', methods=['DELETE'])
def delete_lease(id):
    l = Lease.query.get(id)
    if not l:
        return jsonify({"error": "Lease not found"}), 404

    Payment.query.filter_by(lease_id=id).delete()

    db.session.delete(l)
    db.session.commit()
    return jsonify({"message": "Lease deleted"}), 200
