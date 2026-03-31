from flask import Blueprint, request, jsonify
from models import Payment, Lease
from extensions import db
from datetime import datetime

payment_bp = Blueprint('payment', __name__)

@payment_bp.route('/payments', methods=['GET'])
def get_payments():
    payments = Payment.query.all()
    return jsonify([{
        'id': p.id,
        'lease_id': p.lease_id,
        'lease_name': p.lease.name if p.lease else None,
        'property_id': p.lease.property_id if p.lease else None,
        'property_name': p.lease.property.name if p.lease and p.lease.property else None,
        'due_date': p.due_date.strftime('%Y-%m-%d') if p.due_date else None,
        'amount': p.amount,
        'status': p.status,
        'paid_date': p.paid_date.strftime('%Y-%m-%d') if p.paid_date else None,
        'remark': p.remark
    } for p in payments]), 200

@payment_bp.route('/payments/<int:id>', methods=['GET'])
def get_payment(id):
    p = Payment.query.get(id)
    if not p:
        return jsonify({"error": "Payment not found"}), 404
    return jsonify({
        'id': p.id,
        'lease_id': p.lease_id,
        'lease_name': p.lease.name if p.lease else None,
        'property_id': p.lease.property_id if p.lease else None,
        'property_name': p.lease.property.name if p.lease and p.lease.property else None,
        'due_date': p.due_date.strftime('%Y-%m-%d') if p.due_date else None,
        'amount': p.amount,
        'status': p.status,
        'paid_date': p.paid_date.strftime('%Y-%m-%d') if p.paid_date else None,
        'remark': p.remark
    }), 200

@payment_bp.route('/payments/<int:id>', methods=['PUT'])
def update_payment(id):
    p = Payment.query.get(id)
    if not p:
        return jsonify({"error": "Payment not found"}), 404
    data = request.get_json()

    if 'status' in data:
        p.status = data['status']
        if data['status'] == 'paid' and not p.paid_date:
            p.paid_date = datetime.now().strftime('%Y-%m-%d')
        elif data['status'] == 'pending':
            p.paid_date = None
    if 'remark' in data:
        p.remark = data['remark']

    db.session.commit()
    return jsonify({"message": "Payment updated"}), 200

@payment_bp.route('/payments/<int:id>', methods=['DELETE'])
def delete_payment(id):
    p = Payment.query.get(id)
    if not p:
        return jsonify({"error": "Payment not found"}), 404
    db.session.delete(p)
    db.session.commit()
    return jsonify({"message": "Payment deleted"}), 200
