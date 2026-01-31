"""
LLM output repair layer.

Fixes ONLY known, safe key typos that LLMs occasionally produce
in structured JSON output. Does NOT weaken Pydantic schemas.
"""
import copy
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Mapping: wrong_key -> correct_key
# Add entries here as new LLM typos are observed in production logs.
_OPTION_KEY_FIXES: dict[str, str] = {
    "Lext": "text",
    "Text": "text",
    "text_answer": "text",
}


def _fix_option_keys(option: dict[str, Any]) -> dict[str, Any]:
    """Apply known key renames to a single option dict."""
    fixed = {}
    for key, value in option.items():
        corrected_key = _OPTION_KEY_FIXES.get(key, key)
        fixed[corrected_key] = value
    return fixed


def normalize_test_data(data: dict[str, Any]) -> dict[str, Any]:
    """
    Walk through questions -> options and rename known typo keys.

    Returns a deep copy with fixes applied. Never mutates the input.
    """
    data = copy.deepcopy(data)

    questions = data.get("questions")
    if not isinstance(questions, list):
        return data

    for question in questions:
        if not isinstance(question, dict):
            continue
        options = question.get("options")
        if not isinstance(options, list):
            continue
        question["options"] = [
            _fix_option_keys(opt) if isinstance(opt, dict) else opt
            for opt in options
        ]

    return data
