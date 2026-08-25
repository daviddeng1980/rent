"""
租金管理系统 MCP Server
基于 FastMCP 2.0，将租金管理系统的核心能力以 MCP 协议暴露给 AI 智能体。
支持 stdio（本地 Agent）和 streamable-http（远程 Agent）两种传输方式。
"""

import sys
import os
import json
import argparse
import calendar
from datetime import datetime, date, timedelta
from typing import Optional

from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Flask 应用上下文初始化（复用现有 models 和数据库）
# ---------------------------------------------------------------------------
from flask import Flask
from extensions import db
from models import Property, Lease, Tenant, Payment, LeaseChange

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rent_management.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# ---------------------------------------------------------------------------
# MCP Server 实例
# ---------------------------------------------------------------------------
mcp = FastMCP("rent-management")

# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

STATUS_MAP = {
    'pending': '待生效', 'active': '进行中', 'renewed': '已续签',
    'terminated': '已终止', 'expired': '已到期'
}
PAYMENT_STATUS_MAP = {
    'pending': '未到期', 'overdue': '逾期', 'paid': '已缴纳', 'cancelled': '已取消'
}


def _serialize_property(p: Property) -> dict:
    images = []
    try:
        images = json.loads(p.images) if p.images else []
    except Exception:
        pass
    return {
        'id': p.id, 'name': p.name, 'address': p.address,
        'area': p.area, 'property_type': p.property_type,
        'decoration': p.decoration, 'furniture': p.furniture,
        'rent_guide': p.rent_guide,
        'purchase_date': p.purchase_date.strftime('%Y-%m-%d') if p.purchase_date else None,
        'purchase_price': p.purchase_price,
        'loan_amount': p.loan_amount, 'loan_rate': p.loan_rate,
        'property_fee': p.property_fee, 'remark': p.remark,
        'images': images, 'status': p.status,
    }


def _serialize_tenant(t: Tenant) -> dict:
    return {
        'id': t.id, 'name': t.name, 'phone': t.phone,
        'id_card': t.id_card,
        'emergency_contact': t.emergency_contact,
        'emergency_phone': t.emergency_phone, 'remark': t.remark,
    }


def _serialize_lease(l: Lease) -> dict:
    return {
        'id': l.id, 'name': l.name,
        'property_id': l.property_id,
        'property_name': l.property.name if l.property else None,
        'tenant_id': l.tenant_id,
        'tenant_name': l.tenant.name if l.tenant else None,
        'rent_amount': l.rent_amount, 'rent_day': l.rent_day,
        'payment_cycle': l.payment_cycle, 'deposit': l.deposit,
        'start_date': l.start_date.strftime('%Y-%m-%d') if l.start_date else None,
        'end_date': l.end_date.strftime('%Y-%m-%d') if l.end_date else None,
        'status': l.status, 'status_text': STATUS_MAP.get(l.status, l.status),
        'remark': l.remark,
    }


def _get_payment_status(payment: Payment) -> str:
    if payment.status in ('paid', 'cancelled'):
        return payment.status
    if payment.due_date < date.today():
        return 'overdue'
    return 'pending'


def _serialize_payment(p: Payment) -> dict:
    current_status = _get_payment_status(p)
    return {
        'id': p.id, 'lease_id': p.lease_id,
        'lease_name': p.lease.name if p.lease else None,
        'property_name': p.lease.property.name if p.lease and p.lease.property else None,
        'tenant_name': p.lease.tenant.name if p.lease and p.lease.tenant else None,
        'due_date': p.due_date.strftime('%Y-%m-%d') if p.due_date else None,
        'amount': p.amount, 'status': p.status,
        'current_status': current_status,
        'status_text': PAYMENT_STATUS_MAP.get(current_status, current_status),
        'paid_date': p.paid_date.strftime('%Y-%m-%d') if p.paid_date else None,
        'remark': p.remark,
        'days_until_due': (p.due_date - date.today()).days if p.due_date else None,
    }


