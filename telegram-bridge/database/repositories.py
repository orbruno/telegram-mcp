"""
Repository classes for database operations.

Provides abstraction for data access operations on Telegram chats and messages.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import desc, or_, and_

from database.base import get_session
from database.models import Chat, Message


class ChatRepository:
    """Repository for chat operations."""
    
    def store_chat(
        self,
        chat_id: int,
        title: str,
        username: Optional[str],
        chat_type: str,
        last_message_time: datetime,
    ) -> None:
        """Store a chat in the database."""
        session = get_session()
        try:
            chat = session.query(Chat).filter_by(id=chat_id).first()
            
            if chat:
                # Update existing chat
                chat.title = title
                chat.username = username
                chat.type = chat_type
                chat.last_message_time = last_message_time
            else:
                # Create new chat
                chat = Chat(
                    id=chat_id,
                    title=title,
                    username=username,
                    type=chat_type,
                    last_message_time=last_message_time
                )
                session.add(chat)
                
            session.commit()
        finally:
            session.close()
    
    def get_chats(
        self,
        query: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        chat_type: Optional[str] = None,
        sort_by: str = "last_message_time"
    ) -> List[Chat]:
        """Get chats from the database."""
        session = get_session()
        try:
            # Build query
            db_query = session.query(Chat)
            
            # Apply filters
            if query:
                db_query = db_query.filter(
                    or_(
                        Chat.title.ilike(f"%{query}%"),
                        Chat.username.ilike(f"%{query}%")
                    )
                )
            
            if chat_type:
                db_query = db_query.filter(Chat.type == chat_type)
                
            # Apply sorting
            if sort_by == "last_message_time":
                db_query = db_query.order_by(desc(Chat.last_message_time))
            else:
                db_query = db_query.order_by(Chat.title)
                
            # Apply pagination
            db_query = db_query.limit(limit).offset(offset)
            
            return db_query.all()
        finally:
            session.close()
    
    def get_chat_by_id(self, chat_id: int) -> Optional[Chat]:
        """Get a chat by its ID."""
        session = get_session()
        try:
            return session.query(Chat).filter_by(id=chat_id).first()
        finally:
            session.close()


class MessageRepository:
    """Repository for message operations."""

    def store_message(
        self,
        message_id: int,
        chat_id: int,
        sender_id: int,
        sender_name: str,
        content: str,
        timestamp: datetime,
        is_from_me: bool,
        has_media: bool = False,
        media_type: Optional[str] = None,
        file_id: Optional[str] = None,
        file_name: Optional[str] = None,
        file_size: Optional[int] = None,
        mime_type: Optional[str] = None,
    ) -> None:
        """Store a message in the database."""
        # Allow messages with media even if content is empty
        if not content and not has_media:
            return

        session = get_session()
        try:
            message = session.query(Message).filter_by(
                id=message_id, chat_id=chat_id
            ).first()

            if message:
                # Update existing message
                message.sender_id = sender_id
                message.sender_name = sender_name
                message.content = content
                message.timestamp = timestamp
                message.is_from_me = is_from_me
                message.has_media = has_media
                message.media_type = media_type
                message.file_id = file_id
                message.file_name = file_name
                message.file_size = file_size
                message.mime_type = mime_type
            else:
                # Create new message
                message = Message(
                    id=message_id,
                    chat_id=chat_id,
                    sender_id=sender_id,
                    sender_name=sender_name,
                    content=content or "",
                    timestamp=timestamp,
                    is_from_me=is_from_me,
                    has_media=has_media,
                    media_type=media_type,
                    file_id=file_id,
                    file_name=file_name,
                    file_size=file_size,
                    mime_type=mime_type,
                )
                session.add(message)

            session.commit()
        finally:
            session.close()

    def get_messages_with_media(
        self,
        chat_id: Optional[int] = None,
        media_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Message]:
        """Get messages that have media attachments."""
        session = get_session()
        try:
            db_query = session.query(Message).filter(Message.has_media == True)

            if chat_id:
                db_query = db_query.filter(Message.chat_id == chat_id)

            if media_type:
                db_query = db_query.filter(Message.media_type == media_type)

            db_query = db_query.order_by(desc(Message.timestamp))
            db_query = db_query.limit(limit).offset(offset)

            return db_query.all()
        finally:
            session.close()

    def update_local_path(
        self,
        message_id: int,
        chat_id: int,
        local_path: str
    ) -> bool:
        """Update the local path for a downloaded attachment."""
        session = get_session()
        try:
            message = session.query(Message).filter_by(
                id=message_id, chat_id=chat_id
            ).first()

            if message:
                message.local_path = local_path
                session.commit()
                return True
            return False
        finally:
            session.close()

    def get_message_by_id(self, message_id: int, chat_id: int) -> Optional[Message]:
        """Get a specific message by ID and chat_id."""
        session = get_session()
        try:
            return session.query(Message).filter_by(
                id=message_id, chat_id=chat_id
            ).first()
        finally:
            session.close()
    
    def get_messages(
        self,
        chat_id: Optional[int] = None,
        sender_id: Optional[int] = None,
        query: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        date_range: Optional[Tuple[datetime, datetime]] = None,
    ) -> List[Message]:
        """Get messages from the database."""
        session = get_session()
        try:
            # Build query
            db_query = session.query(Message).join(Chat)
            
            # Apply filters
            filters = []
            
            if chat_id:
                filters.append(Message.chat_id == chat_id)
                
            if sender_id:
                filters.append(Message.sender_id == sender_id)
                
            if query:
                filters.append(Message.content.ilike(f"%{query}%"))
                
            if date_range:
                start_date, end_date = date_range
                filters.append(and_(
                    Message.timestamp >= start_date,
                    Message.timestamp <= end_date
                ))
                
            if filters:
                db_query = db_query.filter(and_(*filters))
                
            # Apply sorting and pagination
            db_query = db_query.order_by(desc(Message.timestamp))
            db_query = db_query.limit(limit).offset(offset)
            
            return db_query.all()
        finally:
            session.close()
    
    def get_message_context(
        self,
        message_id: int,
        chat_id: int,
        before: int = 5,
        after: int = 5
    ) -> Dict[str, Any]:
        """Get context around a specific message."""
        session = get_session()
        try:
            # Get the target message
            target_message = session.query(Message).filter_by(
                id=message_id, chat_id=chat_id
            ).first()
            
            if not target_message:
                raise ValueError(f"Message with ID {message_id} in chat {chat_id} not found")
                
            # Get messages before
            before_messages = session.query(Message).filter(
                Message.chat_id == chat_id,
                Message.timestamp < target_message.timestamp
            ).order_by(desc(Message.timestamp)).limit(before).all()
            
            # Get messages after
            after_messages = session.query(Message).filter(
                Message.chat_id == chat_id,
                Message.timestamp > target_message.timestamp
            ).order_by(Message.timestamp).limit(after).all()
            
            return {
                "message": target_message,
                "before": before_messages,
                "after": after_messages
            }
        finally:
            session.close()