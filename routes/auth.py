from flask import Blueprint, request, jsonify, url_for, current_app, redirect
from models import db, User
import uuid # For generating unique tokens
from flask_mail import Message # Import Message

auth_bp = Blueprint('auth_bp', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'investor')
    email = data.get('email')
    phone = data.get('phone')

    if not username or not password or not email:
        return jsonify({'error': 'Username, password, and email are required'}), 400
    
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email address is already in use'}), 409

    new_user = User(
        username=username, 
        role=role,
        email=email,
        phone=phone,
        email_verified=False # New users are not verified by default
    )
    new_user.set_password(password)
    
    # Generate a unique verification token
    verification_token = str(uuid.uuid4())
    new_user.email_verification_token = verification_token
    
    db.session.add(new_user)
    db.session.commit()

    # Send verification email
    try:
        # Construct the verification link. _external=True makes it an absolute URL.
        # Make sure Flask's request context is available.
        with current_app.app_context():
            # For local development, this will be http://127.0.0.1:5000/api/auth/verify-email/<token>
            # In production, ensure SERVER_NAME is configured in app.py for correct domain.
            verification_link = url_for('auth_bp.verify_email', token=verification_token, _external=True)
            
            msg = Message(
                'Verify Your Email Address for Auction Platform',
                recipients=[email],
                html=f"""
                <p>Hello {username},</p>
                <p>Thank you for registering on our Auction Platform. Please click the link below to verify your email address and activate your account:</p>
                <p><a href="{verification_link}" style="display: inline-block; padding: 10px 20px; background-color: #007bff; color: #ffffff; text-decoration: none; border-radius: 5px;">Verify Email Address</a></p>
                <p>If you did not register for this service, please ignore this email.</p>
                <p>Regards,</p>
                <p>The Auction Platform Team</p>
                """
            )
            current_app.extensions['mail'].send(msg)
        
        return jsonify({
            'message': f'User {username} registered successfully. Please check your email ({email}) for a verification link to activate your account.'
        }), 201
    except Exception as e:
        db.session.rollback() # Rollback user creation if email fails critically (optional, depending on desired behavior)
        print(f"Failed to send verification email to {email}: {e}")
        # Even if email sending fails, user is registered, but not verified.
        # Inform the user that verification email couldn't be sent.
        return jsonify({
            'message': f'User {username} registered successfully, but failed to send verification email. Please contact support if you don\'t receive it.',
            'error_sending_email': True
        }), 201

@auth_bp.route('/verify-email/<token>', methods=['GET'])
def verify_email(token):
    user = User.query.filter_by(email_verification_token=token).first()

    if not user:
        # Redirect to an error page or the login page with an error message
        return redirect("http://localhost:3000/login?message=invalid_token")

    if user.email_verified:
        # Already verified, redirect to login or a success page with a message
        return redirect("http://localhost:3000/login?message=already_verified")

    user.email_verified = True
    user.email_verification_token = None # Clear the token after successful verification
    db.session.commit()

    # Redirect to the frontend login page with a success query parameter
    return redirect("http://localhost:3000/login?verified=true")


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    user = User.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid username or password'}), 401
    
    # Check if the user's email is verified
    if not user.email_verified:
        return jsonify({'error': 'Your email address is not verified. Please check your inbox for a verification link.'}), 403 # Forbidden
    
    return jsonify({'message': 'Login successful', 'user': user.to_dict()}), 200