def _generate_payments(lease: Lease):
    """为租约生成付款计划"""
    start = datetime.strptime(lease.start_date.strftime('%Y-%m-%d'), '%Y-%m-%d')
    end = datetime.strptime(lease.end_date.strftime('%Y-%m-%d'), '%Y-%m-%d')
    payment_cycle = lease.payment_cycle or 1
    current = start
    while current <= end:
        existing = Payment.query.filter_by(lease_id=lease.id, due_date=current.date()).first()
        if not existing:
            payment = Payment(
                lease_id=lease.id, due_date=current.date(),
                amount=lease.rent_amount * payment_cycle, status='pending',
            )
            db.session.add(payment)
        month = current.month + payment_cycle
        year = current.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        day = min(current.day, calendar.monthrange(year, month)[1])
        current = datetime(year, month, day)


# ===========================================================================
#  Tools — 房产
# ===========================================================================

@mcp.tool()
def list_properties() -> list[dict]:
    """列出所有房产及其当前状态（出租中/空置）"""
    with app.app_context():
        return [_serialize_property(p) for p in Property.query.all()]


@mcp.tool()
def get_property(property_id: int) -> dict:
    """获取指定房产的详细信息，包括贷款、物业费、图片等"""
    with app.app_context():
        p = Property.query.get(property_id)
        if not p:
            return {"error": f"房产 ID {property_id} 不存在"}
        return _serialize_property(p)


@mcp.tool()
def add_property(
    name: str,
    address: str,
    area: Optional[float] = None,
    property_type: Optional[str] = None,
    decoration: Optional[str] = None,
    furniture: Optional[str] = None,
    rent_guide: Optional[float] = None,
    purchase_date: Optional[str] = None,
    purchase_price: float = 0,
    loan_amount: float = 0,
    loan_rate: float = 0,
    property_fee: float = 0,
    remark: Optional[str] = None,
) -> dict:
    """添加新房产。日期格式 YYYY-MM-DD"""
    with app.app_context():
        try:
            p = Property(
                name=name, address=address, area=area,
                property_type=property_type, decoration=decoration,
                furniture=furniture, rent_guide=rent_guide,
                purchase_price=purchase_price, loan_amount=loan_amount,
                loan_rate=loan_rate, property_fee=property_fee,
                remark=remark, images='[]',
            )
            if purchase_date:
                p.purchase_date = datetime.strptime(purchase_date, '%Y-%m-%d').date()
            db.session.add(p)
            db.session.commit()
            return {"message": "房产添加成功", "id": p.id, "status": p.status}
        except Exception as e:
            db.session.rollback()
            return {"error": f"添加房产失败: {str(e)}"}


@mcp.tool()
def update_property(
    property_id: int,
    name: Optional[str] = None,
    address: Optional[str] = None,
    area: Optional[float] = None,
    property_type: Optional[str] = None,
    decoration: Optional[str] = None,
    furniture: Optional[str] = None,
    rent_guide: Optional[float] = None,
    purchase_price: Optional[float] = None,
    loan_amount: Optional[float] = None,
    loan_rate: Optional[float] = None,
    property_fee: Optional[float] = None,
    remark: Optional[str] = None,
    purchase_date: Optional[str] = None,
) -> dict:
    """更新房产信息。只需传入要修改的字段，日期格式 YYYY-MM-DD"""
    with app.app_context():
        p = Property.query.get(property_id)
        if not p:
            return {"error": f"房产 ID {property_id} 不存在"}
        updates = {
            'name': name, 'address': address, 'area': area,
            'property_type': property_type, 'decoration': decoration,
            'furniture': furniture, 'rent_guide': rent_guide,
            'purchase_price': purchase_price, 'loan_amount': loan_amount,
            'loan_rate': loan_rate, 'property_fee': property_fee,
            'remark': remark,
        }
        for key, value in updates.items():
            if value is not None:
                setattr(p, key, value)
        if purchase_date:
            p.purchase_date = datetime.strptime(purchase_date, '%Y-%m-%d').date()
        db.session.commit()
        return {"message": "房产更新成功", "status": p.status}


@mcp.tool()
def delete_property(property_id: int) -> dict:
    """删除房产（需无活跃租约）"""
    with app.app_context():
        p = Property.query.get(property_id)
        if not p:
            return {"error": f"房产 ID {property_id} 不存在"}
        active_lease = Lease.query.filter_by(property_id=property_id, status='active').first()
        if active_lease:
            return {"error": "无法删除：该房产有活跃租约"}
        Lease.query.filter_by(property_id=property_id).delete()
        db.session.delete(p)
        db.session.commit()
        return {"message": "房产删除成功"}


# ===========================================================================
#  Tools — 租客
# ===========================================================================

