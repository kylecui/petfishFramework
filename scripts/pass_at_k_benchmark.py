#!/usr/bin/env python
"""Pass^k Benchmark — petfishFramework vs Raw API.

Council Finding: Pass^k tested with FakeModel proves nothing about real reliability.
This script runs the SAME task k=8 times via:
  A) petfishFramework (ReAct + Calculator + event-sourced Session)
  B) Raw OpenAI API (no framework)
And compares Pass@8 consistency.

Usage:
  OPENAI_API_KEY=sk-... uv run python scripts/pass_at_k_benchmark.py

Cost estimate: ~$2-5 (k=8 × 2 groups × GPT-4o-mini)
"""
from __future__ import annotations

import os
import sys

from petfishframework import Agent, Budget, ReAct
from petfishframework.core.types import Task
from petfishframework.models.openai import OpenAIModel
from petfishframework.reliability import exact_match, pass_at_k
from petfishframework.tools.calculator import Calculator

TASKS = [
    Task(prompt="What is 17 * 23? Use the calculator."),
    Task(prompt="What is (45 + 55) / 2? Use the calculator."),
    Task(prompt="What is 2^10? Use the calculator."),
]
K = 8
MODEL = os.environ.get("BENCHMARK_MODEL", "gpt-4o-mini")


def run_benchmark() -> None:
    from dotenv import load_dotenv

    load_dotenv()  # Load .env if present

    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set.")
        sys.exit(1)

    model = OpenAIModel(model=MODEL)
    agent = Agent(model=model, reasoning=ReAct(), tools=(Calculator(),))

    print(f"Pass^{K} Benchmark — {MODEL}")
    print(f"Tasks: {len(TASKS)} | k={K} | Agreement: exact_match")
    print("=" * 60)

    for task in TASKS:
        print(f"\nTask: {task.prompt}")

        # Group A: petfishFramework
        def pf_factory(t: Task):
            return agent.session(t, budget=Budget(max_steps=5))

        pf_result = pass_at_k(pf_factory, task, k=K, agreement=exact_match)
        print(f"  petfishFramework Pass@{K}: {pf_result.pass_count}/{K}  {'✅' if pf_result.agreed else '❌'}")

        # Group B: Raw API (minimal — just ask the model directly, no framework)
        raw_answers = []
        for _i in range(K):
            try:
                import openai

                client = openai.OpenAI(base_url=os.environ.get("OPENAI_BASE_URL"))
                resp = client.chat.completions.create(
                    model=MODEL,
                    messages=[{"role": "user", "content": task.prompt}],
                    temperature=0.7,
                )
                raw_answers.append(resp.choices[0].message.content or "")
            except Exception as e:
                raw_answers.append(f"ERROR: {e}")

        # Check raw consistency
        first = raw_answers[0].strip() if raw_answers else ""
        raw_agreed = all(a.strip() == first for a in raw_answers)
        raw_pass = K if raw_agreed else 0
        print(f"  Raw API           Pass@{K}: {raw_pass}/{K}  {'✅' if raw_agreed else '❌'}")

        # Show variance
        unique_pf = len(set(pf_result.answers))
        unique_raw = len(set(raw_answers))
        print(f"  Unique answers:   PF={unique_pf}  Raw={unique_raw}")

    print("\n" + "=" * 60)
    print("Done. Document results in docs/benchmark-results.md")


if __name__ == "__main__":
    run_benchmark()
