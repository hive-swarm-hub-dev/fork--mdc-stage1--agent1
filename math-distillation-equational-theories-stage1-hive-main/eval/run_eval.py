#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from judge import judge_response
from llm import LlmError, call_llm
from models import load_models, resolve
from prompt import render_prompt


@dataclass
class CallRecord:
    model: str
    problem_set: str
    problem_id: str
    expected_answer: bool
    correct: bool | None
    parseable: bool
    finish_reason: str | None
    actual_provider: str | None
    reason: str
    response_text: str | None = None
    error: str | None = None


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_task_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def slice_problems(entries: list[dict[str, Any]], offset: int = 0, limit: int | None = None) -> list[dict[str, Any]]:
    if offset:
        entries = entries[offset:]
    if limit is not None:
        entries = entries[:limit]
    return entries


async def evaluate(args: argparse.Namespace) -> int:
    import os

    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        print(f"Missing API key: set {args.api_key_env}", file=sys.stderr)
        return 2

    config = load_task_config(args.task_config)
    model_cfgs = load_models(args.model_file)
    prompt_template = args.prompt_file.read_text(encoding="utf-8")

    selected_models = args.models or config["model_aliases"]
    unknown = [m for m in selected_models if m not in model_cfgs]
    if unknown:
        print(f"Unknown model alias(es): {', '.join(unknown)}", file=sys.stderr)
        return 2

    set_defs = config["problem_sets"]
    selected_sets = args.problem_sets or list(set_defs.keys())
    unknown_sets = [s for s in selected_sets if s not in set_defs]
    if unknown_sets:
        print(f"Unknown problem set(s): {', '.join(unknown_sets)}", file=sys.stderr)
        return 2

    all_problem_sets: dict[str, list[dict[str, Any]]] = {}
    for set_name in selected_sets:
        entry = set_defs[set_name]
        raw = load_jsonl(REPO_ROOT / entry["path"])
        problems = slice_problems(raw, offset=entry.get("offset", 0), limit=entry.get("limit"))
        all_problem_sets[set_name] = problems

    records: list[CallRecord] = []
    call_timeout = args.call_timeout if args.call_timeout and args.call_timeout > 0 else None

    async with httpx.AsyncClient(timeout=args.timeout) as client:
        for model_alias in selected_models:
            model_entry = model_cfgs[model_alias]
            provider_name, provider_config, kwargs = resolve(model_entry, api_keys=[api_key])
            if args.max_tokens is not None:
                kwargs.max_tokens = min(args.max_tokens, kwargs.max_tokens or args.max_tokens)

            for set_name, problems in all_problem_sets.items():
                for problem in problems:
                    prompt_text = render_prompt(prompt_template, problem["equation1"], problem["equation2"])
                    try:
                        call = call_llm(
                            client,
                            provider_name=provider_name,
                            provider_config=provider_config,
                            model_id=model_entry.model_id,
                            prompt=prompt_text,
                            kwargs=kwargs,
                        )
                        response = await asyncio.wait_for(call, timeout=call_timeout) if call_timeout is not None else await call
                        correct, reason = judge_response(response.text, expected_answer=problem["answer"])
                        records.append(
                            CallRecord(
                                model=model_alias,
                                problem_set=set_name,
                                problem_id=problem["id"],
                                expected_answer=problem["answer"],
                                correct=correct,
                                parseable=correct is not None,
                                finish_reason=response.finish_reason,
                                actual_provider=response.actual_provider,
                                reason=reason,
                                response_text=None if args.hide_response else response.text,
                            )
                        )
                    except asyncio.TimeoutError:
                        records.append(
                            CallRecord(
                                model=model_alias,
                                problem_set=set_name,
                                problem_id=problem["id"],
                                expected_answer=problem["answer"],
                                correct=None,
                                parseable=False,
                                finish_reason=None,
                                actual_provider=None,
                                reason=f"timeout>{call_timeout}s",
                                error="TimeoutError",
                            )
                        )
                    except LlmError as exc:
                        records.append(
                            CallRecord(
                                model=model_alias,
                                problem_set=set_name,
                                problem_id=problem["id"],
                                expected_answer=problem["answer"],
                                correct=None,
                                parseable=False,
                                finish_reason=None,
                                actual_provider=None,
                                reason=str(exc),
                                error=type(exc).__name__,
                            )
                        )

    penalties = config["penalties"]
    summary: dict[str, Any] = {"models": {}, "problem_sets": {}, "records": []}

    for r in records:
        summary["records"].append(
            {
                "model": r.model,
                "problem_set": r.problem_set,
                "problem_id": r.problem_id,
                "expected_answer": r.expected_answer,
                "correct": r.correct,
                "parseable": r.parseable,
                "finish_reason": r.finish_reason,
                "actual_provider": r.actual_provider,
                "reason": r.reason,
                **({} if r.response_text is None else {"response_text": r.response_text}),
                **({} if r.error is None else {"error": r.error}),
            }
        )

    weighted_acc_total = 0.0
    weight_total = 0.0
    parse_rates: list[float] = []

    for set_name in selected_sets:
        rows = [r for r in records if r.problem_set == set_name]
        correct_n = sum(1 for r in rows if r.correct is True)
        parseable_n = sum(1 for r in rows if r.parseable)
        total_n = len(rows)
        acc = (correct_n / total_n) if total_n else 0.0
        parse_rate = (parseable_n / total_n) if total_n else 0.0
        weight = float(set_defs[set_name]["weight"])
        weighted_acc_total += weight * acc
        weight_total += weight
        parse_rates.append(parse_rate)
        summary["problem_sets"][set_name] = {
            "accuracy": acc,
            "parse_rate": parse_rate,
            "correct": correct_n,
            "total": total_n,
            "weight": weight,
        }

    for model_alias in selected_models:
        rows = [r for r in records if r.model == model_alias]
        correct_n = sum(1 for r in rows if r.correct is True)
        parseable_n = sum(1 for r in rows if r.parseable)
        total_n = len(rows)
        summary["models"][model_alias] = {
            "accuracy": (correct_n / total_n) if total_n else 0.0,
            "parse_rate": (parseable_n / total_n) if total_n else 0.0,
            "correct": correct_n,
            "total": total_n,
        }

    weighted_accuracy = weighted_acc_total / weight_total if weight_total else 0.0
    mean_parse_rate = statistics.mean(parse_rates) if parse_rates else 0.0
    parse_penalty = penalties["parse_failure_weight"] * (1.0 - mean_parse_rate)
    final_score = weighted_accuracy - parse_penalty

    out = {
        "weighted_accuracy": weighted_accuracy,
        "mean_parse_rate": mean_parse_rate,
        "parse_penalty": parse_penalty,
        "cost_penalty": 0.0,
        "latency_penalty": 0.0,
        "final_score": final_score,
        "details": summary,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Hive eval for the math distillation prompt task.")
    parser.add_argument("--prompt-file", type=Path, default=REPO_ROOT / "prompt_template.txt")
    parser.add_argument("--task-config", type=Path, default=REPO_ROOT / "task_config.json")
    parser.add_argument("--model-file", type=Path, default=REPO_ROOT / "evaluation_models.json")
    parser.add_argument("--models", nargs="*")
    parser.add_argument("--problem-sets", nargs="*")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "eval" / "last_result.json")
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--call-timeout", type=float, default=240.0)
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--api-key-env", default="OPENROUTER_API_KEY")
    parser.add_argument("--hide-response", action="store_true")
    return parser


def main() -> int:
    return asyncio.run(evaluate(build_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
