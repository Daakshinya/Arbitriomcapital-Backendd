from flask import Blueprint, jsonify
from models import Bid

bid_bp = Blueprint('bid_bp', __name__)

@bid_bp.route('/bids/<int:auction_id>', methods=['GET'])
def get_bids(auction_id):
    bids = Bid.query.filter_by(auction_id=auction_id).order_by(Bid.timestamp.desc()).all()
    return jsonify([b.to_dict() for b in bids])