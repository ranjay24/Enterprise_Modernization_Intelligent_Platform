"""Quick integration tests for _truncate_to_budget improvements."""

from app.services.bedrock_analyzer import _truncate_to_budget, _truncate_json_safe


def test_json_safe_truncation_preserves_newline_boundaries():
    text = '{"a": 1}\n{"b": 2}\n{"c": 3}\n{"d": 4}'
    result = _truncate_json_safe(text, 20)
    assert result.endswith("\n") or result.endswith("}"), f"Bad truncation: {result!r}"


def test_full_fit_no_truncation():
    sections = [("header", "HEADER\n"), ("classes", "class A {}\n"), ("footer", "\nFOOTER")]
    result = _truncate_to_budget(sections, total_budget=500)
    assert "class A" in result
    assert "FOOTER" in result


def test_truncation_with_marker():
    big_json = '{"data": "' + "x" * 10000 + '"}'
    sections = [("header", "HEADER\n"), ("big", big_json), ("footer", "\nFOOTER")]
    result = _truncate_to_budget(sections, total_budget=500)
    assert "... [truncated" in result


def test_truncation_proportional():
    sections = [
        ("header", "HEADER\n"),
        ("big1", "a" * 2000),
        ("big2", "b" * 2000),
        ("footer", "\nFOOTER"),
    ]
    result = _truncate_to_budget(sections, total_budget=500)
    assert "... [truncated big1]" in result
    assert "... [truncated big2]" in result


def test_empty_sections():
    assert _truncate_to_budget([], total_budget=100) == ""


def test_only_header_and_footer():
    sections = [("header", "HEADER\n"), ("footer", "\nFOOTER")]
    result = _truncate_to_budget(sections, total_budget=100)
    assert result == "HEADER\n" + "\nFOOTER"
