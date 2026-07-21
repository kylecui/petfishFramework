"""Quick MMLU benchmark — 10 questions, minimal API calls."""
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

    # Download 10 MMLU questions via HuggingFace API
    url = "https://datasets-server.huggingface.co/rows?dataset=cais/mmlu&config=all&split=test&offset=0&limit=10"
    resp = urllib.request.urlopen(url, timeout=30)
    data = json.loads(resp.read().decode())
    questions = [r["row"] for r in data.get("rows", [])]
    print(f"Downloaded {len(questions)} MMLU questions")
    print(f"Subjects: {set(q['subject'] for q in questions)}")

    import openai

    from petfishframework import Agent, ReAct
    from petfishframework.models.openai import OpenAIModel

    model_name = os.environ.get("BENCHMARK_MODEL", "gpt-4o-mini")
    model = OpenAIModel(model=model_name)
    agent = Agent(model=model, reasoning=ReAct())
    raw_client = openai.OpenAI(base_url=os.environ.get("OPENAI_BASE_URL"))

    pf_correct = 0
    raw_correct = 0
    total = len(questions)

    print(f"\nMMLU Benchmark | {model_name}")
    print("=" * 50)

    for i, q in enumerate(questions):
        choices_str = "\n".join(f"{chr(65+j)}) {c}" for j, c in enumerate(q["choices"]))
        prompt = f"Question: {q['question']}\n{choices_str}\n\nAnswer with ONLY the letter (A, B, C, or D)."
        correct_letter = chr(65 + q["answer"])

        # PF
        try:
            pf_r = agent.run(prompt)
            pf_letter = pf_r.answer.strip().upper()[:1]
        except Exception:
            pf_letter = "?"
        pf_ok = pf_letter == correct_letter
        pf_correct += pf_ok

        # Raw
        try:
            raw_r = raw_client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            raw_text = (raw_r.choices[0].message.content or "").strip()
            raw_match = re.search(r"[ABCD]", raw_text.upper())
            raw_letter = raw_match.group(0) if raw_match else "?"
        except Exception:
            raw_letter = "?"
        raw_ok = raw_letter == correct_letter
        raw_correct += raw_ok

        mark = "✅" if pf_ok else "❌"
        print(f"  [{i+1}/{total}] PF:{pf_letter} Raw:{raw_letter} Correct:{correct_letter} {mark} ({q['subject']})")

    print(f"\n{'='*50}")
    print(f"MMLU Results ({total} questions):")
    print(f"  PF accuracy:  {pf_correct}/{total} ({pf_correct*100//total}%)")
    print(f"  Raw accuracy: {raw_correct}/{total} ({raw_correct*100//total}%)")


if __name__ == "__main__":
    main()
