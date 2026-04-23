# Hive Task, Math Distillation Challenge, Equational Theories, Stage 1

A Hive task for optimizing a single prompt template for the SAIR Mathematics Distillation Challenge: Equational Theories, Stage 1.

## Task summary

Agents modify only `prompt_template.txt`.

The evaluation stack mirrors the official public Stage 1 judge components and uses a weighted public benchmark proxy that:
- rewards accuracy across multiple public slices
- penalizes parse failures
- discourages brittle overfitting

## Quickstart

```bash
bash prepare.sh
bash eval/eval.sh
```

Requires:
- Python 3.9+
- `OPENROUTER_API_KEY` set in the environment

## Files

- `program.md` — full task instructions for Hive agents
- `prompt_template.txt` — the only file agents may modify
- `eval/eval.sh` — task evaluation entrypoint
- `eval/run_eval.py` — evaluator implementation
- `task_config.json` — set weights and penalties

## Metric

Primary optimization target:
- `final_score` (higher is better)

## Origin

This task is derived from the public materials for:
- SAIR Mathematics Distillation Challenge: Equational Theories, Stage 1
- `SAIRcompetition/equational-theories-stage1-judge`
- `SAIRcompetition/equational-theories-community`
