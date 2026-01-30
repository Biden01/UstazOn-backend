import pytest
from pydantic import ValidationError
from src.schemas.ai_schemas import PresentationData, PresentationSlide, TestData, TestQuestion, QuestionOption


def test_valid_presentation_json():
    """Test that valid presentation JSON passes validation"""
    data = {
        "title": "Квадраттық теңдеулер",
        "slides": [
            {
                "slide_number": 1,
                "title": "Title",
                "content": ["Point 1"],
                "image_query": "mathematics abstract"
            },
            {
                "slide_number": 2,
                "title": "Second Slide",
                "content": ["Point 1", "Point 2"],
                "image_query": "geometry shapes"
            },
            {
                "slide_number": 3,
                "title": "Third Slide",
                "content": ["Point 1", "Point 2", "Point 3"],
                "image_query": "algebra equations"
            }
        ]
    }
    validated = PresentationData(**data)
    assert validated.title == "Квадраттық теңдеулер"
    assert len(validated.slides) == 3


def test_valid_test_json():
    """Test that valid test JSON passes validation"""
    data = {
        "title": "Математика тесті",
        "instructions": "Дұрыс жауапты таңдаңыз",
        "questions": [
            {
                "question_number": 1,
                "question_text": "What is 2 + 2?",
                "options": [
                    {"label": "A", "text": "3"},
                    {"label": "B", "text": "4"},
                    {"label": "C", "text": "5"},
                    {"label": "D", "text": "6"}
                ],
                "correct_answer": "B"
            },
            {
                "question_number": 2,
                "question_text": "What is 3 * 3?",
                "options": [
                    {"label": "A", "text": "6"},
                    {"label": "B", "text": "9"},
                    {"label": "C", "text": "12"},
                    {"label": "D", "text": "15"}
                ],
                "correct_answer": "B"
            },
            {
                "question_number": 3,
                "question_text": "What is 10 - 5?",
                "options": [
                    {"label": "A", "text": "3"},
                    {"label": "B", "text": "4"},
                    {"label": "C", "text": "5"},
                    {"label": "D", "text": "6"}
                ],
                "correct_answer": "C"
            },
            {
                "question_number": 4,
                "question_text": "What is 12 / 4?",
                "options": [
                    {"label": "A", "text": "2"},
                    {"label": "B", "text": "3"},
                    {"label": "C", "text": "4"},
                    {"label": "D", "text": "5"}
                ],
                "correct_answer": "B"
            },
            {
                "question_number": 5,
                "question_text": "What is 5 + 7?",
                "options": [
                    {"label": "A", "text": "10"},
                    {"label": "B", "text": "11"},
                    {"label": "C", "text": "12"},
                    {"label": "D", "text": "13"}
                ],
                "correct_answer": "C"
            }
        ]
    }
    validated = TestData(**data)
    assert validated.title == "Математика тесті"
    assert len(validated.questions) == 5


def test_missing_required_fields():
    """Test that missing required fields fail with ValidationError"""
    data = {
        "title": "Test",
        "slides": [
            {
                "slide_number": 1,
                "title": "Title"
                # Missing content and image_query
            }
        ]
    }
    with pytest.raises(ValidationError):
        PresentationData(**data)


def test_invalid_image_query_url():
    """Test that URLs in image_query field fail validation"""
    data = {
        "title": "Test Presentation",
        "slides": [
            {
                "slide_number": 1,
                "title": "Title",
                "content": [],
                "image_query": "https://unsplash.com/photo/123"
            },
            {
                "slide_number": 2,
                "title": "Second",
                "content": [],
                "image_query": "valid query"
            },
            {
                "slide_number": 3,
                "title": "Third",
                "content": [],
                "image_query": "another valid"
            }
        ]
    }
    with pytest.raises(ValidationError):
        PresentationData(**data)


