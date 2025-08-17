from flask import Blueprint, request, jsonify
from models import db, Auction, Document
from werkzeug.utils import secure_filename
import os
from datetime import datetime

auction_bp = Blueprint('auction_bp', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@auction_bp.route('/auctions', methods=['GET'])
def get_auctions():
    auctions = Auction.query.order_by(Auction.start_time.asc()).all()
    return jsonify([a.to_dict() for a in auctions])

@auction_bp.route('/assets', methods=['POST'])
def create_asset():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'Image file is required.'}), 400

        data = request.form
        image = request.files['image']
        documents = request.files.getlist('documents')
        
        required_fields = ['title', 'description', 'initial_price', 'start_time', 'end_time', 'bank_uploader_id']
        if not all(k in data for k in required_fields):
            return jsonify({'error': 'Missing required form data.'}), 400

        try:
            # --- THIS IS THE FIX ---
            # The incoming string is now a full ISO 8601 UTC string (e.g., "....Z").
            # We use fromisoformat and remove the 'Z' so Python can parse it
            # into a "naive" datetime object, which is what SQLAlchemy/SQLite expects.
            start_time_obj = datetime.fromisoformat(data['start_time'].replace('Z', ''))
            end_time_obj = datetime.fromisoformat(data['end_time'].replace('Z', ''))

        except ValueError:
            return jsonify({'error': 'Invalid datetime format from frontend.'}), 400
        
        if start_time_obj >= end_time_obj:
            return jsonify({'error': 'Start time must be before end time.'}), 400

        # ... (rest of the file is unchanged)
        upload_folder = os.path.join(os.getcwd(), 'static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        
        unique_prefix = f"{datetime.utcnow().timestamp()}_{abs(hash(image.filename))}"
        image_filename = secure_filename(f"{unique_prefix}_{image.filename}")
        image.save(os.path.join(upload_folder, image_filename))

        new_auction = Auction(
            title=data['title'],
            description=data['description'],
            initial_price=float(data['initial_price']),
            image_filename=image_filename,
            bank_uploader_id=int(data['bank_uploader_id']),
            start_time=start_time_obj,
            end_time=end_time_obj
        )
        db.session.add(new_auction)
        db.session.flush()

        for doc in documents:
            if doc and allowed_file(doc.filename):
                doc_prefix = f"{datetime.utcnow().timestamp()}_{abs(hash(doc.filename))}"
                doc_filename = secure_filename(f"{doc_prefix}_{doc.filename}")
                doc.save(os.path.join(upload_folder, doc_filename))
                new_document = Document(filename=doc_filename, auction_id=new_auction.id)
                db.session.add(new_document)
        
        db.session.commit()
        return jsonify(new_auction.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        print(f"--- UPLOAD FAILED: SERVER ERROR ---: {e}")
        return jsonify({'error': 'An internal server error occurred during upload.'}), 500