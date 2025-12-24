from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='doctor')  # 'admin' or 'doctor'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to signature
    signature = db.relationship('Signature', backref='user', uselist=False, cascade='all, delete-orphan')
    # Relationship to signed documents
    signed_documents = db.relationship('Document', backref='signer', foreign_keys='Document.signed_by')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'role': self.role,
            'has_signature': self.signature is not None,
            'created_at': self.created_at.isoformat()
        }


class Signature(db.Model):
    __tablename__ = 'signatures'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    # Encrypted signature file path
    encrypted_path = db.Column(db.String(500), nullable=False)
    # Original filename
    original_filename = db.Column(db.String(255))
    # File hash for integrity verification
    file_hash = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'original_filename': self.original_filename,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class Document(db.Model):
    __tablename__ = 'documents'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_path = db.Column(db.String(500), nullable=False)
    signed_path = db.Column(db.String(500))
    document_type = db.Column(db.String(100))  # e.g., 'consent_form', 'prescription'
    patient_name = db.Column(db.String(100))
    patient_id = db.Column(db.String(50))

    # Upload info
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Signing info
    signed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    signed_at = db.Column(db.DateTime)
    signature_position = db.Column(db.JSON)  # {x, y, page, width, height}

    status = db.Column(db.String(20), default='pending')  # 'pending', 'signed', 'archived'

    # Relationships
    uploader = db.relationship('User', foreign_keys=[uploaded_by])

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'document_type': self.document_type,
            'patient_name': self.patient_name,
            'patient_id': self.patient_id,
            'uploaded_by': self.uploader.name if self.uploader else None,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'signed_by': self.signer.name if self.signer else None,
            'signed_at': self.signed_at.isoformat() if self.signed_at else None,
            'status': self.status
        }