@mcp.tool()
def list_tenants() -> list[dict]:
    """列出所有租客"""
    with app.app_context():
        return [_serialize_tenant(t) for t in Tenant.query.all()]


@mcp.tool()
def get_tenant(tenant_id: int) -> dict:
    """获取指定租客的详细信息"""
    with app.app_context():
        t = Tenant.query.get(tenant_id)
        if not t:
            return {"error": f"租客 ID {tenant_id} 不存在"}
        return _serialize_tenant(t)


@mcp.tool()
def add_tenant(
    name: str,
    phone: str,
    id_card: Optional[str] = None,
    emergency_contact: Optional[str] = None,
    emergency_phone: Optional[str] = None,
    remark: Optional[str] = None,
) -> dict:
    """添加新租客。手机号需11位（1开头），身份证18位（可选）"""
    import re
    with app.app_context():
        # 验证手机号
        if not re.match(r'^1[3-9]\d{9}$', phone):
            return {"error": "手机号格式错误，应为11位数字（以1开头）"}
        # 验证身份证（可选）
        if id_card:
            if not re.match(r'^[1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$', id_card):
                return {"error": "身份证号格式错误，应为18位"}
        try:
            t = Tenant(
                name=name, phone=phone, id_card=id_card,
                emergency_contact=emergency_contact,
                emergency_phone=emergency_phone, remark=remark,
            )
            db.session.add(t)
            db.session.commit()
            return {"message": "租客添加成功", "id": t.id}
        except Exception as e:
            db.session.rollback()
            return {"error": f"添加租客失败: {str(e)}"}


# ===========================================================================
#  Tools — 租约
# ===========================================================================

@mcp.tool()
def list_leases(status: Optional[str] = None) -> list[dict]:
    """列出租约，可按状态筛选: pending(待生效)/active(进行中)/renewed(已续签)/terminated(已终止)/expired(已到期)"""
    with app.app_context():
        leases = Lease.query.all()
        if status:
            leases = [l for l in leases if l.status == status]
        return [_serialize_lease(l) for l in leases]


@mcp.tool()
def get_lease(lease_id: int) -> dict:
    """获取租约详情，包含变更历史和续签信息"""
    with app.app_context():
        l = Lease.query.get(lease_id)
        if not l:
            return {"error": f"租约 ID {lease_id} 不存在"}
        result = _serialize_lease(l)
        # 变更历史
        changes = LeaseChange.query.filter_by(lease_id=lease_id).order_by(LeaseChange.create_time.desc()).all()
        result['changes'] = [{
            'change_type': c.change_type,
            'old_values': json.loads(c.old_values) if c.old_values else {},
            'new_values': json.loads(c.new_values) if c.new_values else {},
            'effective_date': c.effective_date.strftime('%Y-%m-%d') if c.effective_date else None,
            'reason': c.reason,
            'create_time': c.create_time.strftime('%Y-%m-%d %H:%M') if c.create_time else None,
        } for c in changes]
        return result


@mcp.tool()
def create_lease(
    property_id: int,
    tenant_id: int,
    rent_amount: float,
    start_date: str,
    end_date: str,
    name: Optional[str] = None,
    rent_day: int = 1,
    payment_cycle: int = 1,
    deposit: float = 0,
    activate_now: bool = False,
    remark: Optional[str] = None,
) -> dict:
    """创建租约。日期格式 YYYY-MM-DD。payment_cycle: 1=月付, 3=季付, 6=半年付, 12=年付。activate_now=True 则立即生效并生成付款计划。"""
    with app.app_context():
        try:
            sd = datetime.strptime(start_date, '%Y-%m-%d').date()
            ed = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError as e:
            return {"error": f"日期格式错误: {e}"}

        if activate_now:
            active = Lease.query.filter_by(property_id=property_id, status='active').first()
            if active:
                return {"error": "该房产已有生效中的租约"}

        l = Lease(
            name=name, property_id=property_id, tenant_id=tenant_id,
            rent_amount=rent_amount, rent_day=rent_day,
            payment_cycle=payment_cycle, deposit=deposit,
            start_date=sd, end_date=ed, status='pending', remark=remark,
        )
        db.session.add(l)
        db.session.flush()

        if activate_now:
            l.status = 'active'
            _generate_payments(l)

        db.session.commit()
        return {"message": "租约创建成功", "id": l.id, "status": l.status}


