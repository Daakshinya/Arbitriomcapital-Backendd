import os
from datetime import datetime, timezone
from flask import Flask, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from apscheduler.schedulers.background import BackgroundScheduler
from flask_mail import Mail
from dotenv import load_dotenv  # <-- Add this

# Define UTC for Python 3.10
UTC = timezone.utc

# Load environment variables from .env file
load_dotenv()

from models import db, bcrypt, Auction, User, Bid
from routes.auth import auth_bp
from routes.auction import auction_bp
from routes.bid import bid_bp
from routes.payment import payment_bp  # <--- ADDED THIS LINE
 # <--- ADDED THIS LINE

socketio = SocketIO()
cors = CORS()
mail = Mail() # Initialize Flask-Mail globally

def check_auctions_status(app):
    """
    Background job to check and update auction statuses.
    Transitions: upcoming -> live -> closed
    """
    with app.app_context():
        now = datetime.now(UTC)
        
        # Logic to transition auctions from 'upcoming' to 'live'
        starting_auctions = Auction.query.filter(
            Auction.start_time <= now, 
            Auction.end_time > now, 
            Auction.status == 'upcoming'
        ).all()
        
        for auction in starting_auctions:
            auction.status = 'live'
            print(f"Auction ID {auction.id} ('{auction.title}') is now live.")
            socketio.emit('auction_live', {'auction_id': auction.id, 'status': 'live'})

        # Logic to close auctions that are 'live' or 'upcoming' and have ended
        expired_auctions = Auction.query.filter(
            Auction.end_time <= now, 
            Auction.status.in_(['live', 'upcoming'])
        ).all()
        
        for auction in expired_auctions:
            auction.status = 'closed'
            print(f"Auction ID {auction.id} ('{auction.title}') has been closed.")
            socketio.emit('auction_closed', {'auction_id': auction.id, 'status': 'closed'})
            
        if starting_auctions or expired_auctions:
            db.session.commit()

def create_app():
    app = Flask(__name__)
    CORS(app, supports_credentials=True, origins=["http://localhost:3000"])

    basedir = os.path.abspath(os.path.dirname(__file__))
    # Ensure the instance folder exists
    instance_path = os.path.join(basedir, 'instance')
    os.makedirs(instance_path, exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(instance_path, 'database.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Brevo (Sendinblue) SMTP Configuration
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT'))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS').lower() in ('true', '1', 't')
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')

    # Add Stripe API Keys to Flask app config
    app.config['STRIPE_SECRET_KEY'] = os.environ.get('STRIPE_SECRET_KEY')
    app.config['STRIPE_PUBLISHABLE_KEY'] = os.environ.get('STRIPE_PUBLISHABLE_KEY') # Although frontend will use its own env for this

    db.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app) # Initialize Flask-Mail with the app
    socketio.init_app(app, cors_allowed_origins="http://localhost:3000")

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(auction_bp, url_prefix='/api')
    app.register_blueprint(bid_bp, url_prefix='/api')
    app.register_blueprint(payment_bp, url_prefix='/api/payment') # <--- ADDED THIS LINE

    @app.route('/api/auctions/<int:auction_id>', methods=['GET'])
    def get_auction(auction_id):
        auction = Auction.query.get_or_404(auction_id)
        return jsonify(auction.to_dict())
    
    @socketio.on('place_bid')
    def handle_place_bid(data):
        auction_id = data.get('auction_id')
        amount = float(data.get('amount'))
        user_id = data.get('user_id')
        
        auction = Auction.query.get(auction_id)
        user = User.query.get(user_id)

        if not (auction and user):
            return emit('bid_error', {'error': 'Auction or user not found.'})
        if auction.status != 'live':
            return emit('bid_error', {'error': 'This auction is not live for bidding.'})
        if amount <= (auction.current_bid or auction.initial_price):
            return emit('bid_error', {'error': 'Your bid must be higher than the current bid.'})

        previous_highest_bidder_id = auction.highest_bidder_id
        
        auction.current_bid = amount
        auction.highest_bidder_id = user.id
        new_bid = Bid(amount=amount, user_id=user_id, auction_id=auction_id)
        db.session.add(new_bid)
        db.session.commit()
        
        emit('bid_update', {
            'auction_id': auction_id, 
            'new_bid': amount, 
            'highest_bidder_username': user.username,
            'highest_bidder_id': user.id,
            'new_bid_details': new_bid.to_dict()
        }, broadcast=True)
        
        if previous_highest_bidder_id and previous_highest_bidder_id != user.id:
            emit('outbid', {
                'auction_title': auction.title, 
                'outbid_user_id': previous_highest_bidder_id
            }, broadcast=True)

    with app.app_context():
        db.create_all()

    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(func=lambda: check_auctions_status(app), trigger="interval", seconds=10)
    scheduler.start()

    return app

if __name__ == '__main__':
    app = create_app()
    socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)