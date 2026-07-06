"""Minimal MMLU structured test — 3 questions."""
from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class MCQAnswer:
    answer: str


def main() -> None:
    url = "https://datasets-server.huggingface.co/rows?dataset=cais/mmlu&config=all&split=test&offset=0&limit=3"
    resp = urllib.request.urlopen(url, timeout=30)
    qs = [r["row"] for r in json.loads(resp.read().decode()).get("rows", [])]

    from petfishframework import Agent, ReAct
    from petfishframework.models.openai import OpenAIModel

    model = OpenAIModel(model=os.environ.get("BENCHMARK_MODEL", "gpt-4o-mini"))
    agent = Agent(model=model, reasoning=ReAct())

    for i, q in enumerate(qs):
        choices = "\n".join(f"{chr(65 + j)}) {c}" for j, c in enumerate(q["choices"]))
        correct = chr(65 + q["answer"])
        prompt = q["question"] + "\n" + choices + "\n\nWhich option is correct?"
        result = agent.run_structured(prompt, MCQAnswer)
        letter = result.data.answer[:1].upper() if result.data else "?"
        ok = "OK" if letter == correct else "MISS"
        print(f"Q{i+1}: PF={letter} Correct={correct} {ok} data={result.data} err={result.parse_error}")


if __name__ == "__main__":
    main()