@mcp.tool()
def activate_lease(lease_id: int) -> dict:
    """激活租约（从待生效变为进行中），自动生成付款计划"""
    with app.app_context():
        l = Lease.query.get(lease_id)
        if not l:
            return {"error": f"租约 ID {lease_id} 不存在"}
        if l.status != 'pending':
            return {"error": "只有待生效的租约可以激活"}
        if not l.tenant_id:
            return {"error": "请先指定租客"}
        active = Lease.query.filter_by(property_id=l.property_id, status='active').first()
        if active and active.id != lease_id:
            return {"error": "该房产已有生效中的租约"}
        l.status = 'active'
        _generate_payments(l)
        db.session.commit()
        return {"message": "租约已激活", "id": l.id}


@mcp.tool()
def terminate_lease(lease_id: int, termination_date: str, termination_reason: Optional[str] = None) -> dict:
    """终止租约。termination_date 格式 YYYY-MM-DD"""
    with app.app_context():
        l = Lease.query.get(lease_id)
        if not l:
            return {"error": f"租约 ID {lease_id} 不存在"}
        if l.status != 'active':
            return {"error": "只有生效中的租约可以终止"}
        try:
            td = datetime.strptime(termination_date, '%Y-%m-%d').date()
        except ValueError:
            return {"error": "日期格式错误，应为 YYYY-MM-DD"}

        l.status = 'terminated'
        l.termination_reason = termination_reason
        l.termination_date = td

        # 取消终止日期之后的待付付款
        payments = Payment.query.filter(
            Payment.lease_id == lease_id,
            Payment.due_date > td,
            Payment.status == 'pending',
        ).all()
        for p in payments:
            p.status = 'cancelled'

        change = LeaseChange(
            lease_id=l.id, change_type='termination',
            old_values=json.dumps({'status': 'active'}),
            new_values=json.dumps({'status': 'terminated', 'termination_date': termination_date}),
            effective_date=td, reason=termination_reason,
        )
        db.session.add(change)
        db.session.commit()
        return {"message": "租约已终止", "id": l.id}


# ===========================================================================
#  Tools — 付款
# ===========================================================================

@mcp.tool()
def list_payments(
    status: Optional[str] = None,
    lease_id: Optional[int] = None,
) -> list[dict]:
    """列出付款记录。status 可选: pending/overdue/paid。可按 lease_id 筛选。"""
    with app.app_context():
        payments = Payment.query.all()
        result = []
        for p in payments:
            current_status = _get_payment_status(p)
            if status and status != current_status:
                continue
            if lease_id and p.lease_id != lease_id:
                continue
            result.append(_serialize_payment(p))
        result.sort(key=lambda x: x['due_date'] or '')
        return result


@mcp.tool()
def mark_payment_paid(payment_id: int) -> dict:
    """标记指定付款记录为已缴纳"""
    with app.app_context():
        p = Payment.query.get(payment_id)
        if not p:
            return {"error": f"付款记录 ID {payment_id} 不存在"}
        if p.status == 'paid':
            return {"message": "该付款记录已是已缴纳状态"}
        p.status = 'paid'
        p.paid_date = date.today()
        db.session.commit()
        return {"message": "付款已标记为已缴纳", "paid_date": p.paid_date.strftime('%Y-%m-%d')}


# ===========================================================================
#  Tools — 分析
# ===========================================================================

@mcp.tool()
def get_summary() -> dict:
    """获取全局经营概览：房产总数、出租率、月租金收入、年度利润等"""
    with app.app_context():
        properties = Property.query.all()
        total = len(properties)
        rented = sum(1 for p in properties if p.status == '出租中')
        vacant = total - rented

        total_monthly = 0
        total_annual = 0
        total_loan_cost = 0
        total_fee = 0

        for p in properties:
            active = Lease.query.filter_by(property_id=p.id, status='active').first()
            if active:
                total_monthly += active.rent_amount
                total_annual += active.rent_amount * 12
            if p.loan_amount and p.loan_rate:
                total_loan_cost += p.loan_amount * p.loan_rate
            if p.property_fee:
                total_fee += p.property_fee * 12

        return {
            'total_properties': total,
            'rented_count': rented,
            'vacant_count': vacant,
            'occupancy_rate': f"{(rented / total * 100):.1f}%" if total else "0%",
            'income': {'monthly': total_monthly, 'annual': total_annual},
            'costs': {'loan': total_loan_cost, 'property_fee': total_fee, 'total': total_loan_cost + total_fee},
            'annual_profit': total_annual - (total_loan_cost + total_fee),
        }


