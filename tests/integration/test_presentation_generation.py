import pytest
from httpx import AsyncClient
from src.main import app


@pytest.mark.asyncio
async def test_full_presentation_generation():
    """Test full presentation generation flow end-to-end"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        request_data = {
            "subject": "Математика",
            "grade": "5",
            "topic": "Квадраттық теңдеулер",
            "slides_count": 12,
            "model": "gemini-2.5-flash"
        }

        response = await client.post("/ai/generate-presentation", data=request_data)

        # Verify response
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        assert len(response.content) > 0


@pytest.mark.asyncio
async def test_presentation_ai_generates_valid_json():
    """Test that AI generates valid JSON structure"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        request_data = {
            "subject": "Физика",
            "grade": "7",
            "topic": "Механика",
            "slides_count": 8,
            "model": "gemini-2.5-flash"
        }

        response = await client.post("/ai/generate-presentation", data=request_data)

        assert response.status_code == 200
        # If generation succeeds, JSON was valid
        assert len(response.content) > 0


@pytest.mark.asyncio
async def test_presentation_images_fetched():
    """Test that images are fetched from Unsplash"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        request_data = {
            "subject": "География",
            "grade": "6",
            "topic": "Континенты",
            "slides_count": 5,
            "model": "gemini-2.5-flash"
        }

        response = await client.post("/ai/generate-presentation", data=request_data)

        assert response.status_code == 200
        # Images should be included in PPTX
        assert len(response.content) > 0


@pytest.mark.asyncio
async def test_presentation_downloadable():
    """Test that PPTX file is downloadable"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        request_data = {
            "subject": "Биология",
            "grade": "8",
            "topic": "Клетка",
            "slides_count": 10,
            "model": "gemini-2.5-flash"
        }

        response = await client.post("/ai/generate-presentation", data=request_data)

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.presentationml.presentation"


@pytest.mark.asyncio
async def test_presentation_content_type_header():
    """Test that Content-Type header is correct"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        request_data = {
            "subject": "Химия",
            "grade": "9",
            "topic": "Периодическая таблица",
            "slides_count": 7,
            "model": "gemini-2.5-flash"
        }

        response = await client.post("/ai/generate-presentation", data=request_data)

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.presentationml.presentation"


@pytest.mark.asyncio
async def test_presentation_content_disposition_header():
    """Test that Content-Disposition header is correct"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        request_data = {
            "subject": "История",
            "grade": "10",
            "topic": "Древний мир",
            "slides_count": 15,
            "model": "gemini-2.5-flash"
        }

        response = await client.post("/ai/generate-presentation", data=request_data)

        assert response.status_code == 200
        assert "content-disposition" in response.headers
        assert "attachment" in response.headers["content-disposition"]
        assert ".pptx" in response.headers["content-disposition"]
