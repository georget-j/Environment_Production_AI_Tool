from app.coupons import discount_percent, is_valid


def test_valid_code_is_recognised() -> None:
    assert is_valid("WELCOME10")
    assert discount_percent("welcome10") == 10


def test_unknown_code_is_invalid() -> None:
    assert not is_valid("FREESTUFF")
    assert discount_percent("FREESTUFF") == 0


def test_none_is_invalid() -> None:
    assert not is_valid(None)
    assert discount_percent(None) == 0


def test_blank_is_invalid() -> None:
    assert not is_valid("   ")
