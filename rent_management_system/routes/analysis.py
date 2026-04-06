from flask import Blueprint, jsonify
from models import Property, Payment

analysis_bp = Blueprint('analysis', __name__)

@analysis_bp.route('/analysis/annual_profit/<int:property_id>', methods=['GET'])
def get_annual_profit(property_id):
    property = Property.query.get(property_id)
    if not property:
        return jsonify({"error": "Property not found"}), 404
    
    rental_income = sum(p.amount for p in property.payments if p.status == 'paid')
    loan_cost = property.loan_amount * property.loan_rate
    opportunity_cost = property.purchase_price * 0.03
    annual_profit = rental_income - (loan_cost + opportunity_cost + property.property_fee * 12)
    
    return jsonify({"annual_profit": annual_profit}), 200