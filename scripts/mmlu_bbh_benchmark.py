#!/usr/bin/env python
"""MMLU + BBH Benchmark — petfishFramework vs Raw API.

Downloads small subsets of MMLU (multiple choice) and BBH (reasoning),
runs them through both PF and Raw API, reports accuracy + consistency.

Usage: uv run python scripts/mmlu_bbh_benchmark.py
"""
from __future__ import annotations

import csv
import io
import json
import os
import random
import re
import sys
import urllib.request


def download_mmlu_subjects(n_total: int = 90) -> list[dict]:
    """Download MMLU test questions from HuggingFace datasets server."""
    url = f"https://datasets-server.huggingface.co/rows?dataset=cais/mmlu&config=all&split=test&offset=0&limit={n_total}"
    try:
        resp = urllib.request.urlopen(url, timeout=30)
        data = json.loads(resp.read().decode())
        rows = data.get("rows", [])
        all_q = []
        for r in rows:
            row = r["row"]
            all_q.append({
                "subject": row.get("subject", "unknown"),
                "question": row["question"],
                "choices": row["choices"],
                "answer": row["answer"],
            })
        print(f"  MMLU: downloaded {len(all_q)} questions from {len(set(q['subject'] for q in all_q))} subjects")
        return all_q
    except Exception as e:
        print(f"  MMLU: FAILED ({e})")
        return []


def download_bbh_tasks(tasks: list[str], n_per_task: int = 10) -> list[dict]:
    """Download BBH JSON files and sample questions."""
    base = "https://raw.githubusercontent.com/suzgunmirac/BIG-Bench-Hard/main/bbh"
    all_q = []
    for task in tasks:
        url = f"{base}/{task}.json"
        try:
            resp = urllib.request.urlopen(url, timeout=15)
            data = json.loads(resp.read().decode())
            examples = data.get("examples", [])
            sampled = random.sample(examples, min(n_per_task, len(examples)))
            for ex in sampled:
                all_q.append({
                    "task": task,
                    "input": ex["input"],
                    "target": ex["target"],
                })
            print(f"  BBH {task}: {len(examples)} total, sampled {min(n_per_task, len(examples))}")
        except Exception as e:
            print(f"  BBH {task}: FAILED ({e})")
    return all_q


def run_mmlu_benchmark(questions: list[dict], model_name: str, api_key: str, base_url: str | None) -> None:
    """Run MMLU questions through PF and Raw API, compare accuracy."""
    from dotenv import load_dotenv
    load_dotenv()

    from petfishframework import Agent, ReAct
    from petfishframework.models.openai import OpenAIModel

    model = OpenAIModel(model=model_name)
    agent = Agent(model=model, reasoning=ReAct())

    import openai
    raw_client = openai.OpenAI(base_url=base_url)

    pf_correct = 0
    raw_correct = 0
    pf_answers = []
    raw_answers = []
    total = len(questions)

    print(f"\n{'='*60}")
    print(f"MMLU Benchmark — {total} questions | Model: {model_name}")
    print(f"{'='*60}")

    for i, q in enumerate(questions):
        choices_str = "\n".join(f"{chr(65+j)}) {c}" for j, c in enumerate(q["choices"]))
        prompt = f"Question: {q['question']}\n{choices_str}\n\nAnswer with ONLY the letter (A, B, C, or D)."
        correct_letter = chr(65 + q["answer"])

        # PF
        try:
            pf_result = agent.run(prompt)
            pf_ans = pf_result.answer.strip().upper()[:1]
        except Exception:
            pf_ans = "?"
        pf_is_correct = pf_ans == correct_letter
        pf_correct += pf_is_correct
        pf_answers.append(pf_ans)

        # Raw
        try:
            raw_resp = raw_client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            raw_text = (raw_resp.choices[0].message.content or "").strip()
            raw_match = re.search(r"[ABCD]", raw_text.upper())
            raw_ans = raw_match.group(0) if raw_match else "?"
        except Exception:
            raw_ans = "?"
        raw_is_correct = raw_ans == correct_letter
        raw_correct += raw_is_correct
        raw_answers.append(raw_ans)

        if (i + 1) % 10 == 0:
            print(f"  [{i+1}/{total}] PF: {pf_correct}/{i+1} ({pf_correct*100//(i+1)}%) | Raw: {raw_correct}/{i+1} ({raw_correct*100//(i+1)}%)")

    pf_acc = pf_correct / total * 100
    raw_acc = raw_correct / total * 100
    pf_unique = len(set(pf_answers))
    raw_unique = len(set(raw_answers))

    print(f"\nMMLU Results ({total} questions):")
    print(f"  PF accuracy:  {pf_correct}/{total} ({pf_acc:.1f}%)")
    print(f"  Raw accuracy: {raw_correct}/{total} ({raw_acc:.1f}%)")
    print(f"  PF answer distribution:  {sorted(set(pf_answers))} ({pf_unique} unique)")
    print(f"  Raw answer distribution: {sorted(set(raw_answers))} ({raw_unique} unique)")


