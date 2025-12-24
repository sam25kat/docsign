"""
Encryption utilities for secure signature storage.
Uses AES-256-GCM for authenticated encryption.
"""

import os
import hashlib
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class SignatureEncryption:
    def __init__(self, key: bytes = None):
        """
        Initialize encryption with a key.
        If no key provided, generates a new one.
        """
        if key is None:
            self.key = AESGCM.generate_key(bit_length=256)
        else:
            # If key is a string/passphrase, derive a proper key
            if isinstance(key, str):
                key = key.encode()
            if len(key) != 32:
                # Derive 256-bit key from passphrase
                self.key = self._derive_key(key)
            else:
                self.key = key

        self.aesgcm = AESGCM(self.key)

    def _derive_key(self, passphrase: bytes, salt: bytes = None) -> bytes:
        """Derive a 256-bit key from a passphrase using PBKDF2."""
        if salt is None:
            salt = b'medical_pdf_signer_salt'  # In production, use random salt and store it

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(passphrase)

    def encrypt(self, data: bytes) -> bytes:
        """
        Encrypt data using AES-256-GCM.
        Returns: nonce (12 bytes) + ciphertext + tag
        """
        nonce = os.urandom(12)  # GCM standard nonce size
        ciphertext = self.aesgcm.encrypt(nonce, data, None)
        return nonce + ciphertext

    def decrypt(self, encrypted_data: bytes) -> bytes:
        """
        Decrypt data encrypted with AES-256-GCM.
        Expects: nonce (12 bytes) + ciphertext + tag
        """
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        return self.aesgcm.decrypt(nonce, ciphertext, None)

    def encrypt_file(self, input_path: str, output_path: str) -> str:
        """
        Encrypt a file and save to output path.
        Returns the SHA-256 hash of the original file for integrity verification.
        """
        with open(input_path, 'rb') as f:
            data = f.read()

        # Calculate hash of original data
        file_hash = hashlib.sha256(data).hexdigest()

        # Encrypt
        encrypted_data = self.encrypt(data)

        # Save encrypted file
        with open(output_path, 'wb') as f:
            f.write(encrypted_data)

        return file_hash

    def decrypt_file(self, input_path: str, output_path: str = None) -> bytes:
        """
        Decrypt a file.
        If output_path provided, saves decrypted data to file.
        Returns decrypted data.
        """
        with open(input_path, 'rb') as f:
            encrypted_data = f.read()

        decrypted_data = self.decrypt(encrypted_data)

        if output_path:
            with open(output_path, 'wb') as f:
                f.write(decrypted_data)

        return decrypted_data

    def verify_integrity(self, decrypted_data: bytes, expected_hash: str) -> bool:
        """Verify file integrity using SHA-256 hash."""
        actual_hash = hashlib.sha256(decrypted_data).hexdigest()
        return actual_hash == expected_hash

    @staticmethod
    def generate_key() -> str:
        """Generate a new encryption key and return as base64 string."""
        key = AESGCM.generate_key(bit_length=256)
        return base64.b64encode(key).decode()

    @staticmethod
    def key_from_base64(key_string: str) -> bytes:
        """Convert base64 key string back to bytes."""
        return base64.b64decode(key_string)


# Singleton instance - initialized when app starts
_encryption_instance = None


def get_encryption(key: bytes = None) -> SignatureEncryption:
    """Get or create encryption instance."""
    global _encryption_instance
    if _encryption_instance is None:
        _encryption_instance = SignatureEncryption(key)
    return _encryption_instance


def init_encryption(key: bytes):
    """Initialize encryption with a specific key."""
    global _encryption_instance
    _encryption_instance = SignatureEncryption(key)
    return _encryption_instance
