"""
Supabase client module for database and storage operations.
Provides async-compatible wrapper around Supabase Python client.
"""

from typing import Any, Optional
from functools import lru_cache
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions

from config import settings


class SupabaseClient:
    """
    Wrapper for Supabase client with convenience methods.
    """
    
    def __init__(self):
        """Initialize Supabase client."""
        options = ClientOptions(
            postgrest_client_timeout=10,
            storage_client_timeout=30,
        )
        try:
            self._client: Client = create_client(
                settings.supabase_url,
                settings.supabase_key,
                options=options
            )
            self._connected = True
        except Exception as e:
            print(f"⚠️ Supabase connection failed: {e}")
            print("Running in offline/demo mode. Update SUPABASE_KEY in .env")
            self._client = None
            self._connected = False
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    @property
    def client(self) -> Client:
        """Get the raw Supabase client."""
        if not self._connected:
            raise RuntimeError("Supabase not connected. Check SUPABASE_KEY in .env")
        return self._client
    
    # ================== Database Operations ==================
    
    def table(self, table_name: str):
        """Get a table reference for queries."""
        if not self._connected:
            raise RuntimeError("Supabase not connected. Check SUPABASE_KEY in .env")
        return self._client.table(table_name)
    
    async def insert(self, table_name: str, data: dict) -> dict:
        """
        Insert a record into a table.
        
        Args:
            table_name: Name of the table
            data: Record data to insert
            
        Returns:
            Inserted record with generated fields
        """
        result = self._client.table(table_name).insert(data).execute()
        return result.data[0] if result.data else {}
    
    async def select(
        self,
        table_name: str,
        columns: str = "*",
        filters: Optional[dict] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        descending: bool = False
    ) -> list[dict]:
        """
        Select records from a table.
        
        Args:
            table_name: Name of the table
            columns: Columns to select (default "*")
            filters: Dict of column:value equality filters
            order_by: Column to order by
            limit: Maximum records to return
            descending: Sort descending if True
            
        Returns:
            List of matching records
        """
        query = self._client.table(table_name).select(columns)
        
        if filters:
            for column, value in filters.items():
                query = query.eq(column, value)
        
        if order_by:
            query = query.order(order_by, desc=descending)
        
        if limit:
            query = query.limit(limit)
        
        result = query.execute()
        return result.data or []
    
    async def update(
        self,
        table_name: str,
        data: dict,
        filters: dict
    ) -> list[dict]:
        """
        Update records in a table.
        
        Args:
            table_name: Name of the table
            data: Fields to update
            filters: Dict of column:value equality filters
            
        Returns:
            Updated records
        """
        query = self._client.table(table_name).update(data)
        
        for column, value in filters.items():
            query = query.eq(column, value)
        
        result = query.execute()
        return result.data or []
    
    async def delete(self, table_name: str, filters: dict) -> list[dict]:
        """
        Delete records from a table.
        
        Args:
            table_name: Name of the table
            filters: Dict of column:value equality filters
            
        Returns:
            Deleted records
        """
        query = self._client.table(table_name).delete()
        
        for column, value in filters.items():
            query = query.eq(column, value)
        
        result = query.execute()
        return result.data or []
    
    async def upsert(self, table_name: str, data: dict) -> dict:
        """
        Insert or update a record.
        
        Args:
            table_name: Name of the table
            data: Record data (must include primary key)
            
        Returns:
            Upserted record
        """
        result = self._client.table(table_name).upsert(data).execute()
        return result.data[0] if result.data else {}
    
    # ================== Storage Operations ==================
    
    def get_storage_bucket(self, bucket_name: Optional[str] = None):
        """Get a storage bucket reference."""
        bucket = bucket_name or settings.supabase_storage_bucket
        return self._client.storage.from_(bucket)
    
    async def upload_file(
        self,
        file_path: str,
        file_content: bytes,
        content_type: str,
        bucket_name: Optional[str] = None
    ) -> str:
        """
        Upload a file to storage.
        
        Args:
            file_path: Path/name for the file in storage
            file_content: File content as bytes
            content_type: MIME type of the file
            bucket_name: Storage bucket name (uses default if None)
            
        Returns:
            Public URL or path of the uploaded file
        """
        bucket = self.get_storage_bucket(bucket_name)
        result = bucket.upload(
            file_path,
            file_content,
            {"content-type": content_type}
        )
        return file_path
    
    async def download_file(
        self,
        file_path: str,
        bucket_name: Optional[str] = None
    ) -> bytes:
        """
        Download a file from storage.
        
        Args:
            file_path: Path of the file in storage
            bucket_name: Storage bucket name (uses default if None)
            
        Returns:
            File content as bytes
        """
        bucket = self.get_storage_bucket(bucket_name)
        return bucket.download(file_path)
    
    async def delete_file(
        self,
        file_paths: list[str],
        bucket_name: Optional[str] = None
    ) -> None:
        """
        Delete files from storage.
        
        Args:
            file_paths: List of file paths to delete
            bucket_name: Storage bucket name (uses default if None)
        """
        bucket = self.get_storage_bucket(bucket_name)
        bucket.remove(file_paths)
    
    def get_public_url(
        self,
        file_path: str,
        bucket_name: Optional[str] = None
    ) -> str:
        """
        Get public URL for a file.
        
        Args:
            file_path: Path of the file in storage
            bucket_name: Storage bucket name (uses default if None)
            
        Returns:
            Public URL of the file
        """
        bucket = self.get_storage_bucket(bucket_name)
        return bucket.get_public_url(file_path)
    
    async def create_signed_url(
        self,
        file_path: str,
        expires_in: int = 3600,
        bucket_name: Optional[str] = None
    ) -> str:
        """
        Create a signed URL for temporary access.
        
        Args:
            file_path: Path of the file in storage
            expires_in: URL expiration in seconds (default 1 hour)
            bucket_name: Storage bucket name (uses default if None)
            
        Returns:
            Signed URL with temporary access
        """
        bucket = self.get_storage_bucket(bucket_name)
        result = bucket.create_signed_url(file_path, expires_in)
        return result.get("signedURL", "")


@lru_cache()
def get_supabase_client() -> SupabaseClient:
    """Get singleton Supabase client instance."""
    return SupabaseClient()


# Convenience access
supabase = get_supabase_client()
