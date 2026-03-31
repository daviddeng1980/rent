from flask import Blueprint, request, jsonify
from models import Lease, Payment, Property, LeaseChange
from extensions import db
from datetime import datetime, timedelta, date
import json
import calendar

lease_bp = Blueprint('lease', __name__)

# 状态显示映射
STATUS_MAP = {
    'pending': '待生效',
    'active': '进行中',
    'renewed': '已续签',
    'terminated': '已终止',
    'expired': '已到期'
}

def generate_payments(lease):
    """为租约生成付款计划 - 根据租期开始和支付周期自动计算"""
    start = datetime.strptime(lease.start_date.strftime('%Y-%m-%d'), '%Y-%m-%d')
    end = datetime.strptime(lease.end_date.strftime('%Y-%m-%d'), '%Y-%m-%d')
    payment_cycle = lease.payment_cycle or 1  # 默认为月付

    # 第一个付款日是租期开始日
    current = start

    while current <= end:
        # 检查是否已存在
        existing = Payment.query.filter_by(lease_id=lease.id, due_date=current.date()).first()
        if not existing:
            payment = Payment(
                lease_id=lease.id,
                due_date=current.date(),
                amount=lease.rent_amount * payment_cycle,  # 根据支付周期计算金额
                status='pending'
            )
            db.session.add(payment)

        # 根据支付周期计算下一个付款日
        month = current.month + payment_cycle
        year = current.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        day = min(current.day, calendar.monthrange(year, month)[1])  # 防止日期溢出
        current = datetime(year, month, day)

@lease_bp.route('/leases', methods=['GET'])
def get_leases():
    status_filter = request.args.get('status')
    leases = Lease.query.all()
    if status_filter:
        leases = [l for l in leases if l.status == status_filter]

    result = []
    for l in leases:
        item = {
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
            'status_text': STATUS_MAP.get(l.status, l.status),
            'remark': l.remark
        }
        result.append(item)

    return jsonify(result), 200

@lease_bp.route('/leases/<int:id>', methods=['GET'])
def get_lease(id):
    l = Lease.query.get(id)
    if not l:
        return jsonify({"error": "Lease not found"}), 404

    # 获取变更历史
    changes = LeaseChange.query.filter_by(lease_id=id).order_by(LeaseChange.create_time.desc()).all()

    # 获取关联的续签/被续签信息
    renewed_info = None
    original_info = None
    if l.renewed_lease_id:
        renewed = Lease.query.get(l.renewed_lease_id)
        if renewed:
            renewed_info = {'id': renewed.id, 'name': renewed.name}

    if l.original_lease_id:
        original = Lease.query.get(l.original_lease_id)
        if original:
            original_info = {'id': original.id, 'name': original.name}

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
        'status_text': STATUS_MAP.get(l.status, l.status),
        'remark': l.remark,
        'termination_reason': l.termination_reason,
        'termination_date': l.termination_date.strftime('%Y-%m-%d') if l.termination_date else None,
        'contract_files': json.loads(l.contract_files or '[]'),
        'changes': [{
            'id': c.id,
            'change_type': c.change_type,
            'old_values': json.loads(c.old_values) if c.old_values else {},
            'new_values': json.loads(c.new_values) if c.new_values else {},
            'effective_date': c.effective_date.strftime('%Y-%m-%d') if c.effective_date else None,
            'reason': c.reason,
            'create_time': c.create_time.strftime('%Y-%m-%d %H:%M') if c.create_time else None
        } for c in changes],
        'renewed_info': renewed_info,
        'original_info': original_info
    }), 200

@lease_bp.route('/leases', methods=['POST'])
def add_lease():
    """创建租约，初始状态为待生效"""
    data = request.get_json()

    # 日期转换
    try:
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date() if data.get('start_date') else None
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date() if data.get('end_date') else None
    except (ValueError, TypeError) as e:
        return jsonify({"error": f"日期格式错误: {str(e)}，正确格式：YYYY-MM-DD"}), 400

    # 检查房产是否已有生效中的租约
    property_id = data['property_id']
    if data.get('activate_now'):
        active = Lease.query.filter_by(property_id=property_id, status='active').first()
        if active:
            return jsonify({"error": "该房产已有生效中的租约"}), 400

    l = Lease(
        name=data.get('name'),
        property_id=property_id,
        tenant_id=data.get('tenant_id'),
        rent_amount=data['rent_amount'],
        rent_day=data.get('rent_day', 1),
        payment_cycle=data.get('payment_cycle', 1),
        deposit=data.get('deposit', 0),
        start_date=start_date,
        end_date=end_date,
        status='pending',
        remark=data.get('remark')
    )
    db.session.add(l)
    db.session.flush()

    # 如果要求立即生效
    if data.get('activate_now'):
        if not l.tenant_id:
            return jsonify({"error": "请先选择租客"}), 400
        l.status = 'active'
        generate_payments(l)
        # Property.status 是计算属性，会自动根据 active lease 状态返回正确值

    db.session.commit()
    return jsonify({"message": "租约创建成功", "id": l.id, "status": l.status}), 201

