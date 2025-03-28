from . import db
from sqlalchemy.sql import func

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone_number=db.Column(db.String(15), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    address = db.Column(db.Text, nullable=True)
    pincode = db.Column(db.String(6), nullable=True)
    date_created = db.Column(db.DateTime, default=func.now())


class ProfessionalDetails(db.Model):
    __tablename__ = 'professional_details'
    id= db.Column(db.Integer, primary_key=True)
    name= db.Column(db.String(150), nullable=False)
    email= db.Column(db.String(120), unique=True, nullable=False)
    password= db.Column(db.String(200), nullable=False)
    phone_number=db.Column(db.String(15), nullable=False)
    service= db.Column(db.String(150), nullable=False)
    experience = db.Column(db.Integer, nullable=False)
    address = db.Column(db.Text, nullable=True)
    pincode = db.Column(db.String(6), nullable=True)
    status=db.Column(db.String(20), default="pending")
   
    
class ServiceRequest(db.Model):
    __tablename__ = 'service_request'
    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    professional_id = db.Column(db.Integer, db.ForeignKey('professional_details.id'), nullable=True)
    status = db.Column(db.String(50), nullable=False, default="requested")
    rating = db.Column(db.Integer, nullable=True) 
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())
    
    customer = db.relationship('User', backref='service_requests', lazy=True)
    service = db.relationship('Services', backref='service_requests', lazy=True)
    professional = db.relationship('ProfessionalDetails', backref='service_requests', lazy=True)


class Services(db.Model):
    __tablename__='services'
    id = db.Column(db.Integer, primary_key=True)
    domain=db.Column(db.String(40),nullable=False)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(150))
    price= db.Column(db.Float, nullable=False)

class RejectedRequest(db.Model):
    __tablename__ = 'rejected_requests'
    id = db.Column(db.Integer, primary_key=True)
    service_request_id = db.Column(db.Integer, db.ForeignKey('service_request.id'), nullable=False)
    professional_id = db.Column(db.Integer, db.ForeignKey('professional_details.id'), nullable=False)

    service_request = db.relationship('ServiceRequest', backref='rejections', lazy=True)
    professional = db.relationship('ProfessionalDetails', backref='rejections', lazy=True)