def test_invalid_image_query_kazakh():
    """Test that Kazakh/Cyrillic in image_query field fails validation"""
    data = {
        "title": "Test Presentation",
        "slides": [
            {
                "slide_number": 1,
                "title": "Title",
                "content": [],
                "image_query": "математика"
            },
            {
                "slide_number": 2,
                "title": "Second",
                "content": [],
                "image_query": "valid query"
            },
            {
                "slide_number": 3,
                "title": "Third",
                "content": [],
                "image_query": "another valid"
            }
        ]
    }
    with pytest.raises(ValidationError):
        PresentationData(**data)


def test_incorrect_question_answer_validation():
    """Test that incorrect answer validation fails"""
    data = {
        "title": "Math Test",
        "questions": [
            {
                "question_number": 1,
                "question_text": "What is 2 + 2?",
                "options": [
                    {"label": "A", "text": "3"},
                    {"label": "B", "text": "4"},
                    {"label": "C", "text": "5"},
                    {"label": "D", "text": "6"}
                ],
                "correct_answer": "E"  # Invalid - not in options
            },
            {
                "question_number": 2,
                "question_text": "What is 3 * 3?",
                "options": [
                    {"label": "A", "text": "6"},
                    {"label": "B", "text": "9"},
                    {"label": "C", "text": "12"},
                    {"label": "D", "text": "15"}
                ],
                "correct_answer": "B"
            },
            {
                "question_number": 3,
                "question_text": "What is 10 - 5?",
                "options": [
                    {"label": "A", "text": "3"},
                    {"label": "B", "text": "4"},
                    {"label": "C", "text": "5"},
                    {"label": "D", "text": "6"}
                ],
                "correct_answer": "C"
            },
            {
                "question_number": 4,
                "question_text": "What is 12 / 4?",
                "options": [
                    {"label": "A", "text": "2"},
                    {"label": "B", "text": "3"},
                    {"label": "C", "text": "4"},
                    {"label": "D", "text": "5"}
                ],
                "correct_answer": "B"
            },
            {
                "question_number": 5,
                "question_text": "What is 5 + 7?",
                "options": [
                    {"label": "A", "text": "10"},
                    {"label": "B", "text": "11"},
                    {"label": "C", "text": "12"},
                    {"label": "D", "text": "13"}
                ],
                "correct_answer": "C"
            }
        ]
    }
    with pytest.raises(ValidationError):
        TestData(**data)


def test_additional_properties_in_json():
    """Test that additional properties in JSON fail validation"""
    data = {
        "title": "Test Presentation",
        "extra_field": "not allowed",
        "slides": [
            {
                "slide_number": 1,
                "title": "Title",
                "content": [],
                "image_query": "test query"
            },
            {
                "slide_number": 2,
                "title": "Second",
                "content": [],
                "image_query": "another query"
            },
            {
                "slide_number": 3,
                "title": "Third",
                "content": [],
                "image_query": "third query"
            }
        ]
    }
    with pytest.raises(ValidationError):
        PresentationData(**data)


def test_out_of_range_values():
    """Test that out-of-range values fail validation"""
    # Title too short (min_length=5)
    data = {
        "title": "Test",
        "slides": [
            {
                "slide_number": 1,
                "title": "Title",
                "content": [],
                "image_query": "test query"
            },
            {
                "slide_number": 2,
                "title": "Second",
                "content": [],
                "image_query": "another query"
            },
            {
                "slide_number": 3,
                "title": "Third",
                "content": [],
                "image_query": "third query"
            }
        ]
    }
    with pytest.raises(ValidationError):
        PresentationData(**data)

    # Too many slides (max=30)
    data_too_many_slides = {
        "title": "Valid Title",
        "slides": [
            {
                "slide_number": i,
                "title": f"Slide {i}",
                "content": [],
                "image_query": "test query"
            }
            for i in range(1, 32)
        ]
    }
    with pytest.raises(ValidationError):
        PresentationData(**data_too_many_slides)
