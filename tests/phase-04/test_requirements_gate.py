from __future__ import annotations

from workshop.requirements_gate import normalize_clarifications


def test_normalize_clarifications_accepts_telegram_user_responses() -> None:
    payload = {
        "original_questions": [{"question": "What did you mean?"}],
        "user_responses": [
            {
                "question": "What did you mean?",
                "answer": "12-factor app methodology",
                "source": "clarify tool interaction",
            }
        ],
    }

    assert normalize_clarifications(payload) == [
        "What did you mean?: 12-factor app methodology"
    ]
