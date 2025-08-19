from flask import Blueprint, request, jsonify, current_app
import stripe
import os

payment_bp = Blueprint('payment_bp', __name__)

# This will ensure Stripe's API key is set before any request to this blueprint
@payment_bp.before_app_request
def set_stripe_api_key():
    stripe.api_key = current_app.config['STRIPE_SECRET_KEY']

@payment_bp.route('/create-payment-intent', methods=['POST'])
def create_payment_intent():
    try:
        data = request.json
        amount_usd = float(data.get('amount')) # Original bid amount
        auction_title = data.get('auction_title', 'Auction Item')
        
        if not amount_usd or amount_usd <= 0:
            return jsonify({'error': 'Valid amount is required'}), 400

        # Define convenience fee percentage (e.g., 3%)
        CONVENIENCE_FEE_PERCENTAGE = 0.03 # 3% as a decimal

        # Calculate convenience fee
        convenience_fee = amount_usd * CONVENIENCE_FEE_PERCENTAGE
        total_amount_to_charge = amount_usd + convenience_fee

        # Stripe expects amount in cents, so multiply by 100 and convert to integer
        amount_in_cents = int(total_amount_to_charge * 100)

        # Create a PaymentIntent
        # For a real application, you'd save this PaymentIntent ID to your database
        # and associate it with the auction/user.
        intent = stripe.PaymentIntent.create(
            amount=amount_in_cents,
            currency='usd', # Or your desired currency
            metadata={
                'auction_id': data.get('auction_id'), # Pass auction_id for tracking
                'auction_title': auction_title,
                'original_amount': f"{amount_usd:.2f}",
                'convenience_fee_percentage': f"{CONVENIENCE_FEE_PERCENTAGE * 100}%",
                'convenience_fee_amount': f"{convenience_fee:.2f}"
            },
            # You can specify payment_method_types, 'card' is default for most
            # payment_method_types=['card'],
        )
        return jsonify({
            'clientSecret': intent.client_secret,
            'finalAmount': round(total_amount_to_charge, 2), # Send rounded total back
            'convenienceFee': round(convenience_fee, 2) # Send rounded fee back
        })
    except Exception as e:
        print(f"Error creating PaymentIntent: {e}")
        return jsonify({'error': str(e)}), 500