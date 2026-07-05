"""TDD tests for structured output parsing and Agent.run_structured()."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from petfishframework import Agent
from petfishframework.core.structured import StructuredResult, parse_json, parse_structured
from petfishframework.core.types import ModelResponse
from petfishframework.models.fake import FakeModel


@dataclass(frozen=True)
class PersonInfo:
    name: str
    age: int


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    relevant: bool


def test_parse_json_direct() -> None:
    content = '{"name": "Alice", "age": 30}'
    parsed = parse_json(content)
    assert parsed == {"name": "Alice", "age": 30}


def test_parse_json_code_block() -> None:
    content = "Here is the data:\n```json\n{\"name\": \"Bob\"}\n```\nDone."
    parsed = parse_json(content)
    assert parsed == {"name": "Bob"}


def test_parse_json_top_level_array() -> None:
    content = "Some text before [1, 2, 3] and after"
    parsed = parse_json(content)
    assert parsed == [1, 2, 3]


def test_parse_json_nested() -> None:
    content = '{"outer": {"inner": [1, 2, 3]}, "flag": true}'
    parsed = parse_json(content)
    assert parsed == {"outer": {"inner": [1, 2, 3]}, "flag": True}


def test_parse_json_empty_content_raises() -> None:
    with pytest.raises(ValueError, match="No valid JSON found"):
        parse_json("")


def test_parse_structured_dataclass() -> None:
    content = '{"name": "Alice", "age": 30}'
    parsed = parse_structured(content, PersonInfo)
    assert parsed == PersonInfo(name="Alice", age=30)


def test_parse_structured_extra_fields() -> None:
    content = '{"name": "Alice", "age": 30, "extra": "ignored"}'
    parsed = parse_structured(content, PersonInfo)
    assert parsed == PersonInfo(name="Alice", age=30)


def test_parse_structured_invalid_json() -> None:
    with pytest.raises(ValueError, match="Could not parse structured output"):
        parse_structured("not json at all", PersonInfo)


def test_parse_structured_non_object_raises() -> None:
    with pytest.raises(ValueError, match="Expected a JSON object"):
        parse_structured("[1, 2, 3]", PersonInfo)


def test_parse_structured_non_dataclass_raises() -> None:
    with pytest.raises(ValueError, match="output_type must be a dataclass"):
        parse_structured('{"name": "Alice"}', dict)


def test_agent_run_structured_golden() -> None:
    model = FakeModel(
        responses=(ModelResponse(content='{"name": "Alice", "age": 30}'),)
    )
    agent = Agent(model=model)

    result = agent.run_structured("Describe this person.", PersonInfo)

    assert isinstance(result, StructuredResult)
    assert result.data == PersonInfo(name="Alice", age=30)
    assert result.parse_error is None
    assert result.session_id != ""


def test_agent_run_structured_parse_failure() -> None:
    model = FakeModel(responses=(ModelResponse(content="I cannot provide JSON"),))
    agent = Agent(model=model)

    result = agent.run_structured("Describe this person.", PersonInfo)

    assert isinstance(result, StructuredResult)
    assert result.data is None
    assert result.parse_error is not None
    assert result.session_id != ""


def test_agent_run_structured_search_result() -> None:
    content = (
        '{"title": "Petfish Docs", "url": "https://example.com", "relevant": true}'
    )
    model = FakeModel(responses=(ModelResponse(content=content),))
    agent = Agent(model=model)

    result = agent.run_structured("Find a relevant page.", SearchResult)

    assert result.data == SearchResult(
        title="Petfish Docs", url="https://example.com", relevant=True
    )
    assert result.parse_error is None


def test_structured_result_immutable() -> None:
    result = StructuredResult(answer="raw", data=None, parse_error=None, session_id="s1")
    with pytest.raises(AttributeError):
        result.answer = "mutated"
