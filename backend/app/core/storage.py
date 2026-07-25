"""
core/storage.py

Supabase Storage helper — uploads files to a configured bucket.
"""
from __future__ import annotations

import uuid
import logging
from supabase import create_client, Client

from core.config import settings

logger = logging.getLogger(__name__)

_client: Client | None = None


def _get_client() -> Client:
    """Lazily initialize and return the Supabase client."""
    global _client
    if _client is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_KEY must be set in .env to use storage."
            )
        _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _client


def upload_file(
    file_bytes: bytes,
    original_filename: str,
    ticket_id: uuid.UUID,
    content_type: str = "image/jpeg",
) -> str:
    """
    Upload a single file to Supabase Storage and return the public URL.

    Files are stored under: {bucket}/{ticket_id}/{unique_filename}
    """
    client = _get_client()
    bucket = settings.SUPABASE_STORAGE_BUCKET

    # Generate a unique filename to prevent collisions
    ext = original_filename.rsplit(".", 1)[-1] if "." in original_filename else "jpg"
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    path = f"{ticket_id}/{unique_name}"

    client.storage.from_(bucket).upload(
        path,
        file_bytes,
        {"content-type": content_type},
    )

    # Build the public URL
    public_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}"
    return public_url
