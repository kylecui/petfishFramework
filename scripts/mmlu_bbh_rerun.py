"""Re-run MMLU (fixed extraction) + BBH word_sorting (with WordSorter tool)."""
from __future__ import annotations

import json
import os
import random
import re
import urllib.request

from dotenv import load_dotenv

load_dotenv()


def extract_letter(text: str) -> str:
    """Extract A/B/C/D from response — finds LAST standalone letter, not first char."""
    matches = re.findall(r"\b([ABCD])\b", text.upper())
    return matches[-1] if matches else "?"


def main() -> None:
    random.seed(42)
    model_name = os.environ.get("BENCHMARK_MODEL", "gpt-4o-mini")

    from petfishframework import Agent, ReAct
    from petfishframework.models.openai import OpenAIModel
    from petfishframework.tools.calculator import Calculator
    from petfishframework.tools.word_sorter import WordSorter
    import openai

    model = OpenAIModel(model=model_name)
    raw_client = openai.OpenAI(base_url=os.environ.get("OPENAI_BASE_URL"))

    # ── MMLU with fixed extraction ──────────────────────────────────
    print("=" * 60)
    print("MMLU (fixed extraction) |", model_name)
    print("=" * 60)

    url = "https://datasets-server.huggingface.co/rows?dataset=cais/mmlu&config=all&split=test&offset=0&limit=30"
    resp = urllib.request.urlopen(url, timeout=30)
    mmlu = [r["row"] for r in json.loads(resp.read().decode()).get("rows", [])]

    pf_correct = 0
    raw_correct = 0
    for i, q in enumerate(mmlu):
        choices = "\n".join(f"{chr(65+j)}) {c}" for j, c in enumerate(q["choices"]))
        prompt = f"Question: {q['question']}\n{choices}\n\nAnswer with ONLY the letter (A, B, C, or D)."
        correct = chr(65 + q["answer"])

        agent = Agent(model=model, reasoning=ReAct())
        try:
            pf_text = agent.run(prompt).answer
        except Exception:
            pf_text = ""
        pf_letter = extract_letter(pf_text)
        pf_ok = pf_letter == correct
        pf_correct += pf_ok

        try:
            raw_r = raw_client.chat.completions.create(
                model=model_name, messages=[{"role": "user", "content": prompt}], temperature=0.0
            )
            raw_text = (raw_r.choices[0].message.content or "")
        except Exception:
            raw_text = ""
        raw_letter = extract_letter(raw_text)
        raw_ok = raw_letter == correct
        raw_correct += raw_ok

        if pf_ok != raw_ok or pf_letter == "?":
            print(f"  [{i+1}] PF:{pf_letter} Raw:{raw_letter} Correct:{correct} | PF_text={pf_text[:50]!r}")

    print(f"\nMMLU ({len(mmlu)} questions, fixed extraction):")
    print(f"  PF:  {pf_correct}/{len(mmlu)} ({pf_correct*100//len(mmlu)}%)")
    print(f"  Raw: {raw_correct}/{len(mmlu)} ({raw_correct*100//len(mmlu)}%)")

    # ── BBH word_sorting with WordSorter tool ────────────────────────
    print(f"\n{'='*60}")
    print("BBH word_sorting (with WordSorter tool) |", model_name)
    print("=" * 60)

    url2 = "https://raw.githubusercontent.com/suzgunmirac/BIG-Bench-Hard/main/bbh/word_sorting.json"
    data = json.loads(urllib.request.urlopen(url2, timeout=15).read().decode())
    sort_q = random.sample(data["examples"], 5)

    # PF with WordSorter
    sort_agent = Agent(model=model, reasoning=ReAct(), tools=(WordSorter(),))
    pf_sort_correct = 0
    raw_sort_correct = 0

    for i, q in enumerate(sort_q):
        target = q["target"].strip().lower()
        prompt = q["input"] + "\n\nUse the word_sorter tool to sort the words."

        try:
            pf_r = sort_agent.run(prompt)
            pf_text = pf_r.answer.strip().lower()
        except Exception:
            pf_text = ""
        pf_ok = target in pf_text
        pf_sort_correct += pf_ok

        try:
            raw_r = raw_client.chat.completions.create(
                model=model_name, messages=[{"role": "user", "content": prompt}], temperature=0.0
            )
            raw_text = (raw_r.choices[0].message.content or "").strip().lower()
        except Exception:
            raw_text = ""
        raw_ok = target in raw_text
        raw_sort_correct += raw_ok

        print(f"  [{i+1}] PF:{pf_ok} Raw:{raw_ok} | target={target[:40]}...")
        print(f"       PF={pf_text[:60]}")

    print(f"\nword_sorting (5 questions, with WordSorter tool):")
    print(f"  PF:  {pf_sort_correct}/5 ({pf_sort_correct*20}%)")
    print(f"  Raw: {raw_sort_correct}/5 ({raw_sort_correct*20}%)")


if __name__ == "__main__":
    main()
