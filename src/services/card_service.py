from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.card import Card, CardTopic
from src.models.subject import Subject, InstitutionType, Window
from src.schemas.card import CardCreate, CardUpdate, CardTopicCreate, CardTopicUpdate


# CardTopic CRUD
async def get_card_topics(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[dict]:
    """Get root card topics with their children hierarchy"""
    # First, get all topics
    result = await db.execute(select(CardTopic))
    all_topics = list(result.scalars().all())

    # Convert to dict to avoid SQLAlchemy relationship loading
    topics_dict = {}
    for topic in all_topics:
        topics_dict[topic.id] = {
            'id': topic.id,
            'topic': topic.topic,
            'parent_topic_id': topic.parent_topic_id,
            'created_at': topic.created_at,
            'children': []
        }

    # Build hierarchy
    for topic_id, topic_data in topics_dict.items():
        parent_id = topic_data['parent_topic_id']
        if parent_id and parent_id in topics_dict:
            topics_dict[parent_id]['children'].append(topic_data)

    # Get root topics and apply pagination
    root_topics = [t for t in topics_dict.values() if t['parent_topic_id'] is None]
    return root_topics[skip:skip+limit]


async def get_card_topic_by_id(db: AsyncSession, topic_id: int) -> CardTopic | None:
    """Get card topic by ID"""
    result = await db.execute(select(CardTopic).where(CardTopic.id == topic_id))
    return result.scalar_one_or_none()


async def get_card_topic_by_name(db: AsyncSession, topic: str) -> CardTopic | None:
    """Get card topic by name"""
    result = await db.execute(select(CardTopic).where(CardTopic.topic == topic))
    return result.scalar_one_or_none()


async def create_card_topic(
    db: AsyncSession, topic_data: CardTopicCreate
) -> CardTopic:
    """Create new card topic"""
    topic = CardTopic(**topic_data.model_dump())
    db.add(topic)
    await db.commit()
    await db.refresh(topic)
    return topic


async def update_card_topic(
    db: AsyncSession, topic_id: int, topic_data: CardTopicUpdate
) -> CardTopic | None:
    """Update card topic"""
    topic = await get_card_topic_by_id(db, topic_id)
    if not topic:
        return None

    update_data = topic_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(topic, field, value)

    await db.commit()
    await db.refresh(topic)
    return topic


async def delete_card_topic(db: AsyncSession, topic_id: int) -> bool:
    """Delete card topic"""
    topic = await get_card_topic_by_id(db, topic_id)
    if not topic:
        return False

    await db.delete(topic)
    await db.commit()
    return True


# Card CRUD
async def get_cards(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    grade: int | None = None,
    quarter: int | None = None,
    subject_id: int | None = None,
    institution_type_id: int | None = None,
    topic_id: int | None = None,
    window_id: int | None = None,
    author_id: int | None = None,
) -> list[Card]:
    """Get cards with optional filters"""
    query = select(Card).options(
        selectinload(Card.topic),
        selectinload(Card.subjects).selectinload(Subject.institution_types),
        selectinload(Card.subjects).selectinload(Subject.windows),
        selectinload(Card.institution_types),
        selectinload(Card.window),
        selectinload(Card.author),
        selectinload(Card.favorites),
    )

    # Apply filters
    filters = []
    if grade is not None:
        filters.append(Card.grade == grade)
    if quarter is not None:
        filters.append(Card.quarter == quarter)
    if topic_id is not None:
        filters.append(Card.topic_id == topic_id)
    if window_id is not None:
        filters.append(Card.window_id == window_id)
    if author_id is not None:
        filters.append(Card.author_id == author_id)

    if filters:
        query = query.where(and_(*filters))

    # Many-to-many filters
    if subject_id is not None:
        query = query.join(Card.subjects).where(Subject.id == subject_id)
    if institution_type_id is not None:
        query = query.join(Card.institution_types).where(
            InstitutionType.id == institution_type_id
        )

    query = query.offset(skip).limit(limit).order_by(Card.created_at.desc())

    result = await db.execute(query)
    return list(result.unique().scalars().all())


async def get_card_by_id(db: AsyncSession, card_id: int) -> Card | None:
    """Get card by ID with all relationships"""
    result = await db.execute(
        select(Card)
        .where(Card.id == card_id)
        .options(
            selectinload(Card.topic),
            selectinload(Card.subjects).selectinload(Subject.institution_types),
            selectinload(Card.subjects).selectinload(Subject.windows).selectinload(Window.template),
            selectinload(Card.institution_types),
            selectinload(Card.window),
            selectinload(Card.author),
            selectinload(Card.favorites),
        )
    )
    return result.scalar_one_or_none()


async def create_card(db: AsyncSession, card_data: CardCreate, author_id: int) -> Card:
    """Create new card"""
    # Extract many-to-many IDs
    subject_ids = card_data.subject_ids
    institution_type_ids = card_data.institution_type_ids

    # Create card without many-to-many fields
    card_dict = card_data.model_dump(exclude={"subject_ids", "institution_type_ids"})
    card = Card(**card_dict, author_id=author_id)

    # Add subjects
    if subject_ids:
        subjects = await db.execute(select(Subject).where(Subject.id.in_(subject_ids)))
        card.subjects = list(subjects.scalars().all())

    # Add institution types
    if institution_type_ids:
        institution_types = await db.execute(
            select(InstitutionType).where(InstitutionType.id.in_(institution_type_ids))
        )
        card.institution_types = list(institution_types.scalars().all())

    db.add(card)
    await db.commit()
    await db.refresh(card)
    # Return card with all relationships loaded
    return await get_card_by_id(db, card.id)


async def update_card(
    db: AsyncSession, card_id: int, card_data: CardUpdate
) -> Card | None:
    """Update card"""
    card = await get_card_by_id(db, card_id)
    if not card:
        return None

    update_data = card_data.model_dump(exclude_unset=True)

    # Handle many-to-many updates
    subject_ids = update_data.pop("subject_ids", None)
    institution_type_ids = update_data.pop("institution_type_ids", None)

    # Update scalar fields
    for field, value in update_data.items():
        setattr(card, field, value)

    # Update subjects
    if subject_ids is not None:
        subjects = await db.execute(select(Subject).where(Subject.id.in_(subject_ids)))
        card.subjects = list(subjects.scalars().all())

    # Update institution types
    if institution_type_ids is not None:
        institution_types = await db.execute(
            select(InstitutionType).where(InstitutionType.id.in_(institution_type_ids))
        )
        card.institution_types = list(institution_types.scalars().all())

    await db.commit()
    await db.refresh(card)
    # Return card with all relationships loaded
    return await get_card_by_id(db, card.id)


async def delete_card(db: AsyncSession, card_id: int) -> bool:
    """Delete card"""
    card = await get_card_by_id(db, card_id)
    if not card:
        return False

    await db.delete(card)
    await db.commit()
    return True


async def toggle_favorite(db: AsyncSession, card_id: int, user_id: int) -> Card | None:
    """Add or remove card from user favorites"""
    from src.models.user import User

    card = await get_card_by_id(db, card_id)
    if not card:
        return None

    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return None

    # Toggle favorite
    if user in card.favorites:
        card.favorites.remove(user)
    else:
        card.favorites.append(user)

    await db.commit()
    await db.refresh(card)
    return card


async def get_user_favorites(
    db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100
) -> list[Card]:
    """Get user's favorite cards"""
    from src.models.user import User

    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.favorite_cards))
    )
    user = result.scalar_one_or_none()
    if not user:
        return []

    # Return paginated favorites
    return user.favorite_cards[skip : skip + limit]