@mcp.tool()
def analyze_property(property_id: int) -> dict:
    """分析单个房产的年度利润：租金收入、贷款成本、物业费、净利润"""
    with app.app_context():
        p = Property.query.get(property_id)
        if not p:
            return {"error": f"房产 ID {property_id} 不存在"}
        active = Lease.query.filter_by(property_id=property_id, status='active').first()
        rent = active.rent_amount if active else 0
        loan_cost = (p.loan_amount * p.loan_rate) if p.loan_amount and p.loan_rate else 0
        fee_year = (p.property_fee * 12) if p.property_fee else 0
        annual_income = rent * 12
        return {
            'property': {'id': p.id, 'name': p.name, 'address': p.address, 'status': p.status},
            'income': {'monthly': rent, 'annual': annual_income},
            'costs': {'loan': loan_cost, 'property_fee': fee_year, 'total': loan_cost + fee_year},
            'annual_profit': annual_income - (loan_cost + fee_year),
        }


@mcp.tool()
def get_rent_reminders(days: int = 30) -> list[dict]:
    """获取未来 N 天内即将到期的租金提醒（默认30天）"""
    with app.app_context():
        today = date.today()
        end = today + timedelta(days=days)
        payments = Payment.query.filter(
            Payment.due_date >= today,
            Payment.due_date <= end,
            Payment.status.in_(['pending']),
        ).all()
        result = []
        for p in payments:
            result.append({
                'property_name': p.lease.property.name if p.lease and p.lease.property else None,
                'tenant_name': p.lease.tenant.name if p.lease and p.lease.tenant else None,
                'due_date': p.due_date.strftime('%Y-%m-%d'),
                'amount': p.amount,
                'days_until_due': (p.due_date - today).days,
            })
        result.sort(key=lambda x: x['due_date'] or '')
        return result


# ===========================================================================
#  Resources — 只读数据暴露
# ===========================================================================

@mcp.resource("rent://properties")
def resource_properties() -> str:
    """所有房产列表"""
    with app.app_context():
        return json.dumps([_serialize_property(p) for p in Property.query.all()], ensure_ascii=False, indent=2)


@mcp.resource("rent://leases/active")
def resource_active_leases() -> str:
    """当前进行中的租约"""
    with app.app_context():
        leases = Lease.query.filter_by(status='active').all()
        return json.dumps([_serialize_lease(l) for l in leases], ensure_ascii=False, indent=2)


@mcp.resource("rent://payments/overdue")
def resource_overdue_payments() -> str:
    """所有逾期未付的付款记录"""
    with app.app_context():
        payments = Payment.query.all()
        overdue = [p for p in payments if _get_payment_status(p) == 'overdue']
        return json.dumps([_serialize_payment(p) for p in overdue], ensure_ascii=False, indent=2)


@mcp.resource("rent://summary")
def resource_summary() -> str:
    """经营概览"""
    with app.app_context():
        properties = Property.query.all()
        total = len(properties)
        rented = sum(1 for p in properties if p.status == '出租中')
        total_monthly = 0
        for p in properties:
            active = Lease.query.filter_by(property_id=p.id, status='active').first()
            if active:
                total_monthly += active.rent_amount
        return json.dumps({
            'total_properties': total,
            'rented_count': rented,
            'vacant_count': total - rented,
            'monthly_income': total_monthly,
        }, ensure_ascii=False, indent=2)


# ===========================================================================
#  启动入口
# ===========================================================================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='租金管理系统 MCP Server')
    parser.add_argument('--transport', choices=['stdio', 'http'], default='stdio',
                        help='传输方式: stdio (本地Agent) 或 http (远程Agent)')
    parser.add_argument('--port', type=int, default=8000, help='HTTP 模式端口 (默认 8000)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='HTTP 模式监听地址 (默认 0.0.0.0)')
    args = parser.parse_args()

    if args.transport == 'http':
        print(f"Starting MCP Server (HTTP) on {args.host}:{args.port}")
        mcp.run(transport='streamable-http', host=args.host, port=args.port)
    else:
        mcp.run(transport='stdio')
