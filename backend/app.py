"""
Medical PDF Signing Platform - Flask Backend
100% Open Source
"""

import os
import uuid
import base64
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify, send_file, session
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename

from config import Config
from models import db, User, Signature, Document
from encryption import init_encryption, get_encryption, SignatureEncryption
from signature_processor import process_signature_image, validate_image, get_signature_preview
from pdf_signer import add_signature_to_pdf, get_pdf_info

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
CORS(app, supports_credentials=True, origins=['http://localhost:3000', 'http://127.0.0.1:3000'])
db.init_app(app)

# Login manager
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Initialize encryption
def init_app_encryption():
    key = app.config.get('ENCRYPTION_KEY')
    if key:
        if isinstance(key, str):
            key = key.encode()
    else:
        # Generate a key if not provided (save this in production!)
        key = os.urandom(32)
        print("WARNING: Generated new encryption key. Set ENCRYPTION_KEY in .env for production!")
    init_encryption(key)

# Create directories
def create_directories():
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['SIGNED_FOLDER'], exist_ok=True)
    os.makedirs(app.config['SIGNATURES_FOLDER'], exist_ok=True)

# Helper: Check allowed file extensions
def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

# Helper: Role required decorator
def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({'error': 'Authentication required'}), 401
            if current_user.role != role and current_user.role != 'admin':
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ============== AUTH ROUTES ==============

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user."""
    data = request.json

    if not data.get('email') or not data.get('password') or not data.get('name'):
        return jsonify({'error': 'Email, password, and name are required'}), 400

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400

    user = User(
        email=data['email'],
        name=data['name'],
        role=data.get('role', 'doctor')
    )
    user.set_password(data['password'])

    db.session.add(user)
    db.session.commit()

    return jsonify({'message': 'User registered successfully', 'user': user.to_dict()}), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login user."""
    data = request.json

    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required'}), 400

    user = User.query.filter_by(email=data['email']).first()

    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid email or password'}), 401

    login_user(user)
    return jsonify({'message': 'Login successful', 'user': user.to_dict()}), 200


@app.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    """Logout user."""
    logout_user()
    return jsonify({'message': 'Logout successful'}), 200


@app.route('/api/auth/me', methods=['GET'])
@login_required
def get_current_user():
    """Get current logged in user."""
    return jsonify(current_user.to_dict()), 200


# ============== SIGNATURE ROUTES ==============

