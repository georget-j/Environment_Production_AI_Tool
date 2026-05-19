from app.validation import parse_pytest_output


def test_parses_passing_summary() -> None:
    summary = parse_pytest_output("....                       [100%]\n5 passed in 0.42s\n")
    assert summary.passed
    assert summary.passed_count == 5
    assert summary.failed_count == 0


def test_parses_failing_summary() -> None:
    summary = parse_pytest_output("F.                          [50%]\n1 failed, 1 passed in 0.42s\n")
    assert not summary.passed
    assert summary.passed_count == 1
    assert summary.failed_count == 1


def test_parses_error_summary() -> None:
    summary = parse_pytest_output("E\n1 error in 0.10s")
    assert not summary.passed
    assert summary.failed_count == 1


def test_no_tests_ran() -> None:
    summary = parse_pytest_output("collected 0 items\n\nno tests ran in 0.01s")
    assert not summary.passed
    assert summary.passed_count == 0
    assert summary.failed_count == 0


def test_empty_input() -> None:
    summary = parse_pytest_output(None)
    assert not summary.passed
    assert summary.raw == ""
