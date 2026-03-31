from flask import Blueprint, request, jsonify
from models import Property, db

property_bp = Blueprint('property', __name__)

@property_bp.route('/properties', methods=['POST'])
def add_property():
    data = request.get_json()
    new_property = Property(
        address=data['address'],
        rent=data['rent'],
        purchase_date=data['purchase_date']
    )
    db.session.add(new_property)
    db.session.commit()
    return jsonify({"message": "Property added successfully"}), 201

@property_bp.route('/properties/bulk', methods=['POST'])
def bulk_import():
    # ... existing code ...