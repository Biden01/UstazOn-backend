"""
AI Chat endpoints
"""
import logging
import json
import re

from fastapi import APIRouter, HTTPException, status, Depends, Form, File, UploadFile
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.ai import (
    ChatRequest, ChatResponse, UsageInfo, PromptTemplate, PromptCategory,
    ConversationCreate, ConversationUpdate, ConversationResponse,
    ConversationListItem, SendMessageRequest, SendMessageResponse, MessageResponse
)
from src.services.ai_service import ai_service
from src.services.pdf_service import pdf_service
from src.services.presentation_service import PresentationService
from src.services.teaching_materials_service import teaching_materials_service
from src.prompts.teacher_prompts import (
    get_all_prompts_grouped,
    get_quick_prompt,
    get_system_prompt,
    SUBJECT_SPECIFIC_PROMPTS,
    PROMPT_CATEGORIES
)
from src.crud import conversation as crud_conversation
from src.db.session import get_db
from src.api.deps import get_current_user
from src.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


def parse_material_request(text: str, request_type: str) -> dict | None:
    """
    Parse material generation request from AI response

    Args:
        text: AI response text
        request_type: Type of request (PRESENTATION_REQUEST, LESSON_PLAN_REQUEST, TEST_REQUEST, HOMEWORK_REQUEST, RUBRIC_REQUEST)

    Returns:
        dict with material parameters if found, None otherwise
    """
    pattern = rf'{request_type}:\s*(\{{[^}}]+\}})'
    match = re.search(pattern, text)

    if match:
        try:
            json_str = match.group(1)
            data = json.loads(json_str)
            data['json_match'] = match.group(0)  # To remove from text later
            data['request_type'] = request_type
            return data
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse {request_type} JSON: {match.group(1)}")

    return None


def parse_presentation_request(text: str) -> dict | None:
    """Parse PRESENTATION_REQUEST from AI response"""
    result = parse_material_request(text, 'PRESENTATION_REQUEST')
    if result and all(k in result for k in ['subject', 'grade', 'topic']):
        return result
    return None


def parse_lesson_plan_request(text: str) -> dict | None:
    """Parse LESSON_PLAN_REQUEST from AI response"""
    result = parse_material_request(text, 'LESSON_PLAN_REQUEST')
    if result and all(k in result for k in ['subject', 'grade', 'topic']):
        return result
    return None


def parse_test_request(text: str) -> dict | None:
    """Parse TEST_REQUEST from AI response"""
    result = parse_material_request(text, 'TEST_REQUEST')
    if result and all(k in result for k in ['subject', 'grade', 'topic']):
        return result
    return None


def parse_homework_request(text: str) -> dict | None:
    """Parse HOMEWORK_REQUEST from AI response"""
    result = parse_material_request(text, 'HOMEWORK_REQUEST')
    if result and all(k in result for k in ['subject', 'grade', 'topic']):
        return result
    return None


def parse_rubric_request(text: str) -> dict | None:
    """Parse RUBRIC_REQUEST from AI response"""
    result = parse_material_request(text, 'RUBRIC_REQUEST')
    if result and all(k in result for k in ['subject', 'grade', 'work_type']):
        return result
    return None


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to AI chatbot and get a response

    - **message**: User's message (required, 1-4000 characters)
    - **history**: Optional chat history for context
    - **system_instruction**: Optional instruction to guide AI behavior
    """
    try:
        # Convert history format if provided
        history = None
        if request.history:
            history = [
                {"role": msg.role, "content": msg.content} for msg in request.history
            ]

        # Use teacher system prompt if no custom instruction provided
        system_instruction = request.system_instruction
        if not system_instruction:
            system_instruction = get_system_prompt()

        # Get response from AI service
        result = await ai_service.chat(
            message=request.message,
            history=history,
            system_instruction=system_instruction,
        )

        return ChatResponse(
            message=result["text"],
            usage=UsageInfo(**result["usage"]),
        )

    except ValueError as e:
        logger.error(f"AI service error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not available. Please contact administrator.",
        )
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request.",
        )


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Stream AI chat response in real-time

    - **message**: User's message (required, 1-4000 characters)
    - **history**: Optional chat history for context
    - **system_instruction**: Optional instruction to guide AI behavior

    Returns a streaming response with chunks of text
    """
    try:
        # Convert history format if provided
        history = None
        if request.history:
            history = [
                {"role": msg.role, "content": msg.content} for msg in request.history
            ]

        # Use teacher system prompt if no custom instruction provided
        system_instruction = request.system_instruction
        if not system_instruction:
            system_instruction = get_system_prompt()

        async def generate():
            try:
                async for chunk in ai_service.chat_stream(
                    message=request.message,
                    history=history,
                    system_instruction=system_instruction,
                ):
                    yield chunk
            except Exception as e:
                logger.error(f"Error in stream: {e}")
                yield f"Error: {str(e)}"

        return StreamingResponse(generate(), media_type="text/plain")

    except ValueError as e:
        logger.error(f"AI service error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not available. Please contact administrator.",
        )
    except Exception as e:
        logger.error(f"Unexpected error in chat stream endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request.",
        )


