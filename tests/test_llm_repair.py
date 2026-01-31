import copy
import pytest
from pydantic import ValidationError

from src.utils.llm_repair import normalize_test_data
from src.schemas.ai_schemas import TestData


def _build_valid_test_data() -> dict:
    return {
        "title": "Математика тесті",
        "instructions": "Дұрыс жауапты таңдаңыз",
        "questions": [
            {
                "question_number": i,
                "question_text": f"Question number {i} text here?",
                "options": [
                    {"label": "A", "text": "Option A"},
                    {"label": "B", "text": "Option B"},
                    {"label": "C", "text": "Option C"},
                    {"label": "D", "text": "Option D"},
                ],
                "correct_answer": "A",
            }
            for i in range(1, 6)
        ],
    }


class TestNormalizeTestData:
    def test_valid_data_passes_through_unchanged(self):
        data = _build_valid_test_data()
        result = normalize_test_data(data)
        assert result == data

    def test_does_not_mutate_input(self):
        data = _build_valid_test_data()
        data["questions"][0]["options"][0] = {"label": "A", "Lext": "Option A"}
        original = copy.deepcopy(data)
        normalize_test_data(data)
        assert data == original

    def test_fixes_lext_typo(self):
        data = _build_valid_test_data()
        for q in data["questions"]:
            for opt in q["options"]:
                opt["Lext"] = opt.pop("text")

        result = normalize_test_data(data)
        TestData.model_validate(result)

    def test_fixes_capitalized_text(self):
        data = _build_valid_test_data()
        for q in data["questions"]:
            for opt in q["options"]:
                opt["Text"] = opt.pop("text")

        result = normalize_test_data(data)
        TestData.model_validate(result)

    def test_fixes_text_answer_typo(self):
        data = _build_valid_test_data()
        for q in data["questions"]:
            for opt in q["options"]:
                opt["text_answer"] = opt.pop("text")

        result = normalize_test_data(data)
        TestData.model_validate(result)

    def test_mixed_typos_across_questions(self):
        data = _build_valid_test_data()
        data["questions"][0]["options"][0] = {"label": "A", "Lext": "Option A"}
        data["questions"][1]["options"][2] = {"label": "C", "Text": "Option C"}
        data["questions"][2]["options"][3] = {"label": "D", "text_answer": "Option D"}

        result = normalize_test_data(data)
        TestData.model_validate(result)

    def test_unknown_key_is_not_fixed(self):
        data = _build_valid_test_data()
        data["questions"][0]["options"][0] = {"label": "A", "teeext": "Option A"}
        result = normalize_test_data(data)
        with pytest.raises(ValidationError):
            TestData.model_validate(result)

    def test_empty_questions_list(self):
        data = {"title": "Valid Title", "questions": []}
        result = normalize_test_data(data)
        assert result == data

    def test_missing_questions_key(self):
        data = {"title": "Valid Title"}
        result = normalize_test_data(data)
        assert result == data

    def test_missing_options_key(self):
        data = _build_valid_test_data()
        del data["questions"][0]["options"]
        result = normalize_test_data(data)
        assert "options" not in result["questions"][0]

    def test_non_dict_options_left_alone(self):
        data = _build_valid_test_data()
        data["questions"][0]["options"] = "not a list"
        result = normalize_test_data(data)
        assert result["questions"][0]["options"] == "not a list"
