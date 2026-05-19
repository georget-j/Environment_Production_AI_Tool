import json

import jsonschema

from app.ai.review import PR_REVIEW_SCHEMA


def test_minimal_passing_review_validates() -> None:
    sample = {
        "passed": True,
        "score": 85,
        "summary": "Looks good.",
        "strengths": ["Clean code."],
        "issues": [],
        "required_fixes": [],
        "skills_practiced": ["api-validation"],
        "next_recommended_challenge": "fastapi-commerce-reject-invalid-coupons",
    }
    jsonschema.validate(sample, PR_REVIEW_SCHEMA["schema"])


def test_invalid_severity_fails() -> None:
    sample = {
        "passed": False,
        "score": 40,
        "summary": "Issue found.",
        "strengths": [],
        "issues": [{"severity": "spicy", "title": "x", "suggestion": "y"}],
        "required_fixes": [],
        "skills_practiced": [],
        "next_recommended_challenge": None,
    }
    try:
        jsonschema.validate(sample, PR_REVIEW_SCHEMA["schema"])
    except jsonschema.ValidationError:
        return
    raise AssertionError("Expected ValidationError")


def test_missing_required_field_fails() -> None:
    sample = {
        "passed": True,
        "score": 100,
        "summary": "ok",
        "strengths": [],
        "issues": [],
        "required_fixes": [],
        "skills_practiced": [],
    }
    try:
        jsonschema.validate(sample, PR_REVIEW_SCHEMA["schema"])
    except jsonschema.ValidationError:
        return
    raise AssertionError("Expected ValidationError")


def test_schema_serialisable() -> None:
    json.dumps(PR_REVIEW_SCHEMA)
