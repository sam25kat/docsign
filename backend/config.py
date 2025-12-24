import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///medical_docs.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File Storage
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')
    SIGNED_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'signed_documents')
    SIGNATURES_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'signatures')

    # Encryption key for signatures (32 bytes for AES-256)
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', None)

    # Max file sizes
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max

    ALLOWED_PDF_EXTENSIONS = {'pdf'}
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