# Autocomplete / Suggestions
async def get_topic_suggestions(db: AsyncSession, query: str, limit: int = 10) -> list[str]:
    """Get topic suggestions based on search query"""
    if not query or len(query) < 2:
        return []

    result = await db.execute(
        select(CardTopic.topic)
        .where(CardTopic.topic.ilike(f"%{query}%"))
        .order_by(CardTopic.topic)
        .distinct()
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_name_suggestions(db: AsyncSession, query: str, limit: int = 10) -> list[str]:
    """Get card name suggestions based on search query"""
    if not query:
        # Return popular names if no query
        result = await db.execute(
            select(Card.name)
            .distinct()
            .limit(limit)
        )
    else:
        result = await db.execute(
            select(Card.name)
            .where(Card.name.ilike(f"%{query}%"))
            .order_by(Card.name)
            .distinct()
            .limit(limit)
        )
    return list(result.scalars().all())


async def get_description_suggestions(db: AsyncSession, query: str, limit: int = 10) -> list[str]:
    """Get card description suggestions based on search query"""
    from sqlalchemy import and_

    if not query:
        result = await db.execute(
            select(Card.description)
            .where(
                and_(
                    Card.description.isnot(None),
                    Card.description != ""
                )
            )
            .distinct()
            .limit(limit)
        )
    else:
        result = await db.execute(
            select(Card.description)
            .where(
                and_(
                    Card.description.isnot(None),
                    Card.description != "",
                    Card.description.ilike(f"%{query}%")
                )
            )
            .order_by(Card.description)
            .distinct()
            .limit(limit)
        )
    return [d for d in result.scalars().all() if d]


async def search_suggestions(db: AsyncSession, query: str, limit: int = 15) -> list[dict]:
    """
    Smart search suggestions across multiple fields.
    Returns list of dicts with: text, type, label
    """
    from src.models.user import User

    if not query or len(query) < 2:
        return []

    suggestions = []
    query_lower = query.lower()

    # Check for author search prefix
    if query_lower.startswith("автор:") or query_lower.startswith("author:"):
        author_query = query.split(":", 1)[1].strip()
        if author_query:
            result = await db.execute(
                select(User.name)
                .join(Card, Card.author_id == User.id)
                .where(User.name.ilike(f"%{author_query}%"))
                .distinct()
                .limit(10)
            )
            for author_name in result.scalars().all():
                suggestions.append({
                    "text": f"автор: {author_name}",
                    "type": "author",
                    "label": f"Автор: {author_name}"
                })
        return suggestions

    # Priority 1: Card names
    names_result = await db.execute(
        select(Card.name)
        .where(Card.name.ilike(f"%{query}%"))
        .order_by(Card.name)
        .distinct()
        .limit(5)
    )
    for name in names_result.scalars().all():
        suggestions.append({
            "text": name,
            "type": "name",
            "label": f"Атауы: {name}"
        })

    # Priority 2: Topics
    topics_result = await db.execute(
        select(CardTopic.topic)
        .join(Card, Card.topic_id == CardTopic.id)
        .where(CardTopic.topic.ilike(f"%{query}%"))
        .order_by(CardTopic.topic)
        .distinct()
        .limit(4)
    )
    for topic in topics_result.scalars().all():
        suggestions.append({
            "text": topic,
            "type": "topic",
            "label": f"Тақырып: {topic}"
        })

    # Priority 3: Subjects
    subjects_result = await db.execute(
        select(Subject.name)
        .join(Card.subjects)
        .where(Subject.name.ilike(f"%{query}%"))
        .distinct()
        .limit(3)
    )
    for subject in subjects_result.scalars().all():
        suggestions.append({
            "text": subject,
            "type": "subject",
            "label": f"Пән: {subject}"
        })

    # Priority 4: Authors
    authors_result = await db.execute(
        select(User.name)
        .join(Card, Card.author_id == User.id)
        .where(User.name.ilike(f"%{query}%"))
        .distinct()
        .limit(2)
    )
    for author_name in authors_result.scalars().all():
        suggestions.append({
            "text": f"автор: {author_name}",
            "type": "author",
            "label": f"Автор: {author_name}"
        })

    # Priority 5: Descriptions (less important)
    desc_result = await db.execute(
        select(Card.description)
        .where(
            and_(
                Card.description.isnot(None),
                Card.description != "",
                Card.description.ilike(f"%{query}%")
            )
        )
        .order_by(Card.description)
        .distinct()
        .limit(2)
    )
    for desc in desc_result.scalars().all():
        if desc:
            display_desc = desc[:50] + "..." if len(desc) > 50 else desc
            suggestions.append({
                "text": desc,
                "type": "description",
                "label": f"Сипаттама: {display_desc}"
            })

    return suggestions[:limit]