def run_bbh_benchmark(questions: list[dict], model_name: str, api_key: str, base_url: str | None) -> None:
    """Run BBH questions through PF and Raw API, compare accuracy."""
    from dotenv import load_dotenv
    load_dotenv()

    from petfishframework import Agent, ReAct
    from petfishframework.models.openai import OpenAIModel

    model = OpenAIModel(model=model_name)
    agent = Agent(model=model, reasoning=ReAct())

    import openai
    raw_client = openai.OpenAI(base_url=base_url)

    pf_correct = 0
    raw_correct = 0
    total = len(questions)

    print(f"\n{'='*60}")
    print(f"BBH Benchmark — {total} questions | Model: {model_name}")
    print(f"{'='*60}")

    for i, q in enumerate(questions):
        prompt = f"{q['input']}\n\nGive your final answer after 'Final answer:'"
        target = q["target"].strip()

        # PF
        try:
            pf_result = agent.run(prompt)
            pf_text = pf_result.answer.strip()
        except Exception:
            pf_text = ""
        pf_is_correct = target.lower() in pf_text.lower()
        pf_correct += pf_is_correct

        # Raw
        try:
            raw_resp = raw_client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            raw_text = (raw_resp.choices[0].message.content or "").strip()
        except Exception:
            raw_text = ""
        raw_is_correct = target.lower() in raw_text.lower()
        raw_correct += raw_is_correct

        if (i + 1) % 5 == 0:
            print(f"  [{i+1}/{total}] PF: {pf_correct}/{i+1} | Raw: {raw_correct}/{i+1}")

    pf_acc = pf_correct / total * 100
    raw_acc = raw_correct / total * 100

    print(f"\nBBH Results ({total} questions):")
    print(f"  PF accuracy:  {pf_correct}/{total} ({pf_acc:.1f}%)")
    print(f"  Raw accuracy: {raw_correct}/{total} ({raw_acc:.1f}%)")


def main() -> None:
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set.")
        sys.exit(1)

    model_name = os.environ.get("BENCHMARK_MODEL", "gpt-4o-mini")
    base_url = os.environ.get("OPENAI_BASE_URL")
    random.seed(42)  # reproducible sampling

    # Download MMLU — diverse subjects
    print("Downloading MMLU data...")
    mmlu_questions = download_mmlu_subjects(n_total=30)

    # Download BBH — diverse reasoning tasks
    print("\nDownloading BBH data...")
    bbh_tasks = [
        "boolean_expressions", "date_understanding", "word_sorting",
        "tracking_shuffled_objects_three_objects", "logical_deduction_three_objects",
    ]
    bbh_questions = download_bbh_tasks(bbh_tasks, n_per_task=6)

    if mmlu_questions:
        run_mmlu_benchmark(mmlu_questions, model_name, api_key, base_url)

    if bbh_questions:
        run_bbh_benchmark(bbh_questions, model_name, api_key, base_url)

    print(f"\n{'='*60}")
    print("Done.")


if __name__ == "__main__":
    main()