@lease_bp.route('/leases/<int:id>/activate', methods=['POST'])
def activate_lease(id):
    """确认租约生效"""
    l = Lease.query.get(id)
    if not l:
        return jsonify({"error": "Lease not found"}), 404

    if l.status != 'pending':
        return jsonify({"error": "只有待生效的租约可以确认生效"}), 400

    if not l.tenant_id:
        return jsonify({"error": "请先选择租客才能生效"}), 400

    # 检查房产是否已有生效中的租约
    active = Lease.query.filter_by(property_id=l.property_id, status='active').first()
    if active and active.id != id:
        return jsonify({"error": "该房产已有生效中的租约"}), 400

    l.status = 'active'
    generate_payments(l)
    # Property.status 是计算属性，会自动根据 active lease 状态返回正确值

    db.session.commit()
    return jsonify({"message": "租约已生效", "id": l.id}), 200

@lease_bp.route('/leases/<int:id>/renew', methods=['POST'])
def renew_lease(id):
    """续签租约"""
    l = Lease.query.get(id)
    if not l:
        return jsonify({"error": "Lease not found"}), 404

    data = request.get_json()
    new_start = data.get('start_date')
    new_end = data.get('end_date')

    # 创建新租约
    new_lease = Lease(
        name=data.get('name') or f"{l.name}-续签",
        property_id=l.property_id,
        tenant_id=l.tenant_id,
        rent_amount=data.get('rent_amount', l.rent_amount),
        rent_day=data.get('rent_day', l.rent_day),
        deposit=data.get('deposit', l.deposit),
        start_date=new_start,
        end_date=new_end,
        status='pending',  # 新租约也是待生效
        original_lease_id=l.id,
        remark=data.get('remark', l.remark)
    )
    db.session.add(new_lease)
    db.session.flush()

    # 原租约标记为已续签
    l.status = 'renewed'
    l.renewed_lease_id = new_lease.id

    # 如果要求立即生效
    if data.get('activate_now'):
        if not new_lease.tenant_id:
            return jsonify({"error": "请先选择租客"}), 400
        new_lease.status = 'active'
        generate_payments(new_lease)

        # 检查原租约是否需要处理
        active_leases = Lease.query.filter_by(property_id=l.property_id, status='active').all()
        for active in active_leases:
            active.status = 'renewed'

    db.session.commit()
    return jsonify({"message": "租约续签成功", "id": new_lease.id, "original_id": l.id}), 201

@lease_bp.route('/leases/<int:id>/amend', methods=['POST'])
def amend_lease(id):
    """变更租约"""
    l = Lease.query.get(id)
    if not l:
        return jsonify({"error": "Lease not found"}), 404

    if l.status != 'active':
        return jsonify({"error": "只有生效中的租约可以变更"}), 400

    data = request.get_json()
    old_values = {}
    new_values = {}

    # 记录变更
    if 'rent_amount' in data and data['rent_amount'] != l.rent_amount:
        old_values['rent_amount'] = l.rent_amount
        new_values['rent_amount'] = data['rent_amount']
        l.rent_amount = data['rent_amount']

    if 'payment_cycle' in data and data['payment_cycle'] != l.payment_cycle:
        old_values['payment_cycle'] = l.payment_cycle
        new_values['payment_cycle'] = data['payment_cycle']
        l.payment_cycle = data['payment_cycle']

    if 'deposit' in data and data['deposit'] != l.deposit:
        old_values['deposit'] = l.deposit
        new_values['deposit'] = data['deposit']
        l.deposit = data['deposit']

    if 'remark' in data:
        old_values['remark'] = l.remark
        new_values['remark'] = data['remark']
        l.remark = data['remark']

    if not old_values:
        return jsonify({"error": "没有需要变更的字段"}), 400

    effective_date = data.get('effective_date')
    if effective_date:
        effective_date = datetime.strptime(effective_date, '%Y-%m-%d').date()

    change = LeaseChange(
        lease_id=l.id,
        change_type='amendment',
        old_values=json.dumps(old_values),
        new_values=json.dumps(new_values),
        effective_date=effective_date,
        reason=data.get('reason')
    )
    db.session.add(change)
    db.session.commit()

    return jsonify({"message": "租约变更成功", "change_id": change.id}), 200

