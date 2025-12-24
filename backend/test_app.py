"""
Simple test script to verify the backend setup.
Run with: python test_app.py
"""

import os
import sys

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")

    try:
        from flask import Flask
        print("  ✓ Flask")
    except ImportError as e:
        print(f"  ✗ Flask: {e}")
        return False

    try:
        from flask_cors import CORS
        print("  ✓ Flask-CORS")
    except ImportError as e:
        print(f"  ✗ Flask-CORS: {e}")
        return False

    try:
        from flask_login import LoginManager
        print("  ✓ Flask-Login")
    except ImportError as e:
        print(f"  ✗ Flask-Login: {e}")
        return False

    try:
        from flask_sqlalchemy import SQLAlchemy
        print("  ✓ Flask-SQLAlchemy")
    except ImportError as e:
        print(f"  ✗ Flask-SQLAlchemy: {e}")
        return False

    try:
        from PyPDF2 import PdfReader
        print("  ✓ PyPDF2")
    except ImportError as e:
        print(f"  ✗ PyPDF2: {e}")
        return False

    try:
        from reportlab.pdfgen import canvas
        print("  ✓ ReportLab")
    except ImportError as e:
        print(f"  ✗ ReportLab: {e}")
        return False

    try:
        from PIL import Image
        print("  ✓ Pillow")
    except ImportError as e:
        print(f"  ✗ Pillow: {e}")
        return False

    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        print("  ✓ cryptography")
    except ImportError as e:
        print(f"  ✗ cryptography: {e}")
        return False

    # Optional: rembg
    try:
        from rembg import remove
        print("  ✓ rembg (optional - AI background removal)")
    except ImportError:
        print("  ⚠ rembg not installed (will use simple background removal)")

    return True


def test_app_creation():
    """Test that the Flask app can be created."""
    print("\nTesting app creation...")

    try:
        from app import app, db, create_directories
        print("  ✓ App imported successfully")

        create_directories()
        print("  ✓ Directories created")

        with app.app_context():
            db.create_all()
            print("  ✓ Database initialized")

        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_encryption():
    """Test encryption functionality."""
    print("\nTesting encryption...")

    try:
        from encryption import SignatureEncryption

        enc = SignatureEncryption()
        test_data = b"Hello, World!"

        encrypted = enc.encrypt(test_data)
        decrypted = enc.decrypt(encrypted)

        if decrypted == test_data:
            print("  ✓ Encryption/decryption working")
            return True
        else:
            print("  ✗ Decrypted data doesn't match")
            return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_signature_processing():
    """Test signature processing (without actual image)."""
    print("\nTesting signature processing...")

    try:
        from signature_processor import remove_background_simple, HAS_REMBG

        if HAS_REMBG:
            print("  ✓ Using rembg for background removal")
        else:
            print("  ⚠ Using simple threshold-based background removal")

        print("  ✓ Signature processor loaded")
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def main():
    print("=" * 50)
    print("Medical PDF Signer - Backend Test")
    print("=" * 50)

    all_passed = True

    if not test_imports():
        all_passed = False
        print("\n⚠ Some imports failed. Run: pip install -r requirements.txt")

    if not test_encryption():
        all_passed = False

    if not test_signature_processing():
        all_passed = False

    if not test_app_creation():
        all_passed = False

    print("\n" + "=" * 50)
    if all_passed:
        print("✓ All tests passed! Backend is ready.")
        print("\nRun the server with: python app.py")
        print("Default admin: admin@example.com / admin123")
    else:
        print("✗ Some tests failed. Please fix the issues above.")
    print("=" * 50)

    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
