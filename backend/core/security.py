"""
Security module for request validation and content filtering.
Handles file validation, content safety checks, and room security.
"""

import hashlib
import secrets
import string
from typing import Tuple
from enum import Enum

from config import settings


class ContentCategory(str, Enum):
    """Content safety categories."""
    SAFE = "safe"
    NSFW = "nsfw"
    ILLEGAL = "illegal"


class FileValidationError(Exception):
    """Raised when file validation fails."""
    pass


class SecurityService:
    """
    Security service for content validation and room security.
    """
    
    # Keywords that indicate potentially illegal content
    ILLEGAL_KEYWORDS = [
        "minor", "child", "underage", "violence", "gore", 
        "abuse", "illegal", "weapon", "harm"
    ]
    
    @staticmethod
    def generate_room_secret(length: int = 32) -> str:
        """
        Generate a cryptographically secure room secret.
        
        Args:
            length: Length of the secret (default 32)
            
        Returns:
            Secure random string
        """
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def hash_secret(secret: str) -> str:
        """
        Hash a room secret for storage.
        
        Args:
            secret: Plain text secret
            
        Returns:
            SHA-256 hash of the secret
        """
        return hashlib.sha256(secret.encode()).hexdigest()
    
    @staticmethod
    def verify_secret(plain_secret: str, hashed_secret: str) -> bool:
        """
        Verify a secret against its hash.
        
        Args:
            plain_secret: Plain text secret to verify
            hashed_secret: Stored hash to compare against
            
        Returns:
            True if secrets match
        """
        return SecurityService.hash_secret(plain_secret) == hashed_secret
    
    @staticmethod
    def validate_file(
        content: bytes,
        content_type: str,
        filename: str
    ) -> Tuple[bool, str]:
        """
        Validate uploaded file for size, type, and basic safety.
        
        Args:
            content: File content bytes
            content_type: MIME type of the file
            filename: Original filename
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file size
        max_size = settings.max_file_size_mb * 1024 * 1024
        if len(content) > max_size:
            return False, f"File exceeds maximum size of {settings.max_file_size_mb}MB"
        
        # Check content type
        allowed_types = settings.allowed_image_types + settings.allowed_audio_types
        if content_type not in allowed_types:
            return False, f"File type '{content_type}' is not allowed"
        
        # Check for empty file
        if len(content) == 0:
            return False, "File is empty"
        
        # Basic magic byte validation for images
        if content_type in settings.allowed_image_types:
            if not SecurityService._validate_image_magic_bytes(content, content_type):
                return False, "File content does not match declared type"
        
        return True, ""
    
    @staticmethod
    def _validate_image_magic_bytes(content: bytes, content_type: str) -> bool:
        """
        Validate image magic bytes match the declared content type.
        
        Args:
            content: File content bytes
            content_type: Declared MIME type
            
        Returns:
            True if magic bytes match
        """
        magic_bytes = {
            "image/jpeg": [b'\xff\xd8\xff'],
            "image/png": [b'\x89PNG\r\n\x1a\n'],
            "image/gif": [b'GIF87a', b'GIF89a'],
            "image/webp": [b'RIFF'],
        }
        
        expected = magic_bytes.get(content_type, [])
        if not expected:
            return True  # Unknown type, skip validation
        
        return any(content.startswith(magic) for magic in expected)
    
    @staticmethod
    def check_content_safety(text: str) -> ContentCategory:
        """
        Check text content for safety category.
        This is a basic implementation - production should use ML models.
        
        Args:
            text: Text content to check
            
        Returns:
            ContentCategory enum value
        """
        text_lower = text.lower()
        
        # Check for illegal content keywords
        for keyword in SecurityService.ILLEGAL_KEYWORDS:
            if keyword in text_lower:
                # Context matters - this is simplified
                return ContentCategory.ILLEGAL
        
        return ContentCategory.SAFE
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to prevent path traversal and other attacks.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove path separators
        filename = filename.replace('/', '_').replace('\\', '_')
        
        # Remove null bytes and other control characters
        filename = ''.join(c for c in filename if c.isprintable() and c not in '<>:"|?*')
        
        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            filename = name[:250] + ('.' + ext if ext else '')
        
        # Generate random name if empty
        if not filename or filename.startswith('.'):
            filename = secrets.token_hex(16) + filename
        
        return filename
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """
        Generate a secure random token.
        
        Args:
            length: Desired token length
            
        Returns:
            Hex-encoded random token
        """
        return secrets.token_hex(length // 2)


# Singleton instance
security_service = SecurityService()
