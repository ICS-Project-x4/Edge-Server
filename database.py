from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import uuid
from werkzeug.security import generate_password_hash

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    api_key = db.Column(db.String(64), unique=True)

class SimCard(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    number = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='active')
    last_used = db.Column(db.DateTime, default=datetime.utcnow)
    messages = db.relationship('Message', backref='sim_card', lazy=True)

class Message(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sender = db.Column(db.String(20))
    recipient = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')
    direction = db.Column(db.String(10), nullable=False)  # 'incoming' or 'outgoing'
    sender_sim = db.Column(db.String(36), db.ForeignKey('sim_card.id'))

    def to_dict(self):
        return {
   
            'number': self.recipient,
            'message': self.message,
            'message_id': self.id 
        }

class Log(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    action = db.Column(db.String(50), nullable=False)
    details = db.Column(db.Text)
    status = db.Column(db.String(20))
    sender_sim = db.Column(db.String(36), db.ForeignKey('sim_card.id'))

    def to_dict(self):
        try:
            details = json.loads(self.details) if self.details else None
        except:
            details = self.details
        return {
            'id': self.id,
            'action': self.action,
            'details': details,
            'status': self.status,
            'sender_sim': self.sender_sim,
            'timestamp': int(self.timestamp.timestamp())
        }

class SmsStatus(db.Model):
    __tablename__ = 'sms_status'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_number = db.Column(db.String(20), nullable=False)
    receiver_number = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "sender_number": self.sender_number,
            "receiver_number": self.receiver_number,
            "message": self.message,
            "status": self.status,
            "timestamp": int(self.timestamp.timestamp())
        }

def init_db(app):
    with app.app_context():
        db.create_all()
        
        # Check if admin user exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            # Create admin user
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                role='admin',
                api_key='test_api_key_123456'
            )
            db.session.add(admin)
            db.session.commit() 