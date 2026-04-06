from flask import Blueprint, request, jsonify
from models import Payment, db
from datetime import datetime, timedelta

payment_bp = Blueprint('payment', __name__)

@payment_bp.route('/payments', methods=['POST'])
def add_payment():
    data = request.get_json()
    new_payment = Payment(
        due_date=datetime.strptime(data['due_date'], '%Y-%m-%d'),
        amount=data['amount'],
        property_id=data['property_id']
    )
    db.session.add(new_payment)
    db.session.commit()
    return jsonify({"message": "Payment added successfully"}), 201