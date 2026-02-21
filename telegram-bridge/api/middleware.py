"""
Telegram API middleware.

Handles common operations between the application and Telegram API such as
authentication, error handling, and entity type conversion.
"""

import logging
from typing import Dict, Any, Optional, Tuple, List, Callable
from datetime import datetime
from functools import wraps

from telethon.tl.types import (
    User, Chat, Channel, Message, Dialog,
    MessageMediaPhoto, MessageMediaDocument, MessageMediaWebPage,
    DocumentAttributeFilename, DocumentAttributeAudio, DocumentAttributeVideo,
    DocumentAttributeSticker, DocumentAttributeAnimated
)
from telethon.utils import get_display_name

from api.client import TelegramApiClient

logger = logging.getLogger(__name__)


def handle_telegram_errors(func):
    """Decorator to handle Telegram API errors."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Telegram API error in {func.__name__}: {e}")
            return None
    return wrapper


class TelegramMiddleware:
    """Middleware for Telegram API operations."""
    
    def __init__(self, client: TelegramApiClient):
        """Initialize the middleware with a Telegram client.
        
        Args:
            client: Initialized Telegram API client
        """
        self.client = client
        
    async def process_chat_entity(self, entity: Any) -> Dict[str, Any]:
        """Process a chat entity and convert it to a dictionary.
        
        Args:
            entity: Chat entity from Telegram API
            
        Returns:
            Dict: Standardized chat representation
        """
        if isinstance(entity, User):
            chat_type = "user"
            title = get_display_name(entity)
            username = entity.username
        elif isinstance(entity, Chat):
            chat_type = "group"
            title = entity.title
            username = None
        elif isinstance(entity, Channel):
            chat_type = "channel" if entity.broadcast else "supergroup"
            title = entity.title
            username = entity.username
        else:
            logger.warning(f"Unknown chat type: {type(entity)}")
            return {}
            
        return {
            "id": entity.id,
            "title": title,
            "username": username,
            "type": chat_type
        }
        
    @handle_telegram_errors
    async def process_dialog(self, dialog: Dialog) -> Dict[str, Any]:
        """Process a dialog and convert it to a dictionary.
        
        Args:
            dialog: Dialog from Telegram API
            
        Returns:
            Dict: Standardized dialog representation
        """
        chat_info = await self.process_chat_entity(dialog.entity)
        chat_info["last_message_time"] = dialog.date
        return chat_info
        
    @handle_telegram_errors
    async def process_message(self, message: Message) -> Optional[Dict[str, Any]]:
        """Process a message and convert it to a dictionary.

        Args:
            message: Message from Telegram API

        Returns:
            Dict: Standardized message representation
        """
        # Get the chat
        chat = message.chat
        if not chat:
            return None

        # Process media information
        media_info = self._extract_media_info(message)

        # Skip messages with no text AND no media
        if not message.text and not media_info["has_media"]:
            return None

        chat_info = await self.process_chat_entity(chat)

        # Get sender information
        sender = await message.get_sender()
        sender_id = sender.id if sender else 0
        sender_name = get_display_name(sender) if sender else "Unknown"

        # Check if the message is from the current user
        my_id = (await self.client.get_me()).id
        is_from_me = sender_id == my_id

        return {
            "id": message.id,
            "chat_id": chat_info["id"],
            "chat_title": chat_info["title"],
            "sender_id": sender_id,
            "sender_name": sender_name,
            "content": message.text or "",
            "timestamp": message.date,
            "is_from_me": is_from_me,
            **media_info
        }

    def _extract_media_info(self, message: Message) -> Dict[str, Any]:
        """Extract media information from a message.

        Args:
            message: Message from Telegram API

        Returns:
            Dict: Media information
        """
        result = {
            "has_media": False,
            "media_type": None,
            "file_id": None,
            "file_name": None,
            "file_size": None,
            "mime_type": None,
        }

        if not message.media:
            return result

        media = message.media

        if isinstance(media, MessageMediaPhoto):
            result["has_media"] = True
            result["media_type"] = "photo"
            if media.photo:
                result["file_id"] = str(media.photo.id)
                # Photos don't have a direct file size in the photo object
                # Size is in the largest PhotoSize
                if hasattr(media.photo, 'sizes') and media.photo.sizes:
                    largest = max(media.photo.sizes, key=lambda s: getattr(s, 'size', 0) if hasattr(s, 'size') else 0)
                    result["file_size"] = getattr(largest, 'size', None)
            result["mime_type"] = "image/jpeg"
            result["file_name"] = f"photo_{message.id}.jpg"

        elif isinstance(media, MessageMediaDocument):
            result["has_media"] = True
            doc = media.document
            if doc:
                result["file_id"] = str(doc.id)
                result["file_size"] = doc.size
                result["mime_type"] = doc.mime_type

                # Determine media type and filename from attributes
                for attr in doc.attributes:
                    if isinstance(attr, DocumentAttributeFilename):
                        result["file_name"] = attr.file_name
                    elif isinstance(attr, DocumentAttributeAudio):
                        if attr.voice:
                            result["media_type"] = "voice"
                        else:
                            result["media_type"] = "audio"
                    elif isinstance(attr, DocumentAttributeVideo):
                        if attr.round_message:
                            result["media_type"] = "video_note"
                        else:
                            result["media_type"] = "video"
                    elif isinstance(attr, DocumentAttributeSticker):
                        result["media_type"] = "sticker"
                    elif isinstance(attr, DocumentAttributeAnimated):
                        result["media_type"] = "animation"

                # Default media type based on mime type if not set
                if not result["media_type"]:
                    mime = doc.mime_type or ""
                    if mime.startswith("image/"):
                        result["media_type"] = "document_image"
                    elif mime.startswith("video/"):
                        result["media_type"] = "video"
                    elif mime.startswith("audio/"):
                        result["media_type"] = "audio"
                    else:
                        result["media_type"] = "document"

                # Generate filename if not found
                if not result["file_name"]:
                    ext = self._get_extension_from_mime(doc.mime_type)
                    result["file_name"] = f"{result['media_type']}_{message.id}{ext}"

        elif isinstance(media, MessageMediaWebPage):
            # Web page previews - not a downloadable attachment
            return result

        return result

    def _get_extension_from_mime(self, mime_type: Optional[str]) -> str:
        """Get file extension from mime type."""
        if not mime_type:
            return ""
        mime_to_ext = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "video/mp4": ".mp4",
            "video/quicktime": ".mov",
            "audio/mpeg": ".mp3",
            "audio/ogg": ".ogg",
            "application/pdf": ".pdf",
            "application/zip": ".zip",
        }
        return mime_to_ext.get(mime_type, "")
        
    @handle_telegram_errors
    async def find_entity_by_name_or_id(self, recipient: str) -> Optional[Any]:
        """Find an entity by name or ID.
        
        Args:
            recipient: Recipient identifier (ID, username, or title)
            
        Returns:
            Any: Found entity or None
        """
        # Try to parse as an integer (chat ID)
        try:
            chat_id = int(recipient)
            return await self.client.get_entity(chat_id)
        except ValueError:
            pass
            
        # Not an integer, try as username
        if recipient.startswith("@"):
            recipient = recipient[1:]  # Remove @ if present
            
        try:
            return await self.client.get_entity(recipient)
        except Exception:
            logger.error(f"Could not find entity: {recipient}")
            return None