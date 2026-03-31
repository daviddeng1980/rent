from extensions import db

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    area = db.Column(db.Float)
    property_type = db.Column(db.String(50))
    decoration = db.Column(db.String(50))
    furniture = db.Column(db.String(200))
    rent_guide = db.Column(db.Float)
    purchase_date = db.Column(db.Date)
    purchase_price = db.Column(db.Float, default=0)
    loan_amount = db.Column(db.Float, default=0)
    loan_rate = db.Column(db.Float, default=0)
    property_fee = db.Column(db.Float, default=0)
    remark = db.Column(db.Text)
    images = db.Column(db.Text, default='[]')
    create_time = db.Column(db.DateTime, default=db.func.now())

    leases = db.relationship('Lease', backref='property', lazy=True)

    @property
    def status(self):
        active_lease = Lease.query.filter_by(property_id=self.id, status='active').first()
        return '出租中' if active_lease else '空置'

class Lease(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'))
    rent_amount = db.Column(db.Float, nullable=False)
    rent_day = db.Column(db.Integer, default=1)
    deposit = db.Column(db.Float, default=0)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='active')
    remark = db.Column(db.Text)
    create_time = db.Column(db.DateTime, default=db.func.now())

    payments = db.relationship('Payment', backref='lease', lazy=True)

    @property
    def is_active(self):
        return self.status == 'active'

class Tenant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    id_card = db.Column(db.String(50))
    emergency_contact = db.Column(db.String(100))
    emergency_phone = db.Column(db.String(20))
    remark = db.Column(db.Text)
    create_time = db.Column(db.DateTime, default=db.func.now())

    leases = db.relationship('Lease', backref='tenant', lazy=True)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lease_id = db.Column(db.Integer, db.ForeignKey('lease.id'), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')
    paid_date = db.Column(db.Date)
    remark = db.Column(db.String(200))
    create_time = db.Column(db.DateTime, default=db.func.now())
