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
from pdf_signer import add_signature_to_pdf, add_f2f_signature_to_pdf, get_pdf_info
from signature_detector import detect_signature_position, detect_signature_positions_batch, detect_all_signature_positions, detect_f2f_signature_position

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
    import base64
    key = app.config.get('ENCRYPTION_KEY')
    if key:
        if isinstance(key, str):
            # Decode base64 key to get 32 raw bytes
            try:
                key = base64.b64decode(key)
            except Exception:
                # If not valid base64, use as passphrase
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
    - Optionally stores signer name for "Digitally signed by" text
    """
    if 'signature' not in request.files:
        return jsonify({'error': 'No signature file provided'}), 400

    file = request.files['signature']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename, app.config['ALLOWED_IMAGE_EXTENSIONS']):
        return jsonify({'error': 'Invalid file type. Use PNG, JPG, or WEBP'}), 400

    # Get signer name from form data (optional, defaults to user's name)
    signer_name = request.form.get('signer_name', '').strip()
    if not signer_name:
        signer_name = current_user.name  # Default to user's name

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

        # Check for existing signature and update or create
        existing_signature = Signature.query.filter_by(user_id=current_user.id).first()

        if existing_signature:
            # Delete old encrypted file
            if os.path.exists(existing_signature.encrypted_path):
                os.remove(existing_signature.encrypted_path)
            # Update existing record
            existing_signature.encrypted_path = encrypted_path
            existing_signature.original_filename = secure_filename(file.filename)
            existing_signature.file_hash = file_hash
            existing_signature.signer_name = signer_name
            existing_signature.updated_at = datetime.utcnow()
            signature = existing_signature
        else:
            # Create new signature record
            signature = Signature(
                user_id=current_user.id,
                encrypted_path=encrypted_path,
                original_filename=secure_filename(file.filename),
                file_hash=file_hash,
                signer_name=signer_name
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
    """
    Sign a document using saved signature.
    Supports both single position and multiple positions (one per page).
    F2F documents: only last page with text box.
    """
    from pdf_signer import add_multiple_signatures

    document = Document.query.get_or_404(doc_id)

    if document.status == 'signed':
        return jsonify({'error': 'Document already signed'}), 400

    # Get user's signature
    signature = Signature.query.filter_by(user_id=current_user.id).first()
    if not signature:
        return jsonify({'error': 'No signature found. Please upload your signature first.'}), 400

    # Get position(s) from request
    data = request.json
    position = data.get('position')      # Single position (backward compat)
    positions = data.get('positions')    # Multiple positions array

    if not position and not positions:
        return jsonify({'error': 'Signature position required'}), 400

    try:
        # Decrypt signature
        encryption = get_encryption()
        signature_data = encryption.decrypt_file(signature.encrypted_path)

        # Verify integrity
        import hashlib
        if hashlib.sha256(signature_data).hexdigest() != signature.file_hash:
            return jsonify({'error': 'Signature integrity check failed'}), 500

        # Generate unique signed PDF filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = uuid.uuid4().hex[:8]
        signed_filename = f"signed_{timestamp}_{unique_id}_{document.filename}"
        signed_path = os.path.join(app.config['SIGNED_FOLDER'], signed_filename)

        # Get signer name (fallback to user's name if not set)
        signer_name = signature.signer_name or current_user.name

        # F2F documents: use special signing with text box, last page only
        if document.document_type == 'f2f':
            # Use only the first position (should be last page from detection)
            pos = positions[0] if positions else position
            # Generate a unique document ID for the signature box
            import uuid
            doc_uuid = str(uuid.uuid4())
            # Get client IP address
            client_ip = request.remote_addr or request.headers.get('X-Forwarded-For', '::1')
            add_f2f_signature_to_pdf(
                pdf_path=document.original_path,
                signature_data=signature_data,
                position=pos,
                output_path=signed_path,
                signer_name=signer_name,
                document_id=doc_uuid,
                ip_address=client_ip
            )
            num_signatures = 1
        elif positions and len(positions) > 0:
            # Multiple positions - use add_multiple_signatures
            signatures_list = [
                {'signature_data': signature_data, 'position': pos}
                for pos in positions
            ]
            add_multiple_signatures(
                pdf_path=document.original_path,
                signatures=signatures_list,
                output_path=signed_path,
                signer_name=signer_name
            )
            num_signatures = len(positions)
        else:
            # Single position - use add_signature_to_pdf
            add_signature_to_pdf(
                pdf_path=document.original_path,
                signature_data=signature_data,
                position=position,
                output_path=signed_path,
                signer_name=signer_name
            )
            num_signatures = 1

        # Update document record
        document.signed_path = signed_path
        document.signed_by = current_user.id
        document.signed_at = datetime.utcnow()
        document.signature_position = positions if positions else position
        document.status = 'signed'

        db.session.commit()

        return jsonify({
            'message': f'Document signed successfully with {num_signatures} signature(s)',
            'document': document.to_dict(),
            'num_signatures': num_signatures,
            'is_f2f': document.document_type == 'f2f'
        }), 200

    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
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


# ============== AUTO-DETECT & BULK SIGN ROUTES ==============

@app.route('/api/documents/<int:doc_id>/detect-signature-position', methods=['GET'])
@login_required
def detect_document_signature_position(doc_id):
    """
    Detect where signature should be placed in a document.
    Returns all signature positions (at most one per page).
    For F2F documents: only returns position on last page.
    """
    document = Document.query.get_or_404(doc_id)

    try:
        # F2F documents: signature only on last page in blank space
        if document.document_type == 'f2f':
            detection = detect_f2f_signature_position(document.original_path)
            detection['is_f2f'] = True
        else:
            # Use the standard multi-page detection
            detection = detect_all_signature_positions(document.original_path)
            detection['is_f2f'] = False
        return jsonify(detection), 200
    except Exception as e:
        return jsonify({'error': f'Detection failed: {str(e)}'}), 500


@app.route('/api/documents/bulk-detect', methods=['POST'])
@login_required
def bulk_detect_signature_positions():
    """Detect signature positions for multiple documents (multi-page).
    F2F documents only get signature on last page."""
    data = request.json
    document_ids = data.get('document_ids', [])

    if not document_ids:
        return jsonify({'error': 'No document IDs provided'}), 400

    results = []
    for doc_id in document_ids:
        document = Document.query.get(doc_id)
        if document and document.status == 'pending':
            # F2F documents: signature only on last page
            if document.document_type == 'f2f':
                detection = detect_f2f_signature_position(document.original_path)
                detection['is_f2f'] = True
            else:
                # Use multi-page detection
                detection = detect_all_signature_positions(document.original_path)
                detection['is_f2f'] = False
            detection['document_id'] = doc_id
            detection['filename'] = document.filename
            detection['patient_name'] = document.patient_name
            detection['document_type'] = document.document_type
            results.append(detection)

    return jsonify({'detections': results}), 200


@app.route('/api/documents/bulk-sign', methods=['POST'])
@login_required
def bulk_sign_documents():
    """
    Sign multiple documents at once.
    Supports multiple signature positions per document (one per page).

    Request body:
    {
        "documents": [
            {"id": 1, "positions": [{x, y, page, width, height}, ...]},
            {"id": 2, "positions": [{x, y, page, width, height}, ...]},
            ...
        ],
        "auto_mode": false  // If true, auto-detect ALL positions for docs without positions
    }
    """
    from pdf_signer import add_multiple_signatures

    data = request.json
    documents_to_sign = data.get('documents', [])
    auto_mode = data.get('auto_mode', False)

    if not documents_to_sign:
        return jsonify({'error': 'No documents provided'}), 400

    # Get user's signature
    signature = Signature.query.filter_by(user_id=current_user.id).first()
    if not signature:
        return jsonify({'error': 'No signature found. Please upload your signature first.'}), 400

    # Decrypt signature once for all documents
    try:
        encryption = get_encryption()
        signature_data = encryption.decrypt_file(signature.encrypted_path)

        # Verify integrity
        import hashlib
        if hashlib.sha256(signature_data).hexdigest() != signature.file_hash:
            return jsonify({'error': 'Signature integrity check failed'}), 500
    except Exception as e:
        return jsonify({'error': f'Failed to load signature: {str(e)}'}), 500

    results = {
        'successful': [],
        'failed': []
    }

    for doc_info in documents_to_sign:
        doc_id = doc_info.get('id')
        positions = doc_info.get('positions', [])  # Array of positions
        position = doc_info.get('position')        # Single position (backward compat)

        document = Document.query.get(doc_id)
        if not document:
            results['failed'].append({
                'id': doc_id,
                'error': 'Document not found'
            })
            continue

        if document.status == 'signed':
            results['failed'].append({
                'id': doc_id,
                'filename': document.filename,
                'error': 'Already signed'
            })
            continue

        # Check if F2F document
        is_f2f = document.document_type == 'f2f'

        # Auto-detect positions if not provided and auto_mode is on
        if not positions and not position and auto_mode:
            if is_f2f:
                # F2F: use special detection (last page only)
                detection = detect_f2f_signature_position(document.original_path)
            else:
                detection = detect_all_signature_positions(document.original_path)
            if detection['found'] and detection['positions']:
                positions = detection['positions']
            else:
                results['failed'].append({
                    'id': doc_id,
                    'filename': document.filename,
                    'error': 'Could not detect signature positions'
                })
                continue

        # Handle backward compatibility: single position
        if position and not positions:
            positions = [position]

        if not positions:
            results['failed'].append({
                'id': doc_id,
                'filename': document.filename,
                'error': 'No positions provided'
            })
            continue

        try:
            # Generate unique signed PDF filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_id = uuid.uuid4().hex[:8]
            signed_filename = f"signed_{timestamp}_{unique_id}_{document.filename}"
            signed_path = os.path.join(app.config['SIGNED_FOLDER'], signed_filename)

            # Get signer name (fallback to user's name if not set)
            signer_name = signature.signer_name or current_user.name

            # F2F documents: use special signing with text box, last page only
            if is_f2f:
                doc_uuid = uuid.uuid4().hex
                client_ip = request.remote_addr or request.headers.get('X-Forwarded-For', '::1')
                add_f2f_signature_to_pdf(
                    pdf_path=document.original_path,
                    signature_data=signature_data,
                    position=positions[0],  # F2F only uses first position (last page)
                    output_path=signed_path,
                    signer_name=signer_name,
                    document_id=doc_uuid,
                    ip_address=client_ip
                )
            elif len(positions) > 1:
                # Multiple positions - use add_multiple_signatures
                signatures_list = [
                    {'signature_data': signature_data, 'position': pos}
                    for pos in positions
                ]
                add_multiple_signatures(
                    pdf_path=document.original_path,
                    signatures=signatures_list,
                    output_path=signed_path,
                    signer_name=signer_name
                )
            else:
                # Single position
                add_signature_to_pdf(
                    pdf_path=document.original_path,
                    signature_data=signature_data,
                    position=positions[0],
                    output_path=signed_path,
                    signer_name=signer_name
                )

            # Update document record
            document.signed_path = signed_path
            document.signed_by = current_user.id
            document.signed_at = datetime.utcnow()
            document.signature_position = positions
            document.status = 'signed'

            results['successful'].append({
                'id': doc_id,
                'filename': document.filename,
                'num_signatures': 1 if is_f2f else len(positions),
                'is_f2f': is_f2f
            })

        except Exception as e:
            results['failed'].append({
                'id': doc_id,
                'filename': document.filename,
                'error': str(e)
            })

    # Commit all changes
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500

    total_sigs = sum(r.get('num_signatures', 1) for r in results['successful'])
    return jsonify({
        'message': f'Signed {len(results["successful"])} documents with {total_sigs} total signature(s)',
        'results': results
    }), 200


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