@lease_bp.route('/leases/<int:id>/terminate', methods=['POST'])
def terminate_lease(id):
    """终止租约"""
    l = Lease.query.get(id)
    if not l:
        return jsonify({"error": "Lease not found"}), 404

    if l.status != 'active':
        return jsonify({"error": "只有生效中的租约可以终止"}), 400

    data = request.get_json()
    termination_date = data.get('termination_date')
    termination_reason = data.get('termination_reason')

    if not termination_date:
        return jsonify({"error": "请选择终止日期"}), 400

    termination_date = datetime.strptime(termination_date, '%Y-%m-%d').date()

    # 记录终止前的状态
    old_values = {
        'status': l.status,
        'end_date': l.end_date.strftime('%Y-%m-%d') if l.end_date else None
    }

    # 更新租约状态
    l.status = 'terminated'
    l.termination_reason = termination_reason
    l.termination_date = termination_date

    # 将终止日期之后未付的款项标记为已取消
    payments = Payment.query.filter(
        Payment.lease_id == id,
        Payment.due_date > termination_date,
        Payment.status == 'pending'
    ).all()
    for p in payments:
        p.status = 'cancelled'

    # 更新房产状态为空置
    # 检查是否还有其他生效中的租约
    other_active = Lease.query.filter(
        Lease.property_id == l.property_id,
        Lease.status == 'active',
        Lease.id != id
    ).first()
    # Property.status 是计算属性，会自动根据 active lease 状态返回正确值

    # 记录变更历史
    change = LeaseChange(
        lease_id=l.id,
        change_type='termination',
        old_values=json.dumps(old_values),
        new_values=json.dumps({
            'status': 'terminated',
            'termination_reason': termination_reason,
            'termination_date': termination_date.strftime('%Y-%m-%d')
        }),
        effective_date=termination_date,
        reason=data.get('remark')
    )
    db.session.add(change)
    db.session.commit()

    return jsonify({"message": "租约已终止", "id": l.id}), 200

@lease_bp.route('/leases/<int:id>/changes', methods=['GET'])
def get_lease_changes(id):
    """获取租约变更历史"""
    l = Lease.query.get(id)
    if not l:
        return jsonify({"error": "Lease not found"}), 404

    changes = LeaseChange.query.filter_by(lease_id=id).order_by(LeaseChange.create_time.desc()).all()
    return jsonify([{
        'id': c.id,
        'change_type': c.change_type,
        'old_values': json.loads(c.old_values) if c.old_values else {},
        'new_values': json.loads(c.new_values) if c.new_values else {},
        'effective_date': c.effective_date.strftime('%Y-%m-%d') if c.effective_date else None,
        'reason': c.reason,
        'create_time': c.create_time.strftime('%Y-%m-%d %H:%M') if c.create_time else None
    } for c in changes]), 200

@lease_bp.route('/leases/<int:id>', methods=['PUT'])
def update_lease(id):
    """更新租约基本信息"""
    l = Lease.query.get(id)
    if not l:
        return jsonify({"error": "Lease not found"}), 404

    data = request.get_json()

    if 'name' in data:
        l.name = data['name']
    if 'tenant_id' in data:
        l.tenant_id = data['tenant_id']
    if 'remark' in data:
        l.remark = data['remark']

    db.session.commit()
    return jsonify({"message": "Lease updated"}), 200

@lease_bp.route('/leases/<int:id>', methods=['DELETE'])
def delete_lease(id):
    """删除租约（仅允许删除待生效状态的租约）"""
    l = Lease.query.get(id)
    if not l:
        return jsonify({"error": "Lease not found"}), 404

    if l.status != 'pending':
        return jsonify({"error": "只能删除待生效的租约"}), 400

    # 删除关联的付款记录
    Payment.query.filter_by(lease_id=id).delete()

    db.session.delete(l)
    db.session.commit()
    return jsonify({"message": "Lease deleted"}), 200
