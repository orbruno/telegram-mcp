"""
Service layer for the Telegram bridge.

Connects the API middleware with database repositories to provide
high-level operations for the application.
"""

import logging
import os
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from telethon import events

from api import TelegramApiClient, TelegramMiddleware
from database import ChatRepository, MessageRepository

logger = logging.getLogger(__name__)

# Default download directory
DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'store', 'media')


class TelegramService:
    """Service for Telegram operations."""
    
    def __init__(
        self,
        telegram_client: TelegramApiClient,
        middleware: TelegramMiddleware,
        chat_repo: ChatRepository,
        message_repo: MessageRepository
    ):
        """Initialize the service.
        
        Args:
            telegram_client: Telegram API client
            middleware: Telegram middleware
            chat_repo: Chat repository
            message_repo: Message repository
        """
        self.client = telegram_client
        self.middleware = middleware
        self.chat_repo = chat_repo
        self.message_repo = message_repo
        
    async def setup(self) -> None:
        """Set up the service, connect to Telegram, and register handlers."""
        # Connect to Telegram
        await self.client.connect()
        
        # Register event handlers
        self.client.add_event_handler(self._handle_new_message, events.NewMessage)
        
    async def authorize(self) -> bool:
        """Authorize with Telegram if needed."""
        if await self.client.is_authorized():
            logger.info("Already authorized with Telegram")
            return True
            
        logger.info("Not authorized with Telegram. Interactive login required.")
        return False
        
    async def login(self, phone: str, code: str, password: Optional[str] = None) -> bool:
        """Login to Telegram.
        
        Args:
            phone: Phone number
            code: Verification code
            password: Two-factor authentication password (optional)
            
        Returns:
            bool: True if login successful, False otherwise
        """
        if password:
            return await self.client.sign_in(phone=phone, code=code, password=password)
        else:
            # First send code request
            await self.client.send_code_request(phone)
            # Then sign in with the code
            return await self.client.sign_in(phone=phone, code=code)
            
    async def sync_all_dialogs(
        self,
        dialog_limit: int = 100,
        message_limit: int = None,
        full_sync: bool = False
    ) -> None:
        """Sync all dialogs (chats) from Telegram.

        Args:
            dialog_limit: Maximum number of dialogs to retrieve
            message_limit: Maximum messages per dialog (None for all if full_sync)
            full_sync: If True, fetch all messages from each dialog
        """
        logger.info(f"Starting synchronization of dialogs (full_sync={full_sync})")

        # Get all dialogs (chats)
        dialogs = await self.client.get_dialogs(limit=dialog_limit)

        for i, dialog in enumerate(dialogs, 1):
            try:
                logger.info(f"Syncing dialog {i}/{len(dialogs)}: {dialog.name}")
                await self.sync_dialog_history(
                    dialog,
                    limit=message_limit,
                    full_sync=full_sync
                )
            except Exception as e:
                logger.error(f"Error syncing dialog {dialog.name}: {e}")

        logger.info(f"Completed synchronization of {len(dialogs)} dialogs")

    async def sync_chat_full_history(self, chat_id: int) -> Tuple[bool, str, int]:
        """Sync full message history for a specific chat.

        Args:
            chat_id: The chat ID to sync

        Returns:
            Tuple[bool, str, int]: (success, message, count)
        """
        try:
            entity = await self.client.get_entity(chat_id)
            if not entity:
                return False, f"Chat {chat_id} not found", 0

            # Get chat info
            chat_info = await self.middleware.process_chat_entity(entity)

            # Store/update chat info
            self.chat_repo.store_chat(
                chat_id=chat_info["id"],
                title=chat_info["title"],
                username=chat_info.get("username"),
                chat_type=chat_info["type"],
                last_message_time=None
            )

            # Sync all messages
            count = 0
            async for message in self.client.iter_all_messages(entity, limit=None):
                msg_info = await self.middleware.process_message(message)
                if msg_info:
                    self.message_repo.store_message(
                        message_id=msg_info["id"],
                        chat_id=msg_info["chat_id"],
                        sender_id=msg_info["sender_id"],
                        sender_name=msg_info["sender_name"],
                        content=msg_info["content"],
                        timestamp=msg_info["timestamp"],
                        is_from_me=msg_info["is_from_me"],
                        has_media=msg_info.get("has_media", False),
                        media_type=msg_info.get("media_type"),
                        file_id=msg_info.get("file_id"),
                        file_name=msg_info.get("file_name"),
                        file_size=msg_info.get("file_size"),
                        mime_type=msg_info.get("mime_type"),
                    )
                    count += 1

                if count % 500 == 0:
                    logger.info(f"Synced {count} messages from {chat_info['title']}...")

            return True, f"Synced {count} messages from {chat_info['title']}", count

        except Exception as e:
            logger.error(f"Error syncing chat {chat_id}: {e}")
            return False, f"Error: {str(e)}", 0
        
    async def sync_dialog_history(
        self,
        dialog,
        limit: int = None,
        full_sync: bool = False
    ) -> None:
        """Sync message history for a specific dialog.

        Args:
            dialog: Dialog to sync
            limit: Maximum number of messages to retrieve (None for all if full_sync)
            full_sync: If True, fetch all messages; if False, only recent (default 100)
        """
        # Process dialog entity
        chat_info = await self.middleware.process_dialog(dialog)

        if not chat_info:
            logger.warning(f"Could not process dialog: {dialog}")
            return

        # Store chat information
        self.chat_repo.store_chat(
            chat_id=chat_info["id"],
            title=chat_info["title"],
            username=chat_info.get("username"),
            chat_type=chat_info["type"],
            last_message_time=chat_info["last_message_time"]
        )

        # Determine message limit
        if full_sync:
            msg_limit = limit  # None means all messages
        else:
            msg_limit = limit or 100  # Default to 100 for quick sync

        # Use iterator for potentially large message sets
        count = 0
        async for message in self.client.iter_all_messages(dialog.entity, limit=msg_limit):
            msg_info = await self.middleware.process_message(message)
            if msg_info:
                self.message_repo.store_message(
                    message_id=msg_info["id"],
                    chat_id=msg_info["chat_id"],
                    sender_id=msg_info["sender_id"],
                    sender_name=msg_info["sender_name"],
                    content=msg_info["content"],
                    timestamp=msg_info["timestamp"],
                    is_from_me=msg_info["is_from_me"],
                    has_media=msg_info.get("has_media", False),
                    media_type=msg_info.get("media_type"),
                    file_id=msg_info.get("file_id"),
                    file_name=msg_info.get("file_name"),
                    file_size=msg_info.get("file_size"),
                    mime_type=msg_info.get("mime_type"),
                )
                count += 1

            # Log progress for large syncs
            if count % 500 == 0:
                logger.info(f"Synced {count} messages from {chat_info['title']}...")

        logger.info(f"Synced {count} messages from {chat_info['title']}")
        
    async def send_message(self, recipient: str, message: str) -> Tuple[bool, str]:
        """Send a message to a Telegram recipient.
        
        Args:
            recipient: Recipient identifier (ID, username, or title)
            message: Message text to send
            
        Returns:
            Tuple[bool, str]: Success status and message
        """
        if not self.client.client.is_connected():
            return False, "Not connected to Telegram"
            
        entity = await self.middleware.find_entity_by_name_or_id(recipient)
        
        if not entity:
            # Try to find in database
            try:
                # Try to parse as integer
                chat_id = int(recipient)
                chat = self.chat_repo.get_chat_by_id(chat_id)
                if chat:
                    entity = await self.client.get_entity(chat_id)
            except ValueError:
                # Not an integer, try to find by name
                chats = self.chat_repo.get_chats(query=recipient, limit=1)
                if chats:
                    entity = await self.client.get_entity(chats[0].id)
                    
        if not entity:
            return False, f"Recipient not found: {recipient}"
            
        # Send the message
        sent_message = await self.client.send_message(entity, message)
        
        if sent_message:
            # Process and store the sent message
            msg_info = await self.middleware.process_message(sent_message)
            if msg_info:
                self.message_repo.store_message(
                    message_id=msg_info["id"],
                    chat_id=msg_info["chat_id"],
                    sender_id=msg_info["sender_id"],
                    sender_name=msg_info["sender_name"],
                    content=msg_info["content"],
                    timestamp=msg_info["timestamp"],
                    is_from_me=msg_info["is_from_me"]
                )
            return True, f"Message sent to {recipient}"
        else:
            return False, f"Failed to send message to {recipient}"
            
    async def _handle_new_message(self, event) -> None:
        """Handle a new message event from Telegram."""
        message = event.message
        msg_info = await self.middleware.process_message(message)

        if msg_info:
            # Process and store chat information
            chat_entity = message.chat
            if chat_entity:
                chat_info = await self.middleware.process_chat_entity(chat_entity)
                self.chat_repo.store_chat(
                    chat_id=chat_info["id"],
                    title=chat_info["title"],
                    username=chat_info.get("username"),
                    chat_type=chat_info["type"],
                    last_message_time=message.date
                )

            # Store the message
            self.message_repo.store_message(
                message_id=msg_info["id"],
                chat_id=msg_info["chat_id"],
                sender_id=msg_info["sender_id"],
                sender_name=msg_info["sender_name"],
                content=msg_info["content"],
                timestamp=msg_info["timestamp"],
                is_from_me=msg_info["is_from_me"],
                has_media=msg_info.get("has_media", False),
                media_type=msg_info.get("media_type"),
                file_id=msg_info.get("file_id"),
                file_name=msg_info.get("file_name"),
                file_size=msg_info.get("file_size"),
                mime_type=msg_info.get("mime_type"),
            )

            content_preview = msg_info['content'][:30] if msg_info['content'] else "[media]"
            logger.info(
                f"Stored message: [{msg_info['timestamp']}] {msg_info['sender_name']} "
                f"in {msg_info['chat_title']}: {content_preview}..."
            )

    async def download_media(
        self,
        message_id: int,
        chat_id: int,
        download_dir: Optional[str] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """Download media from a message.

        Args:
            message_id: The message ID containing the media
            chat_id: The chat ID where the message is located
            download_dir: Optional custom download directory

        Returns:
            Tuple[bool, str, Optional[str]]: (success, status_message, local_path)
        """
        if not self.client.client.is_connected():
            return False, "Not connected to Telegram", None

        # Get the message from database to verify it has media
        db_message = self.message_repo.get_message_by_id(message_id, chat_id)
        if not db_message:
            return False, f"Message {message_id} not found in chat {chat_id}", None

        if not db_message.has_media:
            return False, "Message does not have media", None

        # Check if already downloaded
        if db_message.local_path and os.path.exists(db_message.local_path):
            return True, "Media already downloaded", db_message.local_path

        try:
            # Get the actual message from Telegram
            entity = await self.client.get_entity(chat_id)
            messages = await self.client.get_messages(entity, ids=[message_id])

            if not messages or not messages[0]:
                return False, "Could not fetch message from Telegram", None

            telegram_message = messages[0]

            if not telegram_message.media:
                return False, "Message no longer has media", None

            # Prepare download directory
            target_dir = download_dir or DOWNLOAD_DIR
            os.makedirs(target_dir, exist_ok=True)

            # Download the media
            file_name = db_message.file_name or f"media_{message_id}"
            file_path = os.path.join(target_dir, file_name)

            # Use Telethon's download_media
            downloaded_path = await self.client.download_media(
                telegram_message,
                file=file_path
            )

            if downloaded_path:
                # Update database with local path
                self.message_repo.update_local_path(message_id, chat_id, downloaded_path)
                return True, f"Downloaded to {downloaded_path}", downloaded_path
            else:
                return False, "Download failed", None

        except Exception as e:
            logger.error(f"Error downloading media: {e}")
            return False, f"Download error: {str(e)}", None

    async def get_attachments(
        self,
        chat_id: Optional[int] = None,
        media_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get list of messages with attachments.

        Args:
            chat_id: Optional chat ID to filter by
            media_type: Optional media type filter (photo, document, video, etc.)
            limit: Maximum number of results

        Returns:
            List of attachment information dictionaries
        """
        messages = self.message_repo.get_messages_with_media(
            chat_id=chat_id,
            media_type=media_type,
            limit=limit
        )

        result = []
        for msg in messages:
            result.append({
                "message_id": msg.id,
                "chat_id": msg.chat_id,
                "sender_name": msg.sender_name,
                "timestamp": msg.timestamp,
                "content": msg.content,
                "media_type": msg.media_type,
                "file_name": msg.file_name,
                "file_size": msg.file_size,
                "mime_type": msg.mime_type,
                "is_downloaded": bool(msg.local_path and os.path.exists(msg.local_path)),
                "local_path": msg.local_path,
            })

        return result