from flask import Blueprint, request, jsonify, send_from_directory, current_app
import os
from werkzeug.utils import secure_filename

doc_bp = Blueprint('documents', __name__)

# Upload a document (PDF, DOCX, etc.)
@doc_bp.route('/documents/upload', methods=['POST'])
def upload_document():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    return jsonify({'message': 'File uploaded successfully', 'filename': filename}), 201


# Download a document
@doc_bp.route('/documents/<filename>', methods=['GET'])
def download_document(filename):
    uploads = current_app.config['UPLOAD_FOLDER']
    return send_from_directory(uploads, filename, as_attachment=True)
