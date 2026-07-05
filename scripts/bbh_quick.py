"""Quick BBH benchmark — 25 questions, CoT prompt fix verification."""
from __future__ import annotations

import json
import os
import random
import re
import urllib.request

from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    random.seed(42)

    tasks = [
        "boolean_expressions", "date_understanding", "word_sorting",
        "tracking_shuffled_objects_three_objects", "logical_deduction_three_objects",
    ]
    bbh: list[dict] = []
    for t in tasks:
        url = f"https://raw.githubusercontent.com/suzgunmirac/BIG-Bench-Hard/main/bbh/{t}.json"
        data = json.loads(urllib.request.urlopen(url, timeout=15).read().decode())
        sampled = random.sample(data["examples"], min(5, len(data["examples"])))
        for ex in sampled:
            bbh.append({"task": t, "input": ex["input"], "target": ex["target"].strip()})
        print(f"{t}: {len(sampled)} sampled")

    total = len(bbh)
    print(f"\nTotal: {total} questions")

    from petfishframework import Agent, ReAct
    from petfishframework.models.openai import OpenAIModel
    import openai

    model_name = os.environ.get("BENCHMARK_MODEL", "gpt-4o-mini")
    model = OpenAIModel(model=model_name)
    agent = Agent(model=model, reasoning=ReAct())
    raw_client = openai.OpenAI(base_url=os.environ.get("OPENAI_BASE_URL"))

    pf_correct = 0
    raw_correct = 0

    print(f"\nBBH CoT Benchmark | {model_name}")
    print("=" * 50)

    for i, q in enumerate(bbh):
        prompt = q["input"] + "\n\nGive your final answer after 'Final answer:'"
        target = q["target"].lower()

        # PF
        try:
            pf_r = agent.run(prompt)
            pf_text = pf_r.answer.strip()
        except Exception:
            pf_text = ""
        pf_ok = target in pf_text.lower()
        pf_correct += pf_ok

        # Raw
        try:
            raw_r = raw_client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            raw_text = (raw_r.choices[0].message.content or "").strip()
        except Exception:
            raw_text = ""
        raw_ok = target in raw_text.lower()
        raw_correct += raw_ok

        mark = "✅" if pf_ok else "❌"
        print(f"  [{i+1}/{total}] PF:{pf_ok} Raw:{raw_ok} {mark} target={q['target'][:25]}")

    print(f"\n{'='*50}")
    print(f"BBH Results ({total} questions, CoT prompt):")
    print(f"  PF accuracy:  {pf_correct}/{total} ({pf_correct*100//total}%)")
    print(f"  Raw accuracy: {raw_correct}/{total} ({raw_correct*100//total}%)")


if __name__ == "__main__":
    main()
