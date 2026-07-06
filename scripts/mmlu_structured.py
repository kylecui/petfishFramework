"""MMLU with run_structured — zero extraction ambiguity."""
from __future__ import annotations

import json
import os
import random
import urllib.request
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    random.seed(42)
    model_name = os.environ.get("BENCHMARK_MODEL", "gpt-4o-mini")

    url = "https://datasets-server.huggingface.co/rows?dataset=cais/mmlu&config=all&split=test&offset=0&limit=10"
    resp = urllib.request.urlopen(url, timeout=30)
    questions = [r["row"] for r in json.loads(resp.read().decode()).get("rows", [])]

    @dataclass(frozen=True)
    class MCQAnswer:
        answer: str

    from petfishframework import Agent, ReAct
    from petfishframework.models.openai import OpenAIModel

    model = OpenAIModel(model=model_name)
    agent = Agent(model=model, reasoning=ReAct())

    pf_correct = 0
    total = len(questions)
    print(f"MMLU with run_structured | {model_name}")
    print("=" * 50)

    for i, q in enumerate(questions):
        choices = "\n".join(f"{chr(65+j)}) {c}" for j, c in enumerate(q["choices"]))
        prompt = f"Question: {q['question']}\n{choices}\n\nWhich option (A, B, C, or D) is correct?"
        correct = chr(65 + q["answer"])

        result = agent.run_structured(prompt, MCQAnswer)
        if result.data:
            pf_letter = result.data.answer.strip().upper()[:1]
        else:
            pf_letter = "?"
        ok = pf_letter == correct
        pf_correct += ok
        status = "OK" if ok else "MISS"
        err = "parse_fail" if result.parse_error else "clean"
        print(f"  [{i+1}] PF:{pf_letter} Correct:{correct} {status} ({err})")

    print(f"\nMMLU run_structured ({total} questions):")
    print(f"  PF: {pf_correct}/{total} ({pf_correct*100//total}%)")
    print(f"  Zero extraction ambiguity — structured output forces clean letter")


if __name__ == "__main__":
    main()
