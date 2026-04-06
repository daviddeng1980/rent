from flask import Blueprint, request, jsonify
from models import Payment, Lease
from extensions import db
from datetime import datetime, timedelta, date

payment_bp = Blueprint('payment', __name__)

STATUS_MAP = {
    'pending': '未到期',
    'overdue': '逾期',
    'paid': '已缴纳',
    'cancelled': '已取消'
}

def get_payment_status(payment):
    """根据当前日期和状态计算支付状态"""
    if payment.status in ('paid', 'cancelled'):
        return payment.status
    today = date.today()
    if payment.due_date < today:
        return 'overdue'
    return 'pending'

@payment_bp.route('/payments', methods=['GET'])
def get_payments():
    status_filter = request.args.get('status')  # pending/overdue/paid
    lease_id = request.args.get('lease_id')

    payments = Payment.query.all()

    result = []
    for p in payments:
        current_status = get_payment_status(p)

        # 应用筛选
        if status_filter and status_filter != current_status:
            continue
        if lease_id and p.lease_id != int(lease_id):
            continue

        item = {
            'id': p.id,
            'lease_id': p.lease_id,
            'lease_name': p.lease.name if p.lease else None,
            'property_id': p.lease.property_id if p.lease else None,
            'property_name': p.lease.property.name if p.lease and p.lease.property else None,
            'tenant_name': p.lease.tenant.name if p.lease and p.lease.tenant else None,
            'due_date': p.due_date.strftime('%Y-%m-%d') if p.due_date else None,
            'amount': p.amount,
            'status': p.status,
            'current_status': current_status,  # 实时计算的状态
            'status_text': STATUS_MAP.get(current_status, current_status),
            'paid_date': p.paid_date.strftime('%Y-%m-%d') if p.paid_date else None,
            'remark': p.remark,
            'days_until_due': (p.due_date - date.today()).days if p.due_date else None
        }
        result.append(item)

    # 按到期日期排序
    result.sort(key=lambda x: x['due_date'] or '')
    return jsonify(result), 200

@payment_bp.route('/payments/<int:id>', methods=['GET'])
def get_payment(id):
    p = Payment.query.get(id)
    if not p:
        return jsonify({"error": "Payment not found"}), 404

    current_status = get_payment_status(p)

    return jsonify({
        'id': p.id,
        'lease_id': p.lease_id,
        'lease_name': p.lease.name if p.lease else None,
        'property_id': p.lease.property_id if p.lease else None,
        'property_name': p.lease.property.name if p.lease and p.lease.property else None,
        'tenant_name': p.lease.tenant.name if p.lease and p.lease.tenant else None,
        'due_date': p.due_date.strftime('%Y-%m-%d') if p.due_date else None,
        'amount': p.amount,
        'status': p.status,
        'current_status': current_status,
        'status_text': STATUS_MAP.get(current_status, current_status),
        'paid_date': p.paid_date.strftime('%Y-%m-%d') if p.paid_date else None,
        'remark': p.remark,
        'days_until_due': (p.due_date - date.today()).days if p.due_date else None
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
            p.paid_date = datetime.now().date()
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

    if p.status == 'paid':
        return jsonify({"error": "已缴纳的付款记录不能删除"}), 400

    db.session.delete(p)
    db.session.commit()
    return jsonify({"message": "Payment deleted"}), 200

@payment_bp.route('/reminders', methods=['GET'])
def get_reminders():
    """获取30天内即将到期的租金提醒"""
    days = request.args.get('days', 30, type=int)
    today = date.today()
    end_date = today + timedelta(days=days)

    payments = Payment.query.filter(
        Payment.due_date >= today,
        Payment.due_date <= end_date,
        Payment.status.in_(['pending'])
    ).all()

    result = []
    for p in payments:
        item = {
            'id': p.id,
            'lease_id': p.lease_id,
            'lease_name': p.lease.name if p.lease else None,
            'property_id': p.lease.property_id if p.lease else None,
            'property_name': p.lease.property.name if p.lease and p.lease.property else None,
            'tenant_name': p.lease.tenant.name if p.lease and p.lease.tenant else None,
            'due_date': p.due_date.strftime('%Y-%m-%d') if p.due_date else None,
            'amount': p.amount,
            'days_until_due': (p.due_date - today).days if p.due_date else None,
            'is_overdue': p.due_date < today
        }
        result.append(item)

    # 按到期日期排序
    result.sort(key=lambda x: x['due_date'] or '')
    return jsonify(result), 200