@app.route('/api/signatures/upload', methods=['POST'])
@login_required
def upload_signature():
    """
    Upload signature image.
    - Removes background automatically
    - Encrypts and stores securely
    """
    if 'signature' not in request.files:
        return jsonify({'error': 'No signature file provided'}), 400

    file = request.files['signature']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename, app.config['ALLOWED_IMAGE_EXTENSIONS']):
        return jsonify({'error': 'Invalid file type. Use PNG, JPG, or WEBP'}), 400

    # Read file data
    image_data = file.read()

    # Validate image
    is_valid, error_msg = validate_image(image_data)
    if not is_valid:
        return jsonify({'error': error_msg}), 400

    try:
        # Process signature (remove background, optimize)
        processed_signature = process_signature_image(image_data)

        # Generate unique filename
        filename = f"{current_user.id}_{uuid.uuid4().hex}.enc"
        encrypted_path = os.path.join(app.config['SIGNATURES_FOLDER'], filename)

        # Encrypt and save
        encryption = get_encryption()
        file_hash = encryption.encrypt_file(
            input_path=None,  # We'll pass data directly
            output_path=encrypted_path
        ) if False else None

        # Actually encrypt from memory
        encrypted_data = encryption.encrypt(processed_signature)
        with open(encrypted_path, 'wb') as f:
            f.write(encrypted_data)

        # Calculate hash for integrity
        import hashlib
        file_hash = hashlib.sha256(processed_signature).hexdigest()

        # Delete old signature if exists
        old_signature = Signature.query.filter_by(user_id=current_user.id).first()
        if old_signature:
            # Delete old encrypted file
            if os.path.exists(old_signature.encrypted_path):
                os.remove(old_signature.encrypted_path)
            db.session.delete(old_signature)

        # Save to database
        signature = Signature(
            user_id=current_user.id,
            encrypted_path=encrypted_path,
            original_filename=secure_filename(file.filename),
            file_hash=file_hash
        )
        db.session.add(signature)
        db.session.commit()

        return jsonify({
            'message': 'Signature uploaded and processed successfully',
            'signature': signature.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to process signature: {str(e)}'}), 500


@app.route('/api/signatures/preview', methods=['GET'])
@login_required
def get_signature_preview_route():
    """Get preview of user's saved signature."""
    signature = Signature.query.filter_by(user_id=current_user.id).first()

    if not signature:
        return jsonify({'error': 'No signature found'}), 404

    try:
        encryption = get_encryption()
        decrypted_data = encryption.decrypt_file(signature.encrypted_path)

        # Verify integrity
        import hashlib
        if hashlib.sha256(decrypted_data).hexdigest() != signature.file_hash:
            return jsonify({'error': 'Signature integrity check failed'}), 500

        # Return as base64 for preview
        base64_data = base64.b64encode(decrypted_data).decode()
        return jsonify({
            'signature': f'data:image/png;base64,{base64_data}',
            'info': signature.to_dict()
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to retrieve signature: {str(e)}'}), 500


@app.route('/api/signatures/delete', methods=['DELETE'])
@login_required
def delete_signature():
    """Delete user's saved signature."""
    signature = Signature.query.filter_by(user_id=current_user.id).first()

    if not signature:
        return jsonify({'error': 'No signature found'}), 404

    try:
        # Delete encrypted file
        if os.path.exists(signature.encrypted_path):
            os.remove(signature.encrypted_path)

        db.session.delete(signature)
        db.session.commit()

        return jsonify({'message': 'Signature deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete signature: {str(e)}'}), 500


# ============== DOCUMENT ROUTES ==============

@app.route('/api/documents/upload', methods=['POST'])
@login_required
@role_required('admin')
def upload_document():
    """Upload a PDF document (admin only)."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename, app.config['ALLOWED_PDF_EXTENSIONS']):
        return jsonify({'error': 'Only PDF files are allowed'}), 400

    # Get metadata
    document_type = request.form.get('document_type', 'general')
    patient_name = request.form.get('patient_name', '')
    patient_id = request.form.get('patient_id', '')

    # Save file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    original_filename = secure_filename(file.filename)
    filename = f"{timestamp}_{uuid.uuid4().hex[:8]}_{original_filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Create document record
    document = Document(
        filename=filename,
        original_path=filepath,
        document_type=document_type,
        patient_name=patient_name,
        patient_id=patient_id,
        uploaded_by=current_user.id,
        status='pending'
    )

    db.session.add(document)
    db.session.commit()

    # Get PDF info
    pdf_info = get_pdf_info(filepath)

    return jsonify({
        'message': 'Document uploaded successfully',
        'document': document.to_dict(),
        'pdf_info': pdf_info
    }), 201


@app.route('/api/documents', methods=['GET'])
@login_required
def get_documents():
    """Get documents based on status filter."""
    status = request.args.get('status', 'pending')

    if current_user.role == 'admin':
        documents = Document.query.filter_by(status=status).all()
    else:
        # Doctors see pending documents
        documents = Document.query.filter_by(status=status).all()

    return jsonify([doc.to_dict() for doc in documents]), 200


@app.route('/api/documents/<int:doc_id>', methods=['GET'])
@login_required
def get_document(doc_id):
    """Get document details."""
    document = Document.query.get_or_404(doc_id)
    pdf_info = get_pdf_info(document.original_path)

    return jsonify({
        'document': document.to_dict(),
        'pdf_info': pdf_info
    }), 200


@app.route('/api/documents/<int:doc_id>/file', methods=['GET'])
@login_required
def get_document_file(doc_id):
    """Serve the PDF file."""
    document = Document.query.get_or_404(doc_id)
    return send_file(document.original_path, mimetype='application/pdf')


@app.route('/api/documents/<int:doc_id>/sign', methods=['POST'])
@login_required
def sign_document(doc_id):
    """Sign a document using saved signature."""
    document = Document.query.get_or_404(doc_id)

    if document.status == 'signed':
        return jsonify({'error': 'Document already signed'}), 400

    # Get user's signature
    signature = Signature.query.filter_by(user_id=current_user.id).first()
    if not signature:
        return jsonify({'error': 'No signature found. Please upload your signature first.'}), 400

    # Get position from request
    data = request.json
    position = data.get('position')

    if not position:
        return jsonify({'error': 'Signature position required'}), 400

    try:
        # Decrypt signature
        encryption = get_encryption()
        signature_data = encryption.decrypt_file(signature.encrypted_path)

        # Verify integrity
        import hashlib
        if hashlib.sha256(signature_data).hexdigest() != signature.file_hash:
            return jsonify({'error': 'Signature integrity check failed'}), 500

        # Generate signed PDF filename
        signed_filename = f"signed_{document.filename}"
        signed_path = os.path.join(app.config['SIGNED_FOLDER'], signed_filename)

        # Add signature to PDF
        add_signature_to_pdf(
            pdf_path=document.original_path,
            signature_data=signature_data,
            position=position,
            output_path=signed_path
        )

        # Update document record
        document.signed_path = signed_path
        document.signed_by = current_user.id
        document.signed_at = datetime.utcnow()
        document.signature_position = position
        document.status = 'signed'

        db.session.commit()

        return jsonify({
            'message': 'Document signed successfully',
            'document': document.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to sign document: {str(e)}'}), 500


@app.route('/api/documents/<int:doc_id>/download', methods=['GET'])
@login_required
def download_signed_document(doc_id):
    """Download signed PDF."""
    document = Document.query.get_or_404(doc_id)

    if document.status != 'signed' or not document.signed_path:
        return jsonify({'error': 'Document not signed yet'}), 400

    return send_file(
        document.signed_path,
        as_attachment=True,
        download_name=f"signed_{document.filename}"
    )


@app.route('/api/documents/<int:doc_id>/delete', methods=['DELETE'])
@login_required
@role_required('admin')
def delete_document(doc_id):
    """Delete a document (admin only)."""
    document = Document.query.get_or_404(doc_id)

    try:
        # Delete files
        if os.path.exists(document.original_path):
            os.remove(document.original_path)
        if document.signed_path and os.path.exists(document.signed_path):
            os.remove(document.signed_path)

        db.session.delete(document)
        db.session.commit()

        return jsonify({'message': 'Document deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete document: {str(e)}'}), 500


# ============== UTILITY ROUTES ==============

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}), 200


# ============== ERROR HANDLERS ==============

@app.errorhandler(401)
def unauthorized(e):
    return jsonify({'error': 'Unauthorized'}), 401

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500


# ============== MAIN ==============

if __name__ == '__main__':
    create_directories()

    with app.app_context():
        db.create_all()
        init_app_encryption()

        # Create default admin if not exists
        admin = User.query.filter_by(email='admin@example.com').first()
        if not admin:
            admin = User(email='admin@example.com', name='Admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Created default admin: admin@example.com / admin123")

    app.run(debug=True, port=5000)
