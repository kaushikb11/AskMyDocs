import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from config import settings
from db.models import ChatMessage, Conversation, Document
from fastapi.exceptions import HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select


class ChatDto:
    def __init__(self, db_engine):
        self.__db_engine = db_engine

    def get_or_create_conversation(
        self, document_id: str, conversation_id: Optional[str] = None
    ) -> Conversation:
        """Get existing conversation or create new one."""
        with Session(self.__db_engine) as session:
            # Special handling for multi-document conversations
            if document_id != "multi-doc":
                # Verify document exists for single-document conversations
                document = session.get(Document, document_id)
                if not document:
                    raise HTTPException(status_code=404, detail="Document not found")

            if conversation_id:
                # Get existing conversation
                conversation = session.get(Conversation, conversation_id)
                if conversation and conversation.document_id == document_id:
                    return conversation
                else:
                    raise HTTPException(
                        status_code=404, detail="Conversation not found"
                    )

            # Create new conversation
            new_conversation_id = str(uuid.uuid4())
            new_conversation = Conversation(
                conversation_id=new_conversation_id, document_id=document_id
            )

            session.add(new_conversation)
            session.commit()
            session.refresh(new_conversation)

            return new_conversation

    def save_message(
        self,
        conversation_id: str,
        role: str,  # "user", "assistant", "system"
        content: str,
        source_chunks: Optional[List[str]] = None,
        relevance_scores: Optional[List[float]] = None,
        response_time: Optional[float] = None,
    ) -> ChatMessage:
        """Save a chat message to database."""
        with Session(self.__db_engine) as session:
            # Verify conversation exists
            conversation = session.get(Conversation, conversation_id)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")

            # Create message
            message_id = str(uuid.uuid4())

            # Serialize lists to JSON strings
            source_chunks_json = json.dumps(source_chunks) if source_chunks else None
            relevance_scores_json = (
                json.dumps(relevance_scores) if relevance_scores else None
            )

            message = ChatMessage(
                message_id=message_id,
                conversation_id=conversation_id,
                role=role,
                content=content,
                source_chunks=source_chunks_json,
                relevance_scores=relevance_scores_json,
                response_time=response_time,
            )

            session.add(message)

            # Update conversation timestamp
            conversation.updated_at = datetime.now()
            session.add(conversation)

            session.commit()
            session.refresh(message)

            return message

    def get_conversation_history(self, conversation_id: str) -> Dict[str, any]:
        """Get conversation history with messages."""
        with Session(self.__db_engine) as session:
            conversation = session.get(Conversation, conversation_id)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")

            # Get all messages for conversation
            messages = session.exec(
                select(ChatMessage)
                .where(ChatMessage.conversation_id == conversation_id)
                .order_by(ChatMessage.timestamp)
            ).all()

            return {
                "conversation_id": conversation.conversation_id,
                "document_id": conversation.document_id,
                "created_at": conversation.created_at,
                "updated_at": conversation.updated_at,
                "messages": messages,
            }

    def get_document_conversations(
        self, document_id: str, skip: int = 0, limit: int = 10
    ) -> List[Dict[str, any]]:
        """Get all conversations for a document."""
        with Session(self.__db_engine) as session:
            # Special handling for multi-document conversations
            if document_id != "multi-doc":
                # Verify document exists for single-document conversations
                document = session.get(Document, document_id)
                if not document:
                    raise HTTPException(status_code=404, detail="Document not found")

            conversations = session.exec(
                select(Conversation)
                .where(Conversation.document_id == document_id)
                .order_by(Conversation.updated_at.desc())
                .offset(skip)
                .limit(limit)
            ).all()

            result = []
            for conv in conversations:
                # Get message count and last message
                messages = session.exec(
                    select(ChatMessage)
                    .where(ChatMessage.conversation_id == conv.conversation_id)
                    .order_by(ChatMessage.timestamp.desc())
                ).all()

                last_message = (
                    messages[0].content[:100] + "..."
                    if messages and len(messages[0].content) > 100
                    else (messages[0].content if messages else "")
                )

                # Handle document filename for multi-doc conversations
                document_filename = (
                    "All Documents" if document_id == "multi-doc" else None
                )
                if document_id != "multi-doc":
                    document = session.get(Document, document_id)
                    document_filename = (
                        document.filename if document else "Unknown Document"
                    )

                result.append(
                    {
                        "conversation_id": conv.conversation_id,
                        "document_id": conv.document_id,
                        "document_filename": document_filename,
                        "last_message": last_message,
                        "message_count": len(messages),
                        "created_at": conv.created_at,
                        "updated_at": conv.updated_at,
                    }
                )

            return result

    def get_all_conversations(
        self, skip: int = 0, limit: int = 20
    ) -> List[Dict[str, any]]:
        """Get all conversations across all documents."""
        with Session(self.__db_engine) as session:
            conversations = session.exec(
                select(Conversation)
                .order_by(Conversation.updated_at.desc())
                .offset(skip)
                .limit(limit)
            ).all()

            result = []
            for conv in conversations:
                # Get message count and last message
                messages = session.exec(
                    select(ChatMessage)
                    .where(ChatMessage.conversation_id == conv.conversation_id)
                    .order_by(ChatMessage.timestamp.desc())
                ).all()

                last_message = (
                    messages[0].content[:100] + "..."
                    if messages and len(messages[0].content) > 100
                    else (messages[0].content if messages else "")
                )

                # Determine document filename
                document_filename = "All Documents"  # Default for multi-doc
                if conv.document_id != "multi-doc":
                    document = session.get(Document, conv.document_id)
                    document_filename = (
                        document.filename if document else "Unknown Document"
                    )

                result.append(
                    {
                        "conversation_id": conv.conversation_id,
                        "document_id": conv.document_id,
                        "document_filename": document_filename,
                        "conversation_type": (
                            "multi-document"
                            if conv.document_id == "multi-doc"
                            else "single-document"
                        ),
                        "last_message": last_message,
                        "message_count": len(messages),
                        "created_at": conv.created_at,
                        "updated_at": conv.updated_at,
                    }
                )

            return result

    def clear_conversation(self, conversation_id: str) -> Dict[str, str]:
        """Clear all messages from a conversation."""
        with Session(self.__db_engine) as session:
            conversation = session.get(Conversation, conversation_id)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")

            # Delete all messages
            messages = session.exec(
                select(ChatMessage).where(
                    ChatMessage.conversation_id == conversation_id
                )
            ).all()

            for message in messages:
                session.delete(message)

            # Update conversation timestamp
            conversation.updated_at = datetime.now()
            session.add(conversation)

            session.commit()

            return {
                "conversation_id": conversation_id,
                "message": "Conversation cleared successfully",
            }

    def delete_conversation(self, conversation_id: str) -> Dict[str, str]:
        """Delete entire conversation and all messages."""
        with Session(self.__db_engine) as session:
            conversation = session.get(Conversation, conversation_id)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")

            # Delete all messages first (due to foreign key constraints)
            messages = session.exec(
                select(ChatMessage).where(
                    ChatMessage.conversation_id == conversation_id
                )
            ).all()

            for message in messages:
                session.delete(message)

            # Delete conversation
            session.delete(conversation)
            session.commit()

            return {
                "conversation_id": conversation_id,
                "message": "Conversation deleted successfully",
            }

    def get_conversation_by_document(
        self, document_id: str, conversation_id: str
    ) -> Optional[Conversation]:
        """Get conversation by ID and verify it belongs to document."""
        with Session(self.__db_engine) as session:
            conversation = session.get(Conversation, conversation_id)

            if conversation and conversation.document_id == document_id:
                return conversation

            return None
