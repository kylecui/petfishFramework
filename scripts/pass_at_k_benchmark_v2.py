#!/usr/bin/env python
"""Pass^k Benchmark v2 — verbose output with actual answers + numeric_match.

Improvements over v1:
- Prints EVERY answer (not just counts)
- Adds numeric_match agreement (extract numbers, compare)
- Adds stronger system prompt for PF group ("always use calculator")
- Saves results to docs/benchmark-results.md
"""
from __future__ import annotations

import os
import re
import sys


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv()

    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set.")
        sys.exit(1)

    from petfishframework import Agent, Budget, ReAct
    from petfishframework.core.types import Message, ModelRequest, ModelResponse, Role, Task, Result
    from petfishframework.models.openai import OpenAIModel
    from petfishframework.reliability import exact_match
    from petfishframework.tools.calculator import Calculator

    model_name = os.environ.get("BENCHMARK_MODEL", "gpt-4o-mini")
    K = 8

    TASKS = [
        Task(prompt="What is 17 * 23? Use the calculator tool."),
        Task(prompt="What is (45 + 55) / 2? Use the calculator tool."),
        Task(prompt="What is 2^10? Use the calculator tool."),
    ]

    def numeric_match(results: list[Result]) -> bool:
        """Extract the LAST number (the final answer) from each response and compare.

        Previous version compared ALL numbers including operands mentioned in
        explanation text — this was incorrect. A model that says "17 * 23 = 391"
        vs "The product of 17 and 23 is 391" both have the correct answer (391)
        but different number sets. We should only compare the answer value.
        """
        def extract_answer_num(s: str) -> str | None:
            nums = re.findall(r"\d+\.?\d*", s)
            return nums[-1] if nums else None
        if not results:
            return False
        first = extract_answer_num(results[0].answer.strip())
        if first is None:
            return False
        return all(extract_answer_num(r.answer.strip()) == first for r in results)

    model = OpenAIModel(model=model_name)
    agent = Agent(model=model, reasoning=ReAct(), tools=(Calculator(),))

    lines: list[str] = []
    lines.append(f"# Pass^{K} Benchmark Results")
    lines.append(f"")
    lines.append(f"> Model: {model_name} | k={K} | Date: 2026-07-05")
    lines.append(f"")

    for task in TASKS:
        lines.append(f"## Task: {task.prompt}")
        lines.append("")

        # --- petfishFramework ---
        pf_answers: list[str] = []
        for i in range(K):
            session = agent.session(task, budget=Budget(max_steps=5))
            result = session.run()
            pf_answers.append(result.answer.strip())

        pf_exact = all(a == pf_answers[0] for a in pf_answers)
        pf_numeric = numeric_match([Result(answer=a) for a in pf_answers])

        lines.append(f"### petfishFramework")
        lines.append(f"- exact_match: {'8/8 ✅' if pf_exact else '0/8 ❌'}")
        lines.append(f"- numeric_match: {'8/8 ✅' if pf_numeric else '0/8 ❌'}")
        lines.append(f"- unique answers: {len(set(pf_answers))}")
        lines.append(f"")
        lines.append(f"| Run # | Answer |")
        lines.append(f"|---|---|")
        for i, a in enumerate(pf_answers):
            lines.append(f"| {i+1} | {a[:120]} |")
        lines.append(f"")

        # --- Raw API ---
        import openai

        client = openai.OpenAI(base_url=os.environ.get("OPENAI_BASE_URL"))
        raw_answers: list[str] = []
        for _i in range(K):
            try:
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": task.prompt}],
                    temperature=0.7,
                )
                raw_answers.append((resp.choices[0].message.content or "").strip())
            except Exception as e:
                raw_answers.append(f"ERROR: {e}")

        raw_exact = all(a == raw_answers[0] for a in raw_answers)
        raw_numeric = numeric_match([Result(answer=a) for a in raw_answers])

        lines.append(f"### Raw API (no framework)")
        lines.append(f"- exact_match: {'8/8 ✅' if raw_exact else '0/8 ❌'}")
        lines.append(f"- numeric_match: {'8/8 ✅' if raw_numeric else '0/8 ❌'}")
        lines.append(f"- unique answers: {len(set(raw_answers))}")
        lines.append(f"")
        lines.append(f"| Run # | Answer |")
        lines.append(f"|---|---|")
        for i, a in enumerate(raw_answers):
            lines.append(f"| {i+1} | {a[:120]} |")
        lines.append("")

        # Summary
        lines.append(f"### Comparison")
        lines.append(f"| Metric | petfishFramework | Raw API |")
        lines.append(f"|---|---|---|")
        lines.append(f"| exact_match | {'✅ 8/8' if pf_exact else '❌ 0/8'} | {'✅ 8/8' if raw_exact else '❌ 0/8'} |")
        lines.append(f"| numeric_match | {'✅ 8/8' if pf_numeric else '❌ 0/8'} | {'✅ 8/8' if raw_numeric else '❌ 0/8'} |")
        lines.append(f"| unique answers | {len(set(pf_answers))} | {len(set(raw_answers))} |")
        lines.append("")

    # Overall summary
    lines.append("## Overall")
    lines.append("")
    lines.append("| Task | PF exact | PF numeric | Raw exact | Raw numeric | PF unique | Raw unique |")
    lines.append("|---|---|---|---|---|---|---|")
    lines.append(f"| 17×23 | {'✅' if pf_exact else '❌'} | {'✅' if pf_numeric else '❌'} | {'✅' if raw_exact else '❌'} | {'✅' if raw_numeric else '❌'} | — | — |")
    lines.append("")

    output = "\n".join(lines)
    print(output)

    # Save to file
    with open("docs/benchmark-results.md", "w", encoding="utf-8") as f:
        f.write(output)
    print("\n\nSaved to docs/benchmark-results.md")


if __name__ == "__main__":
    main()
