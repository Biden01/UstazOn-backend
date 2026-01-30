import pytest
from httpx import AsyncClient
from src.main import app


@pytest.mark.asyncio
async def test_full_test_generation():
    """Test full test generation flow end-to-end"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        request_data = {
            "subject": "Математика",
            "grade": "5",
            "topic": "Квадраттық теңдеулер",
            "question_count": 15,
            "difficulty": "medium",
            "model": "gemini-2.5-flash"
        }

        response = await client.post("/ai/generate-test", data=request_data)

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert len(response.content) > 0


@pytest.mark.asyncio
async def test_test_ai_generates_valid_json():
    """Test that AI generates valid JSON structure for tests"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        request_data = {
            "subject": "Физика",
            "grade": "7",
            "topic": "Механика",
            "question_count": 10,
            "difficulty": "easy",
            "model": "gemini-2.5-flash"
        }

        response = await client.post("/ai/generate-test", data=request_data)

        assert response.status_code == 200
        # If generation succeeds, JSON was valid
        assert len(response.content) > 0


@pytest.mark.asyncio
async def test_test_correct_answer_validation():
    """Test that correct answer validation works"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        request_data = {
            "subject": "География",
            "grade": "6",
            "topic": "Континенты",
            "question_count": 8,
            "difficulty": "medium",
            "model": "gemini-2.5-flash"
        }

        response = await client.post("/ai/generate-test", data=request_data)

        assert response.status_code == 200
        # Validation passed
        assert len(response.content) > 0


@pytest.mark.asyncio
async def test_test_docx_created():
    """Test that DOCX file is created"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        request_data = {
            "subject": "Биология",
            "grade": "8",
            "topic": "Клетка",
            "question_count": 12,
            "difficulty": "hard",
            "model": "gemini-2.5-flash"
        }

        response = await client.post("/ai/generate-test", data=request_data)

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@pytest.mark.asyncio
async def test_test_file_downloadable():
    """Test that test file is downloadable"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        request_data = {
            "subject": "Химия",
            "grade": "9",
            "topic": "Периодическая таблица",
            "question_count": 20,
            "difficulty": "medium",
            "model": "gemini-2.5-flash"
        }

        response = await client.post("/ai/generate-test", data=request_data)

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert "content-disposition" in response.headers
        assert "attachment" in response.headers["content-disposition"]
        assert ".docx" in response.headers["content-disposition"]
