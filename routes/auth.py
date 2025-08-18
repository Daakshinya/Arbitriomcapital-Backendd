# FILE: backend/routes/auth.py
from flask import Blueprint, request, jsonify
from models import db, User

# keep the same name you've been using so app.py import still works
auth_bp = Blueprint('auth_bp', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json(force=True)

    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    role     = (data.get('role') or 'investor').strip()
    email    = (data.get('email') or '').strip().lower()
    phone    = (data.get('phone') or '').strip()

    # Basic validation
    if not username or not password or not email:
        return jsonify({'error': 'Username, password, and email are required'}), 400

    # Enforce unique username/email
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email address is already in use'}), 409

    # Create user (no email verification)
    user = User(
        username=username,
        role=role,
        email=email,
        phone=phone,
        email_verified=True,            # <- mark verified by default
        email_verification_token=None   # <- not used anymore
    )
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    return jsonify({
        'message': 'Registration successful',
        'user': user.to_dict()
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(force=True)
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()

    user = User.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid username or password'}), 401

    # No email verification gate
    return jsonify({
        'message': 'Login successful',
        'user': user.to_dict()
    }), 200
