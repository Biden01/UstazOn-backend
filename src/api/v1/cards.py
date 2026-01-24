from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_db
from src.models.user import User
from src.schemas.card import (
    CardCreate,
    CardUpdate,
    CardResponse,
    CardListItem,
    CardDetailResponse,
    CardTopicCreate,
    CardTopicUpdate,
    CardTopicResponse,
)
from src.services import card_service

router = APIRouter()


# CardTopic endpoints
@router.get("/topics/", response_model=list[CardTopicResponse])
async def get_card_topics(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db: AsyncSession = Depends(get_db),
):
    """Get root card topics with their children hierarchy"""
    return await card_service.get_card_topics(db, skip=skip, limit=limit)


@router.post("/topics/", response_model=CardTopicResponse, status_code=status.HTTP_201_CREATED)
async def create_card_topic(
    topic_data: CardTopicCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create new card topic (authenticated users only)"""
    # Check if topic already exists
    existing = await card_service.get_card_topic_by_name(db, topic_data.topic)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Topic with this name already exists",
        )
    return await card_service.create_card_topic(db, topic_data)


@router.get("/topics/{topic_id}", response_model=CardTopicResponse)
async def get_card_topic(
    topic_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get card topic by ID"""
    topic = await card_service.get_card_topic_by_id(db, topic_id)
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found"
        )
    return topic


@router.put("/topics/{topic_id}", response_model=CardTopicResponse)
async def update_card_topic(
    topic_id: int,
    topic_data: CardTopicUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update card topic (authenticated users only)"""
    topic = await card_service.update_card_topic(db, topic_id, topic_data)
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found"
        )
    return topic


@router.delete("/topics/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_card_topic(
    topic_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete card topic (authenticated users only)"""
    success = await card_service.delete_card_topic(db, topic_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found"
        )


# Card endpoints
@router.get("/", response_model=list[CardListItem])
async def get_cards(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    grade: int | None = Query(None, ge=1, le=11),
    quarter: int | None = Query(None, ge=1, le=4),
    subject_id: int | None = None,
    institution_type_id: int | None = None,
    topic_id: int | None = None,
    window_id: int | None = None,
    author_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get cards with optional filters"""
    return await card_service.get_cards(
        db,
        skip=skip,
        limit=limit,
        grade=grade,
        quarter=quarter,
        subject_id=subject_id,
        institution_type_id=institution_type_id,
        topic_id=topic_id,
        window_id=window_id,
        author_id=author_id,
    )


@router.post("/", response_model=CardDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_card(
    card_data: CardCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create new card (authenticated users only)"""
    return await card_service.create_card(db, card_data, current_user.id)


@router.get("/{card_id}", response_model=CardDetailResponse)
async def get_card(
    card_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get card by ID with full details"""
    card = await card_service.get_card_by_id(db, card_id)
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Card not found"
        )
    return card


@router.put("/{card_id}", response_model=CardDetailResponse)
async def update_card(
    card_id: int,
    card_data: CardUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update card (only by author)"""
    # Check if card exists and user is the author
    existing_card = await card_service.get_card_by_id(db, card_id)
    if not existing_card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Card not found"
        )
    if existing_card.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own cards",
        )

    card = await card_service.update_card(db, card_id, card_data)
    return card


@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_card(
    card_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete card (only by author)"""
    # Check if card exists and user is the author
    existing_card = await card_service.get_card_by_id(db, card_id)
    if not existing_card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Card not found"
        )
    if existing_card.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own cards",
        )

    await card_service.delete_card(db, card_id)


@router.post("/{card_id}/favorite", response_model=CardDetailResponse)
async def toggle_favorite(
    card_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add or remove card from favorites"""
    card = await card_service.toggle_favorite(db, card_id, current_user.id)
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Card not found"
        )
    return card


@router.get("/favorites/me", response_model=list[CardListItem])
async def get_my_favorites(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's favorite cards"""
    return await card_service.get_user_favorites(db, current_user.id, skip=skip, limit=limit)


# Autocomplete / Suggestions endpoints
@router.get("/suggestions/topics")
async def get_topic_suggestions(
    q: str = Query("", description="Search query"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get topic suggestions for autocomplete"""
    suggestions = await card_service.get_topic_suggestions(db, q, limit=limit)
    return {"suggestions": suggestions}


@router.get("/suggestions/names")
async def get_name_suggestions(
    q: str = Query("", description="Search query"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get card name suggestions for autocomplete"""
    suggestions = await card_service.get_name_suggestions(db, q, limit=limit)
    return {"suggestions": suggestions}


@router.get("/suggestions/descriptions")
async def get_description_suggestions(
    q: str = Query("", description="Search query"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get card description suggestions for autocomplete"""
    suggestions = await card_service.get_description_suggestions(db, q, limit=limit)
    return {"suggestions": suggestions}


@router.get("/suggestions/search")
async def search_suggestions(
    q: str = Query("", description="Search query"),
    limit: int = Query(15, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    Smart search suggestions across multiple fields.
    
    Returns suggestions from:
    - Card names (priority 1)
    - Topics (priority 2)
    - Subjects (priority 3)
    - Authors (priority 4)
    - Descriptions (priority 5)
    
    Supports author search with prefix: "автор: name" or "author: name"
    """
    suggestions = await card_service.search_suggestions(db, q, limit=limit)
    return {"suggestions": suggestions}