@router.get("/prompts", response_model=dict)
async def get_prompts():
    """
    Получить все доступные шаблоны промптов для учителей, сгруппированные по категориям

    Returns:
        Словарь с категориями и промптами
    """
    try:
        return get_all_prompts_grouped()
    except Exception as e:
        logger.error(f"Error getting prompts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve prompts",
        )


@router.get("/prompts/{prompt_key}", response_model=PromptTemplate)
async def get_prompt(prompt_key: str):
    """
    Получить конкретный шаблон промпта по ключу

    - **prompt_key**: Ключ промпта (lesson_plan, create_test, etc.)
    """
    try:
        prompt = get_quick_prompt(prompt_key)
        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt with key '{prompt_key}' not found",
            )
        return {"key": prompt_key, **prompt}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prompt {prompt_key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve prompt",
        )


@router.get("/system-prompt")
async def get_teacher_system_prompt(subject: str | None = None):
    """
    Получить системный промпт для учителя

    - **subject**: Опциональный код предмета (math, physics, etc.)

    Returns:
        Системный промпт с учетом предмета
    """
    try:
        return {
            "system_prompt": get_system_prompt(subject),
            "subject": subject
        }
    except Exception as e:
        logger.error(f"Error getting system prompt: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system prompt",
        )


@router.get("/subjects")
async def get_ai_subjects():
    """
    Получить список предметов с AI поддержкой

    Returns:
        Список доступных предметов для специализированных промптов
    """
    try:
        subjects = [
            {
                "code": code,
                "name_ru": data["name_ru"],
                "name_kk": data["name_kk"]
            }
            for code, data in SUBJECT_SPECIFIC_PROMPTS.items()
        ]
        return {"subjects": subjects}
    except Exception as e:
        logger.error(f"Error getting subjects: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subjects",
        )


@router.get("/categories")
async def get_prompt_categories():
    """
    Получить список категорий промптов

    Returns:
        Список категорий
    """
    try:
        categories = [
            {"key": key, "name": name}
            for key, name in PROMPT_CATEGORIES.items()
        ]
        return {"categories": categories}
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve categories",
        )


