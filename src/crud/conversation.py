"""
CRUD operations for AI chat conversations
"""
from datetime import datetime, timezone
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.ai_chat import ChatConversation, ChatMessage
from src.schemas.ai import ConversationCreate, ConversationUpdate


async def create_conversation(
    db: AsyncSession,
    user_id: int,
    data: ConversationCreate | None = None
) -> ChatConversation:
    """Create new conversation"""
    conversation = ChatConversation(
        user_id=user_id,
        title=data.title if data else None,
        subject=data.subject if data else None,
        message_count=0,
        total_tokens=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def get_conversation(
    db: AsyncSession,
    conversation_id: int,
    user_id: int,
    load_messages: bool = False
) -> ChatConversation | None:
    """Get conversation by ID"""
    query = select(ChatConversation).where(
        ChatConversation.id == conversation_id,
        ChatConversation.user_id == user_id
    )

    if load_messages:
        query = query.options(selectinload(ChatConversation.messages))

    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_user_conversations(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 50
) -> list[ChatConversation]:
    """Get all conversations for user"""
    query = (
        select(ChatConversation)
        .where(ChatConversation.user_id == user_id)
        .order_by(desc(ChatConversation.updated_at))
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(query)
    return list(result.scalars().all())


async def update_conversation(
    db: AsyncSession,
    conversation_id: int,
    user_id: int,
    data: ConversationUpdate
) -> ChatConversation | None:
    """Update conversation"""
    conversation = await get_conversation(db, conversation_id, user_id)
    if not conversation:
        return None

    if data.title is not None:
        conversation.title = data.title
    if data.subject is not None:
        conversation.subject = data.subject

    conversation.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(conversation)
    return conversation


async def delete_conversation(
    db: AsyncSession,
    conversation_id: int,
    user_id: int
) -> bool:
    """Delete conversation"""
    conversation = await get_conversation(db, conversation_id, user_id)
    if not conversation:
        return False

    await db.delete(conversation)
    await db.commit()
    return True


async def add_message(
    db: AsyncSession,
    conversation_id: int,
    role: str,
    content: str,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    total_tokens: int | None = None
) -> ChatMessage:
    """Add message to conversation"""
    message = ChatMessage(
        conversation_id=conversation_id,
        role=role,
        content=content,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        created_at=datetime.now(timezone.utc)
    )

    db.add(message)

    # Update conversation stats
    conversation = await db.get(ChatConversation, conversation_id)
    if conversation:
        conversation.message_count += 1
        if total_tokens:
            conversation.total_tokens += total_tokens
        conversation.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(message)
    return message


async def get_conversation_messages(
    db: AsyncSession,
    conversation_id: int,
    user_id: int,
    limit: int = 100
) -> list[ChatMessage]:
    """Get messages from conversation"""
    # First check if conversation belongs to user
    conversation = await get_conversation(db, conversation_id, user_id)
    if not conversation:
        return []

    query = (
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at)
        .limit(limit)
    )

    result = await db.execute(query)
    return list(result.scalars().all())


async def auto_generate_title(
    db: AsyncSession,
    conversation: ChatConversation,
    first_message: str
) -> None:
    """Auto-generate conversation title from first message"""
    if not conversation.title and first_message:
        # Take first 50 characters of the message as title
        title = first_message[:50]
        if len(first_message) > 50:
            title += "..."

        conversation.title = title
        conversation.updated_at = datetime.now(timezone.utc)
        await db.commit()
