"""
Schemas for AI chat functionality
"""
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Single chat message"""

    role: str = Field(..., description="Message role: 'user' or 'model'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request for AI chat"""

    message: str = Field(..., min_length=1, max_length=4000, description="User message")
    history: list[ChatMessage] | None = Field(
        None, description="Optional chat history"
    )
    system_instruction: str | None = Field(
        None, max_length=1000, description="Optional system instruction"
    )


class UsageInfo(BaseModel):
    """Token usage information"""

    input_tokens: int
    output_tokens: int
    total_tokens: int


class ChatResponse(BaseModel):
    """Response from AI chat"""

    message: str = Field(..., description="AI response message")
    usage: UsageInfo = Field(..., description="Token usage information")


class PromptTemplate(BaseModel):
    """Template for quick prompts"""

    key: str = Field(..., description="Unique prompt key")
    name_ru: str = Field(..., description="Russian name")
    name_kk: str = Field(..., description="Kazakh name")
    prompt: str = Field(..., description="Prompt text")
    category: str = Field(..., description="Category key")


class PromptCategory(BaseModel):
    """Category of prompts"""

    key: str = Field(..., description="Category key")
    name: str = Field(..., description="Category name")


class SubjectInfo(BaseModel):
    """Subject information for AI"""

    code: str = Field(..., description="Subject code")
    name_ru: str = Field(..., description="Russian name")
    name_kk: str = Field(..., description="Kazakh name")


# Conversation schemas
class ConversationCreate(BaseModel):
    """Create new conversation"""

    title: str | None = Field(None, max_length=200, description="Conversation title")
    subject: str | None = Field(None, max_length=50, description="Subject code")


class ConversationUpdate(BaseModel):
    """Update conversation"""

    title: str | None = Field(None, max_length=200, description="New title")
    subject: str | None = Field(None, max_length=50, description="Subject code")


class MessageResponse(BaseModel):
    """Single message in conversation"""

    id: int
    role: str
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    created_at: str

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    """Conversation response"""

    id: int
    user_id: int
    title: str | None
    subject: str | None
    message_count: int
    total_tokens: int
    created_at: str
    updated_at: str
    messages: list[MessageResponse] = []

    class Config:
        from_attributes = True


class ConversationListItem(BaseModel):
    """Conversation list item (without messages)"""

    id: int
    title: str | None
    subject: str | None
    message_count: int
    total_tokens: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class SendMessageRequest(BaseModel):
    """Send message to conversation"""

    conversation_id: int | None = Field(None, description="Conversation ID (creates new if null)")
    message: str = Field(..., min_length=1, max_length=4000, description="User message")
    subject: str | None = Field(None, max_length=50, description="Subject for system prompt")
    save_to_history: bool = Field(True, description="Save messages to database")


class SendMessageResponse(BaseModel):
    """Response from sending message"""

    conversation_id: int
    user_message: MessageResponse
    assistant_message: MessageResponse