# Conversation management endpoints
@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    data: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Создать новую беседу"""
    try:
        conversation = await crud_conversation.create_conversation(
            db, current_user.id, data
        )
        return ConversationResponse(
            id=conversation.id,
            user_id=conversation.user_id,
            title=conversation.title,
            subject=conversation.subject,
            message_count=conversation.message_count,
            total_tokens=conversation.total_tokens,
            created_at=conversation.created_at.isoformat(),
            updated_at=conversation.updated_at.isoformat(),
            messages=[]
        )
    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create conversation"
        )


@router.get("/conversations", response_model=list[ConversationListItem])
async def get_conversations(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить список всех бесед пользователя"""
    try:
        conversations = await crud_conversation.get_user_conversations(
            db, current_user.id, skip, limit
        )
        return [
            ConversationListItem(
                id=c.id,
                title=c.title,
                subject=c.subject,
                message_count=c.message_count,
                total_tokens=c.total_tokens,
                created_at=c.created_at.isoformat(),
                updated_at=c.updated_at.isoformat()
            )
            for c in conversations
        ]
    except Exception as e:
        logger.error(f"Error getting conversations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversations"
        )


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить конкретную беседу с историей сообщений"""
    try:
        conversation = await crud_conversation.get_conversation(
            db, conversation_id, current_user.id, load_messages=True
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        return ConversationResponse(
            id=conversation.id,
            user_id=conversation.user_id,
            title=conversation.title,
            subject=conversation.subject,
            message_count=conversation.message_count,
            total_tokens=conversation.total_tokens,
            created_at=conversation.created_at.isoformat(),
            updated_at=conversation.updated_at.isoformat(),
            messages=[
                MessageResponse(
                    id=m.id,
                    role=m.role,
                    content=m.content,
                    input_tokens=m.input_tokens,
                    output_tokens=m.output_tokens,
                    total_tokens=m.total_tokens,
                    created_at=m.created_at.isoformat()
                )
                for m in conversation.messages
            ]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversation"
        )


@router.put("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    data: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Обновить беседу (название, предмет)"""
    try:
        conversation = await crud_conversation.update_conversation(
            db, conversation_id, current_user.id, data
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        return ConversationResponse(
            id=conversation.id,
            user_id=conversation.user_id,
            title=conversation.title,
            subject=conversation.subject,
            message_count=conversation.message_count,
            total_tokens=conversation.total_tokens,
            created_at=conversation.created_at.isoformat(),
            updated_at=conversation.updated_at.isoformat(),
            messages=[]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update conversation"
        )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удалить беседу"""
    try:
        success = await crud_conversation.delete_conversation(
            db, conversation_id, current_user.id
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete conversation"
        )


@router.post("/messages", response_model=SendMessageResponse)
async def send_message(
    message: str = Form(...),
    conversation_id: int | None = Form(None),
    subject: str | None = Form(None),
    save_to_history: bool = Form(True),
    model: str = Form("gemini-2.5-flash"),
    files: list[UploadFile] | None = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Отправить сообщение в беседу и получить ответ AI

    Поддерживает текст и изображения (JPEG, PNG, WebP)
    """
    try:
        # Read uploaded images and documents
        images = []
        document_texts = []

        if files:
            for file in files:
                # Read file bytes
                content = await file.read()

                # Check if it's an image
                if file.content_type and file.content_type.startswith('image/'):
                    images.append(content)

                # Check if it's a PDF
                elif file.content_type == 'application/pdf':
                    try:
                        from PyPDF2 import PdfReader
                        from io import BytesIO
                        pdf_reader = PdfReader(BytesIO(content))
                        text = ""
                        for page in pdf_reader.pages:
                            text += page.extract_text() + "\n"
                        if text.strip():
                            document_texts.append(f"PDF Document ({file.filename}):\n{text}")
                    except Exception as e:
                        logger.error(f"Error reading PDF {file.filename}: {e}")

                # Check if it's a DOCX
                elif file.content_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                    try:
                        from docx import Document
                        from io import BytesIO
                        doc = Document(BytesIO(content))
                        text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
                        if text.strip():
                            document_texts.append(f"Word Document ({file.filename}):\n{text}")
                    except Exception as e:
                        logger.error(f"Error reading DOCX {file.filename}: {e}")

        # Combine message with document texts
        full_message = message
        if document_texts:
            full_message = message + "\n\n" + "\n\n".join(document_texts)

        # Create or get conversation
        conversation = None
        history = None

        if save_to_history:
            if conversation_id:
                conversation = await crud_conversation.get_conversation(
                    db, conversation_id, current_user.id, load_messages=True
                )
                # If found, build history
                if conversation and conversation.messages:
                    history = [
                        {"role": msg.role, "parts": [{"text": msg.content}]}
                        for msg in conversation.messages
                    ]

            if not conversation:
                # Create new conversation
                from src.schemas.ai import ConversationCreate
                conversation = await crud_conversation.create_conversation(
                    db,
                    current_user.id,
                    ConversationCreate(title=None, subject=subject)
                )
                conversation_id = conversation.id
                # History is empty for new conversation, do not access conversation.messages

        # Get system prompt based on subject
        system_instruction = get_system_prompt(subject)

        # Get AI response with images and document text
        result = await ai_service.chat(
            message=full_message,
            history=history,
            system_instruction=system_instruction,
            images=images if images else None,
            model=model
        )

        # Check if AI response contains any material generation request
        ai_text = result["text"]

        # Try to parse different types of requests
        presentation_params = parse_presentation_request(ai_text)
        lesson_plan_params = parse_lesson_plan_request(ai_text)
        test_params = parse_test_request(ai_text)
        homework_params = parse_homework_request(ai_text)
        rubric_params = parse_rubric_request(ai_text)

        # Determine which material generation request was found and create appropriate link
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        clean_text = ai_text
        material_link = None

        if presentation_params:
            clean_text = ai_text.replace(presentation_params['json_match'], '').strip()
            material_link = f"[PRESENTATION_LINK:{presentation_params['subject']}|{presentation_params['grade']}|{presentation_params['topic']}|{presentation_params.get('slides_count', 12)}]"

        elif lesson_plan_params:
            clean_text = ai_text.replace(lesson_plan_params['json_match'], '').strip()
            material_link = f"[LESSON_PLAN_LINK:{lesson_plan_params['subject']}|{lesson_plan_params['grade']}|{lesson_plan_params['topic']}|{lesson_plan_params.get('duration', 45)}]"

        elif test_params:
            clean_text = ai_text.replace(test_params['json_match'], '').strip()
            difficulty = test_params.get('difficulty', 'medium')
            question_count = test_params.get('question_count', 15)
            material_link = f"[TEST_LINK:{test_params['subject']}|{test_params['grade']}|{test_params['topic']}|{question_count}|{difficulty}]"

        elif homework_params:
            clean_text = ai_text.replace(homework_params['json_match'], '').strip()
            duration = homework_params.get('duration', 30)
            difficulty = homework_params.get('difficulty', 'medium')
            material_link = f"[HOMEWORK_LINK:{homework_params['subject']}|{homework_params['grade']}|{homework_params['topic']}|{duration}|{difficulty}]"

        elif rubric_params:
            clean_text = ai_text.replace(rubric_params['json_match'], '').strip()
            work_type = rubric_params['work_type']
            description = rubric_params.get('description', '')
            material_link = f"[RUBRIC_LINK:{rubric_params['subject']}|{rubric_params['grade']}|{work_type}|{description}]"

        # Add material link to content if found
        final_content = clean_text + (f"\n\n{material_link}" if material_link else "")

        # Save messages to database if requested
        user_msg_db = None
        assistant_msg_db = None

        if save_to_history and conversation_id:
            # Save user message
            user_msg_db = await crud_conversation.add_message(
                db,
                conversation_id=conversation_id,
                role="user",
                content=message
            )

            # Save assistant message
            assistant_msg_db = await crud_conversation.add_message(
                db,
                conversation_id=conversation_id,
                role="model",
                content=final_content,
                input_tokens=result["usage"]["input_tokens"],
                output_tokens=result["usage"]["output_tokens"],
                total_tokens=result["usage"]["total_tokens"]
            )

            # Auto-generate title if this is the first exchange
            if conversation and not conversation.title:
                # Use first 50 chars of user message as title
                title = message[:50] + ("..." if len(message) > 50 else "")
                from src.schemas.ai import ConversationUpdate
                await crud_conversation.update_conversation(
                    db,
                    conversation_id,
                    current_user.id,
                    ConversationUpdate(title=title)
                )

        # Create response messages
        user_message_response = MessageResponse(
            id=user_msg_db.id if user_msg_db else 0,
            role="user",
            content=message,
            created_at=user_msg_db.created_at.isoformat() if user_msg_db else now
        )

        assistant_message = MessageResponse(
            id=assistant_msg_db.id if assistant_msg_db else 0,
            role="model",
            content=final_content,
            input_tokens=result["usage"]["input_tokens"],
            output_tokens=result["usage"]["output_tokens"],
            total_tokens=result["usage"]["total_tokens"],
            created_at=assistant_msg_db.created_at.isoformat() if assistant_msg_db else now
        )

        return SendMessageResponse(
            conversation_id=conversation_id or 0,
            user_message=user_message_response,
            assistant_message=assistant_message
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message"
        )


@router.post("/generate-pdf")
async def generate_pdf(
    content: str = Form(...),
    title: str = Form("Документ"),
    document_type: str = Form("lesson_plan"),
    current_user: User = Depends(get_current_user)
):
    """
    Генерация PDF документа из текста AI

    Типы документов:
    - lesson_plan: План урока
    - test: Тест
    - ktp: КТП
    - homework: Домашнее задание
    """
    try:
        # Generate PDF based on document type
        if document_type == "test":
            pdf_output = pdf_service.generate_test(content, title)
        elif document_type == "ktp":
            pdf_output = pdf_service.generate_ktp(content, title)
        elif document_type == "homework":
            pdf_output = pdf_service.generate_homework(content, title)
        else:
            pdf_output = pdf_service.generate_lesson_plan(content, title)

        # Return PDF as downloadable file
        from fastapi.responses import Response
        return Response(
            content=pdf_output.getvalue(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{title}.pdf"'
            }
        )

    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate PDF"
        )


