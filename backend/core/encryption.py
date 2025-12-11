"""
AES-256 GCM Encryption module for secure media handling.
Provides server-side encryption with unique nonce per file.
"""

import os
import base64
import secrets
from typing import Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class EncryptionService:
    """
    AES-256 GCM encryption service for media files.
    Uses unique nonce per encryption operation for security.
    """
    
    NONCE_SIZE = 12  # 96 bits recommended for GCM
    KEY_SIZE = 32    # 256 bits
    
    def __init__(self, encryption_key: str):
        """
        Initialize encryption service with base64-encoded key.
        
        Args:
            encryption_key: Base64-encoded 32-byte key
        """
        self._key = self._derive_key(encryption_key)
        self._aesgcm = AESGCM(self._key)
    
    def _derive_key(self, key_string: str) -> bytes:
        """
        Derive a proper 256-bit key from the provided string.
        
        Args:
            key_string: Input key string (base64 or plain text)
            
        Returns:
            32-byte key suitable for AES-256
        """
        try:
            # Try to decode as base64 first
            decoded = base64.b64decode(key_string)
            if len(decoded) == self.KEY_SIZE:
                return decoded
        except Exception:
            pass
        
        # Derive key using PBKDF2 if not valid base64 key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.KEY_SIZE,
            salt=b"couple_chat_ai_salt_v1",  # Fixed salt for determinism
            iterations=100000,
        )
        return kdf.derive(key_string.encode())
    
    def encrypt(self, plaintext: bytes, associated_data: bytes | None = None) -> Tuple[bytes, bytes]:
        """
        Encrypt data using AES-256-GCM with a unique nonce.
        
        Args:
            plaintext: Data to encrypt
            associated_data: Optional additional authenticated data
            
        Returns:
            Tuple of (nonce, ciphertext) both as bytes
        """
        nonce = secrets.token_bytes(self.NONCE_SIZE)
        ciphertext = self._aesgcm.encrypt(nonce, plaintext, associated_data)
        return nonce, ciphertext
    
    def decrypt(self, nonce: bytes, ciphertext: bytes, associated_data: bytes | None = None) -> bytes:
        """
        Decrypt data using AES-256-GCM.
        
        Args:
            nonce: The nonce used during encryption
            ciphertext: The encrypted data
            associated_data: Optional additional authenticated data (must match encryption)
            
        Returns:
            Decrypted plaintext bytes
            
        Raises:
            cryptography.exceptions.InvalidTag: If decryption fails (wrong key or tampered data)
        """
        return self._aesgcm.decrypt(nonce, ciphertext, associated_data)
    
    def encrypt_to_base64(self, plaintext: bytes, associated_data: bytes | None = None) -> str:
        """
        Encrypt data and return as base64 string with embedded nonce.
        
        Format: base64(nonce + ciphertext)
        
        Args:
            plaintext: Data to encrypt
            associated_data: Optional additional authenticated data
            
        Returns:
            Base64-encoded string containing nonce and ciphertext
        """
        nonce, ciphertext = self.encrypt(plaintext, associated_data)
        combined = nonce + ciphertext
        return base64.b64encode(combined).decode('utf-8')
    
    def decrypt_from_base64(self, encrypted_data: str, associated_data: bytes | None = None) -> bytes:
        """
        Decrypt base64-encoded data with embedded nonce.
        
        Args:
            encrypted_data: Base64 string from encrypt_to_base64
            associated_data: Optional additional authenticated data
            
        Returns:
            Decrypted plaintext bytes
        """
        combined = base64.b64decode(encrypted_data)
        nonce = combined[:self.NONCE_SIZE]
        ciphertext = combined[self.NONCE_SIZE:]
        return self.decrypt(nonce, ciphertext, associated_data)


def generate_encryption_key() -> str:
    """
    Generate a new random encryption key.
    
    Returns:
        Base64-encoded 32-byte key suitable for AES-256
    """
    key = secrets.token_bytes(32)
    return base64.b64encode(key).decode('utf-8')


# Singleton instance - initialized lazily
_encryption_service: EncryptionService | None = None


def get_encryption_service() -> EncryptionService:
    """
    Get the singleton encryption service instance.
    
    Returns:
        Configured EncryptionService instance
    """
    global _encryption_service
    if _encryption_service is None:
        from config import settings
        _encryption_service = EncryptionService(settings.encryption_key)
    return _encryption_service
