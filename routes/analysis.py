from flask import Blueprint, jsonify
from models import Property, Lease, Payment
from extensions import db

analysis_bp = Blueprint('analysis', __name__)

@analysis_bp.route('/analysis/property/<int:property_id>', methods=['GET'])
def analyze_property(property_id):
    property = Property.query.get(property_id)
    if not property:
        return jsonify({"error": "Property not found"}), 404

    active_lease = Lease.query.filter_by(property_id=property_id, status='active').first()

    loan_cost = property.loan_amount * property.loan_rate if property.loan_amount and property.loan_rate else 0
    property_fee_year = property.property_fee * 12 if property.property_fee else 0
    opportunity_cost = property.purchase_price * 0.03 if property.purchase_price else 0

    rent_amount = active_lease.rent_amount if active_lease else 0
    rental_income = rent_amount * 12

    profit = rental_income - loan_cost - property_fee_year - opportunity_cost

    return jsonify({
        'property': {
            'id': property.id,
            'name': property.name,
            'address': property.address,
            'status': property.status
        },
        'income': {
            'monthly_rent': rent_amount,
            'annual_rent': rental_income
        },
        'costs': {
            'loan_cost': loan_cost,
            'property_fee': property_fee_year,
            'opportunity_cost': opportunity_cost,
            'total': loan_cost + property_fee_year + opportunity_cost
        },
        'profit': profit
    }), 200

@analysis_bp.route('/analysis/summary', methods=['GET'])
def summary():
    properties = Property.query.all()

    total_properties = len(properties)
    rented_count = sum(1 for p in properties if p.status == '出租中')
    vacant_count = total_properties - rented_count

    total_monthly_rent = 0
    total_annual_rent = 0
    total_loan_cost = 0
    total_property_fee = 0
    total_opportunity_cost = 0

    for p in properties:
        active_lease = Lease.query.filter_by(property_id=p.id, status='active').first()
        if active_lease:
            total_monthly_rent += active_lease.rent_amount
            total_annual_rent += active_lease.rent_amount * 12
        if p.loan_amount and p.loan_rate:
            total_loan_cost += p.loan_amount * p.loan_rate
        if p.property_fee:
            total_property_fee += p.property_fee * 12
        if p.purchase_price:
            total_opportunity_cost += p.purchase_price * 0.03

    return jsonify({
        'total_properties': total_properties,
        'rented_count': rented_count,
        'vacant_count': vacant_count,
        'income': {
            'total_monthly_rent': total_monthly_rent,
            'total_annual_rent': total_annual_rent
        },
        'costs': {
            'loan_cost': total_loan_cost,
            'property_fee': total_property_fee,
            'opportunity_cost': total_opportunity_cost,
            'total': total_loan_cost + total_property_fee + total_opportunity_cost
        },
        'profit': total_annual_rent - (total_loan_cost + total_property_fee + total_opportunity_cost)
    }), 200