@router.get("/models")
async def get_available_models(current_user: User = Depends(get_current_user)):
    """
    Get list of available AI models for presentation generation

    Returns:
        List of available models with metadata
    """
    models = ai_service.get_available_models()
    return {"models": models}


@router.post("/generate-presentation-outline")
async def generate_presentation_outline(
    subject: str = Form(...),
    grade: str = Form(...),
    topic: str = Form(...),
    slides_count: int = Form(12),
    model: str = Form("gemini-2.5-flash"),
    current_user: User = Depends(get_current_user)
):
    """
    Generate outline for presentation
    Returns JSON structure of the presentation
    """
    try:
        from src.prompts.teacher_prompts import QUICK_PROMPTS
        import json
        import re

        # Get presentation generation prompt
        presentation_prompt = QUICK_PROMPTS["presentation"]["prompt"]

        # Create user message
        user_message = f"""Предмет: {subject}
Класс: {grade}
Тема урока: {topic}
Количество слайдов: {slides_count}

{presentation_prompt}"""

        # Generate structure using AI
        result = await ai_service.chat(
            message=user_message,
            history=None,
            system_instruction="Ты - эксперт по созданию образовательных презентаций. Верни ТОЛЬКО валидный JSON без дополнительного текста.",
            model=model
        )

        # Extract JSON
        ai_response = result["text"].strip()
        ai_response = re.sub(r'```json\s*', '', ai_response)
        ai_response = re.sub(r'```\s*$', '', ai_response)
        ai_response = ai_response.strip()

        # Parse JSON to validate
        try:
            presentation_data = json.loads(ai_response)
        except json.JSONDecodeError:
            json_match = re.search(r'\{[\s\S]*\}', ai_response)
            if json_match:
                presentation_data = json.loads(json_match.group())
            else:
                raise ValueError("Failed to parse JSON from AI response")

        return presentation_data

    except Exception as e:
        logger.error(f"Error generating outline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate outline: {str(e)}"
        )


