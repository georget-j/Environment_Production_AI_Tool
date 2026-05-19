from app.ai.mentor import ChallengeContext, build_messages
from app.ai.prompts import get_prompt, get_prompt_sha

CTX = ChallengeContext(
    title="Fix invalid coupon handling",
    scenario="Customers are getting discounts with random codes.",
    learner_goal="Reject invalid codes with HTTP 400.",
    latest_test_output="1 failed, 3 passed in 0.42s",
    attempts_count=1,
)


def test_prompt_sections_load() -> None:
    p = get_prompt("socratic-hint-prompt")
    assert "senior software engineer" in p.lower()


def test_prompt_sha_is_stable() -> None:
    sha1 = get_prompt_sha()
    sha2 = get_prompt_sha()
    assert sha1 == sha2
    assert len(sha1) >= 16


def test_build_messages_includes_context_and_history() -> None:
    history = [
        {"role": "user", "content": "Where do I start?"},
        {"role": "assistant", "content": "Have you read the failing test?"},
    ]
    msgs = build_messages(CTX, history, "I read it. The assertion checks the response code.", 2)
    assert msgs[0]["role"] == "system"
    assert "senior software engineer" in msgs[0]["content"].lower()
    assert "Fix invalid coupon" in msgs[1]["content"]
    assert "HINT LEVEL 2" in msgs[1]["content"]
    assert msgs[-1]["role"] == "user"
    assert msgs[-1]["content"].startswith("I read it.")


def test_hint_level_clamped() -> None:
    msgs = build_messages(CTX, [], "help", 99)
    assert "HINT LEVEL 3" in msgs[1]["content"]
    msgs = build_messages(CTX, [], "help", -5)
    assert "HINT LEVEL 1" in msgs[1]["content"]


def test_long_test_output_is_truncated() -> None:
    ctx = ChallengeContext(
        title="x", scenario="x", learner_goal="x",
        latest_test_output="Q" * 5000, attempts_count=0,
    )
    msgs = build_messages(ctx, [], "help", 1)
    body = msgs[1]["content"]
    # Q is a rare letter in the prompt text, so its count equals the truncated payload size.
    assert body.count("Q") == 2000
