"""Prove structured output eliminates MMLU extraction ambiguity."""
from __future__ import annotations

import re
from dataclasses import dataclass

from petfishframework import Agent, ReAct
from petfishframework.core.types import ModelResponse
from petfishframework.models.fake import FakeModel


@dataclass(frozen=True)
class MCQAnswer:
    answer: str


def main() -> None:
    # Simulate verbose model output (what causes extraction issues)
    model = FakeModel(responses=(
        ModelResponse(content="The polynomial has degree 5, so it has 5 roots. The answer is C."),
        ModelResponse(content='{"answer": "C"}'),
    ))

    agent = Agent(model=model, reasoning=ReAct())

    # Without structured (extraction needed)
    r1 = agent.run("What are the roots? A) 1  B) 2  C) 5  D) 7")
    print("Without structured:")
    print(f"  Raw answer: {r1.answer[:60]!r}")
    first_char = r1.answer.strip().upper()[:1]
    print(f"  First char: {first_char!r}  (WRONG: gets 'T' from 'The')")
    matches = re.findall(r"\b[ABCD]\b", r1.answer.upper())
    print(f"  Regex last: {matches[-1] if matches else '?'}  (correct but needs regex)")

    # With structured (zero ambiguity)
    r2 = agent.run_structured("What are the roots? A) 1  B) 2  C) 5  D) 7", MCQAnswer)
    print("\nWith run_structured:")
    print(f"  data: {r2.data}")
    print(f"  parse_error: {r2.parse_error}")
    if r2.data:
        print(f"  answer: {r2.data.answer!r}  (ZERO ambiguity)")


if __name__ == "__main__":
    main()