@router.post("/generate-presentation")
async def generate_presentation(
    subject: str = Form(...),
    grade: str = Form(...),
    topic: str = Form(...),
    slides_count: int = Form(12),
    outline: str | None = Form(None),
    model: str = Form("gemini-2.5-flash"),
    current_user: User = Depends(get_current_user)
):
    """
    Генерация презентации PowerPoint для урока
    
    If outline is provided (as JSON string), it uses it directly.
    Otherwise manages full generation cycle.
    """
    try:
        import json
        import urllib.parse
        from fastapi.responses import Response
        from src.services.presentation_service import presentation_service

        presentation_data = None

        if outline:
            # Use provided outline
            try:
                presentation_data = json.loads(outline)
            except json.JSONDecodeError:
                raise ValueError("Invalid outline JSON provided")
        else:
            # Fallback to full generation (Legacy support)
            # Call generate_presentation_outline logic inline or reuse code
            # For simplicity, we'll just error or duplicate for now, but 
            # ideally better to reuse. Let's redirect to outline logic.
             # Get presentation generation prompt
            from src.prompts.teacher_prompts import QUICK_PROMPTS
            import re
            
            presentation_prompt = QUICK_PROMPTS["presentation"]["prompt"]

            user_message = f"""Предмет: {subject}
Класс: {grade}
Тема урока: {topic}
Количество слайдов: {slides_count}

{presentation_prompt}"""

            result = await ai_service.chat(
                message=user_message,
                history=None,
                system_instruction="Ты - эксперт по созданию образовательных презентаций. Верни ТОЛЬКО валидный JSON без дополнительного текста.",
                model=model
            )

            ai_response = result["text"].strip()
            ai_response = re.sub(r'```json\s*', '', ai_response)
            ai_response = re.sub(r'```\s*$', '', ai_response)
            ai_response = ai_response.strip()

            try:
                presentation_data = json.loads(ai_response)
            except json.JSONDecodeError:
                json_match = re.search(r'\{[\s\S]*\}', ai_response)
                if json_match:
                    presentation_data = json.loads(json_match.group())
                else:
                    raise ValueError("Failed to parse JSON from AI response")

        # Generate PowerPoint presentation from data
        pptx_output = presentation_service.create_presentation(presentation_data)

        # Return PPTX as downloadable file
        safe_filename = f"{topic.replace(' ', '_')}_{grade.replace(' ', '_')}.pptx"
        encoded_filename = urllib.parse.quote(safe_filename)

        return Response(
            content=pptx_output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )
    except Exception as e:
        logger.error(f"Error generating presentation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate presentation: {str(e)}"
        )


