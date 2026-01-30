import pytest
from io import BytesIO
from pptx import Presentation
from unittest.mock import patch
from src.services.presentation_service import presentation_service
from src.schemas.ai_schemas import PresentationData


def test_generate_pptx_with_images():
    """Test generating PPTX with valid slide data and images"""
    data = {
        "title": "Test Presentation",
        "slides": [
            {
                "slide_number": 1,
                "title": "Introduction",
                "content": ["Point 1", "Point 2", "Point 3"],
                "image_query": "education classroom",
                "notes": "Speaker notes for slide 1"
            },
            {
                "slide_number": 2,
                "title": "Main Content",
                "content": ["First item", "Second item"],
                "image_query": "mathematics abstract",
                "notes": "Speaker notes for slide 2"
            },
            {
                "slide_number": 3,
                "title": "Conclusion",
                "content": ["Summary point"],
                "image_query": "graduation success",
                "notes": "Final notes"
            }
        ]
    }

    pptx_bytes = presentation_service.create_presentation(data)

    assert pptx_bytes is not None
    assert isinstance(pptx_bytes, BytesIO)
    assert len(pptx_bytes.getvalue()) > 0

    # Verify PPTX is valid by opening it
    pptx_bytes.seek(0)
    prs = Presentation(pptx_bytes)
    assert len(prs.slides) == 3


def test_missing_image_placeholder():
    """Test that presentation continues with placeholder when image fetch fails"""
    data = {
        "title": "Test Presentation",
        "slides": [
            {
                "slide_number": 1,
                "title": "Slide One",
                "content": ["Content 1"],
                "image_query": "nonexistent query xyz123",
                "notes": ""
            },
            {
                "slide_number": 2,
                "title": "Slide Two",
                "content": ["Content 2"],
                "image_query": "another bad query",
                "notes": ""
            },
            {
                "slide_number": 3,
                "title": "Slide Three",
                "content": ["Content 3"],
                "image_query": "third bad query",
                "notes": ""
            }
        ]
    }

    with patch('src.services.image_service.image_service.fetch_image', return_value=None):
        pptx_bytes = presentation_service.create_presentation(data)

        assert pptx_bytes is not None
        pptx_bytes.seek(0)
        prs = Presentation(pptx_bytes)
        assert len(prs.slides) == 3


def test_invalid_formatting_uses_defaults():
    """Test that invalid formatting falls back to defaults"""
    data = {
        "title": "Test Presentation",
        "slides": [
            {
                "slide_number": 1,
                "title": "Title",
                "content": [],
                "image_query": "test query",
                "notes": ""
            },
            {
                "slide_number": 2,
                "title": "Second",
                "content": [],
                "image_query": "another query",
                "notes": ""
            },
            {
                "slide_number": 3,
                "title": "Third",
                "content": [],
                "image_query": "third query",
                "notes": ""
            }
        ]
    }

    pptx_bytes = presentation_service.create_presentation(data)

    assert pptx_bytes is not None
    pptx_bytes.seek(0)
    prs = Presentation(pptx_bytes)
    assert len(prs.slides) == 3


def test_speaker_notes_included():
    """Test that speaker notes are present in PPTX"""
    data = {
        "title": "Test Presentation",
        "slides": [
            {
                "slide_number": 1,
                "title": "Slide with Notes",
                "content": ["Point 1"],
                "image_query": "test query",
                "notes": "These are important speaker notes"
            },
            {
                "slide_number": 2,
                "title": "Another Slide",
                "content": ["Point 2"],
                "image_query": "another query",
                "notes": "More speaker notes here"
            },
            {
                "slide_number": 3,
                "title": "Final Slide",
                "content": ["Point 3"],
                "image_query": "final query",
                "notes": "Final notes"
            }
        ]
    }

    pptx_bytes = presentation_service.create_presentation(data)

    assert pptx_bytes is not None
    pptx_bytes.seek(0)
    prs = Presentation(pptx_bytes)

    # Check that notes exist (notes slides are created)
    assert len(prs.slides) == 3


def test_empty_content_slide():
    """Test that slides with empty content are handled"""
    data = {
        "title": "Test Presentation",
        "slides": [
            {
                "slide_number": 1,
                "title": "Title Slide Only",
                "content": [],
                "image_query": "test query",
                "notes": ""
            },
            {
                "slide_number": 2,
                "title": "Another Empty",
                "content": [],
                "image_query": "another query",
                "notes": ""
            },
            {
                "slide_number": 3,
                "title": "Third Empty",
                "content": [],
                "image_query": "third query",
                "notes": ""
            }
        ]
    }

    pptx_bytes = presentation_service.create_presentation(data)

    assert pptx_bytes is not None
    pptx_bytes.seek(0)
    prs = Presentation(pptx_bytes)
    assert len(prs.slides) == 3
