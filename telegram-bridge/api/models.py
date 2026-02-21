"""
API models for data transfer.

Defines Pydantic models for request and response data validation.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ChatModel(BaseModel):
    """Model representing a Telegram chat."""
    id: int
    title: str
    username: Optional[str] = None
    type: str
    last_message_time: Optional[datetime] = None


class MessageModel(BaseModel):
    """Model representing a Telegram message."""
    id: int
    chat_id: int
    chat_title: str
    sender_id: int
    sender_name: str
    content: str
    timestamp: datetime
    is_from_me: bool = False


class MessageContextModel(BaseModel):
    """Model representing a message with its context."""
    message: MessageModel
    before: List[MessageModel] = []
    after: List[MessageModel] = []


class SendMessageRequest(BaseModel):
    """Model for sending message requests."""
    recipient: str
    message: str


class SendMessageResponse(BaseModel):
    """Model for sending message responses."""
    success: bool
    message: str


class AttachmentModel(BaseModel):
    """Model representing a message attachment."""
    message_id: int
    chat_id: int
    sender_name: str
    timestamp: datetime
    content: Optional[str] = None
    media_type: str
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    is_downloaded: bool = False
    local_path: Optional[str] = None


class DownloadRequest(BaseModel):
    """Model for download requests."""
    message_id: int
    chat_id: int
    download_dir: Optional[str] = None


class DownloadResponse(BaseModel):
    """Model for download responses."""
    success: bool
    message: str
    local_path: Optional[str] = None


class SyncRequest(BaseModel):
    """Model for sync requests."""
    chat_id: int


class SyncResponse(BaseModel):
    """Model for sync responses."""
    success: bool
    message: str
    count: int = 0