@router.post("/generate-lesson-plan")
async def generate_lesson_plan(
    subject: str = Form(...),
    grade: str = Form(...),
    topic: str = Form(...),
    duration: int = Form(45),
    model: str = Form("gemini-2.5-flash"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Генерация плана урока в формате DOCX

    Args:
        subject: Предмет
        grade: Класс
        topic: Тема урока
        duration: Длительность урока в минутах
        model: AI модель

    Returns:
        DOCX файл с планом урока
    """
    try:
        from fastapi.responses import StreamingResponse
        from src.models.teaching_materials import MaterialType

        # Generate lesson plan using service
        lesson_plan_data = await teaching_materials_service.generate_lesson_plan(
            subject=subject,
            grade=grade,
            topic=topic,
            duration=duration,
            model=model,
            db=db,
            user_id=current_user.id
        )

        # Export to DOCX
        docx_output = teaching_materials_service.export_to_docx(lesson_plan_data, MaterialType.LESSON_PLAN)

        # Create filename
        filename = f"План_урока_{topic.replace(' ', '_')}_{grade.replace(' ', '_')}.docx"

        return StreamingResponse(
            docx_output,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating lesson plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate lesson plan: {str(e)}"
        )


@router.post("/generate-test")
async def generate_test(
    subject: str = Form(...),
    grade: str = Form(...),
    topic: str = Form(...),
    question_count: int = Form(15),
    difficulty: str = Form("medium"),
    model: str = Form("gemini-2.5-flash"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Генерация теста/СОР в формате DOCX

    Args:
        subject: Предмет
        grade: Класс
        topic: Тема
        question_count: Количество вопросов
        difficulty: Уровень сложности (easy/medium/hard/mixed)
        model: AI модель

    Returns:
        DOCX файл с тестом
    """
    try:
        from fastapi.responses import StreamingResponse
        from src.models.teaching_materials import MaterialType

        # Generate test using service
        test_data = await teaching_materials_service.generate_test(
            subject=subject,
            grade=grade,
            topic=topic,
            question_count=question_count,
            difficulty=difficulty,
            model=model,
            db=db,
            user_id=current_user.id
        )

        # Export to DOCX
        docx_output = teaching_materials_service.export_to_docx(test_data, MaterialType.TEST)

        # Create filename
        filename = f"Тест_{topic.replace(' ', '_')}_{grade.replace(' ', '_')}.docx"

        return StreamingResponse(
            docx_output,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating test: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate test: {str(e)}"
        )


@router.post("/generate-homework")
async def generate_homework(
    subject: str = Form(...),
    grade: str = Form(...),
    topic: str = Form(...),
    duration: int = Form(30),
    difficulty: str = Form("medium"),
    model: str = Form("gemini-2.5-flash"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Генерация домашнего задания в формате DOCX

    Args:
        subject: Предмет
        grade: Класс
        topic: Тема
        duration: Время на выполнение (минуты)
        difficulty: Уровень сложности
        model: AI модель

    Returns:
        DOCX файл с домашним заданием
    """
    try:
        from fastapi.responses import StreamingResponse
        from src.models.teaching_materials import MaterialType

        # Generate homework using service
        homework_data = await teaching_materials_service.generate_homework(
            subject=subject,
            grade=grade,
            topic=topic,
            duration=duration,
            difficulty=difficulty,
            model=model,
            db=db,
            user_id=current_user.id
        )

        # Export to DOCX
        docx_output = teaching_materials_service.export_to_docx(homework_data, MaterialType.HOMEWORK)

        # Create filename
        filename = f"ДЗ_{topic.replace(' ', '_')}_{grade.replace(' ', '_')}.docx"

        return StreamingResponse(
            docx_output,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating homework: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate homework: {str(e)}"
        )


@router.post("/generate-rubric")
async def generate_rubric(
    subject: str = Form(...),
    grade: str = Form(...),
    work_type: str = Form(...),
    description: str = Form(...),
    model: str = Form("gemini-2.5-flash"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Генерация критериев оценивания (рубрики) в формате DOCX

    Args:
        subject: Предмет
        grade: Класс
        work_type: Тип работы (тест/проект/презентация/эссе)
        description: Описание работы
        model: AI модель

    Returns:
        DOCX файл с критериями оценивания
    """
    try:
        from fastapi.responses import StreamingResponse
        from src.models.teaching_materials import MaterialType

        # Generate rubric using service
        rubric_data = await teaching_materials_service.generate_rubric(
            subject=subject,
            grade=grade,
            work_type=work_type,
            description=description,
            model=model,
            db=db,
            user_id=current_user.id
        )

        # Export to DOCX
        docx_output = teaching_materials_service.export_to_docx(rubric_data, MaterialType.RUBRIC)

        # Create filename
        filename = f"Рубрика_{work_type.replace(' ', '_')}_{grade.replace(' ', '_')}.docx"

        return StreamingResponse(
            docx_output,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating rubric: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate rubric: {str(e)}"
        )


@router.post("/generate-manim")
async def generate_manim_code(
    topic: str = Form(...),
    detail_level: str = Form("medium"),
    model: str = Form("gemini-2.5-flash"),
    current_user: User = Depends(get_current_user)
):
    """
    Generate Manim video for mathematical visualization
    """
    try:
        from src.prompts.teacher_prompts import QUICK_PROMPTS
        import json
        import re
        from fastapi.responses import FileResponse
        from src.services.manim_service import manim_service

        prompt_template = QUICK_PROMPTS["manim"]["prompt"]
        
        user_message = f"""Topic to visualize: {topic}
Level of Detail: {detail_level}

{prompt_template}"""

        # Generate code using AI
        result = await ai_service.chat(
            message=user_message,
            history=None,
            system_instruction="You are a Python expert specializing in Manim library.",
            model=model
        )

        ai_response = result["text"].strip()
        
        # Clean up response to get JSON
        ai_response = re.sub(r'```json\s*', '', ai_response)
        ai_response = re.sub(r'```\s*$', '', ai_response)
        ai_response = ai_response.strip()

        code = ""
        try:
            data = json.loads(ai_response)
            code = data.get("code", "")
        except json.JSONDecodeError:
             # Fallback: try to extract code block if JSON fails
            code_match = re.search(r'```python(.*?)```', result["text"], re.DOTALL)
            if code_match:
                code = code_match.group(1).strip()
            else:
                raise ValueError("Failed to parse AI response code")
        
        if not code:
            logger.error(f"Failed to extract code. Raw AI response: {result['text']}")
            raise ValueError("AI did not generate any code")

        logger.info(f"Generated Manim Code: {code[:200]}...")  # Log start of code


        # Generate Video
        video_path = manim_service.generate_video(code)
        
        filename = f"manim_{topic.replace(' ', '_')[:20]}.mp4"
        
        return FileResponse(
            path=video_path,
            filename=filename,
            media_type="video/mp4"
        )

    except Exception as e:
        logger.error(f"Error generating Manim video: {e}")
        # Return error as JSON even on failure so frontend handles it
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate video: {str(e)}"
        )
