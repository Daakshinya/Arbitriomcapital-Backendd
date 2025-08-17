from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
bcrypt = Bcrypt()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='investor')
    email = db.Column(db.String(120), unique=True, nullable=False) # Changed to nullable=False
    phone = db.Column(db.String(20), nullable=True)
    email_verified = db.Column(db.Boolean, default=False) # New field
    email_verification_token = db.Column(db.String(256), unique=True, nullable=True) # New field

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'email': self.email,
            'phone': self.phone,
            'email_verified': self.email_verified # Include in dict
        }

class Auction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    initial_price = db.Column(db.Float, nullable=False)
    current_bid = db.Column(db.Float, nullable=True)
    image_filename = db.Column(db.String(120), nullable=True)
    
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='upcoming')
    
    bank_uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    highest_bidder_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    bank_uploader = db.relationship('User', foreign_keys=[bank_uploader_id], backref='auctions_created')
    highest_bidder = db.relationship('User', foreign_keys=[highest_bidder_id])
    
    documents = db.relationship('Document', backref='auction', cascade="all, delete-orphan", lazy=True)
    bids = db.relationship('Bid', backref='auction', cascade="all, delete-orphan", lazy=True)

    def to_dict(self):
        highest_bidder_username = self.highest_bidder.username if self.highest_bidder else None
        
        # Create a local datetime object for display purposes
        local_start_time = self.start_time

        # --- MODIFIED: Include highest_bidder_id ---
        return {
            'id': self.id, 'title': self.title, 'description': self.description,
            'initial_price': self.initial_price, 'current_bid': self.current_bid or self.initial_price,
            'image_url': f'/static/uploads/{self.image_filename}' if self.image_filename else None,
            'start_time': self.start_time.isoformat() + "Z", # Explicitly mark as UTC
            'end_time': self.end_time.isoformat() + "Z",   # Explicitly mark as UTC
            'status': self.status,
            'highest_bidder_username': highest_bidder_username,
            'highest_bidder_id': self.highest_bidder_id, # ADDED THIS LINE
            'documents': [doc.to_dict() for doc in self.documents],
            'bank_contact': self.bank_uploader.to_dict() if self.bank_uploader else None,
            'participants_count': len(set(bid.user_id for bid in self.bids)),
            # These are now calculated on the frontend based on the user's local timezone
            'date': local_start_time.strftime('%Y-%m-%d'), 
            'time': local_start_time.strftime('%I:%M %p'),
        }

class Bid(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    auction_id = db.Column(db.Integer, db.ForeignKey('auction.id'), nullable=False)
    user = db.relationship('User', backref='bids')
    def to_dict(self):
        return {'id': self.id, 'amount': self.amount, 'timestamp': self.timestamp.isoformat() + "Z", 'username': self.user.username}

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(120), nullable=False)
    auction_id = db.Column(db.Integer, db.ForeignKey('auction.id'), nullable=False)
    def to_dict(self):
        return { 'id': self.id, 'filename': self.filename, 'url': f'/static/uploads/{self.filename}' }