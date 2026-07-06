"""Minimal Tier 1 proof — 2 MMLU + 1 arithmetic."""
from __future__ import annotations

import json
import os
import re
import urllib.request
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class MCQAnswer:
    answer: str


def main() -> None:
    from petfishframework import Agent, ReAct
    from petfishframework.models.openai import OpenAIModel
    from petfishframework.tools.calculator import Calculator
    import openai

    m = os.environ.get("BENCHMARK_MODEL", "gpt-4o-mini")
    model = OpenAIModel(model=m)
    raw = openai.OpenAI(base_url=os.environ.get("OPENAI_BASE_URL"))

    # Download 2 MMLU questions
    url = "https://datasets-server.huggingface.co/rows?dataset=cais/mmlu&config=all&split=test&offset=0&limit=2"
    resp = urllib.request.urlopen(url, timeout=30)
    qs = [r["row"] for r in json.loads(resp.read().decode()).get("rows", [])]

    print(f"Tier 1 Mini | {m}")
    print("=" * 50)

    # MMLU: PF structured vs Raw regex
    print("\n[1] MMLU (run_structured — zero regex for PF):")
    for i, q in enumerate(qs):
        choices = "\n".join(f"{chr(65+j)}) {c}" for j, c in enumerate(q["choices"]))
        correct = chr(65 + q["answer"])
        prompt = q["question"] + "\n" + choices + "\n\nWhich option is correct?"

        agent = Agent(model=model, reasoning=ReAct())
        result = agent.run_structured(prompt, MCQAnswer)
        pf = result.data.answer[:1].upper() if result.data and result.data.answer else "?"

        raw_r = raw.chat.completions.create(model=m, messages=[{"role": "user", "content": prompt}], temperature=0.0)
        raw_match = re.search(r"[ABCD]", (raw_r.choices[0].message.content or "").upper())
        raw_letter = raw_match.group(0) if raw_match else "?"

        pf_ok = "OK" if pf == correct else "MISS"
        print(f"  Q{i+1}: PF={pf}(structured,{pf_ok}) Raw={raw_letter}(regex) Correct={correct}")

    # Arithmetic: Calculator tool — exact match
    print("\n[2] Arithmetic (Calculator tool — exact match, zero regex):")
    agent2 = Agent(model=model, reasoning=ReAct(), tools=(Calculator(),))
    r = agent2.run("What is 17 * 23? Use the calculator.")
    pf_exact = r.answer.strip() == "391"
    print(f"  PF:  {r.answer!r}  exact_match={pf_exact}")

    raw_r = raw.chat.completions.create(model=m, messages=[{"role": "user", "content": "What is 17 * 23?"}], temperature=0.0)
    raw_text = (raw_r.choices[0].message.content or "").strip()
    print(f"  Raw: {raw_text[:60]!r}")

    print("\n[3] Scoring method comparison:")
    print("  PF MMLU:  result.data.answer == correct  (zero regex)")
    print("  Raw MMLU: re.search(r'[ABCD]', text)     (regex needed)")
    print("  PF Arith: result.answer == '391'          (zero regex)")
    print("  Raw Arith: '391' in text                  (substring needed)")


if __name__ == "__main__":
    main()
