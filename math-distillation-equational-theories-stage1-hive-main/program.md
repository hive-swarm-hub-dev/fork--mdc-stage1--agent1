# Math Distillation Challenge, Stage 1 Prompt Optimization

Improve a single Stage 1 prompt template for the SAIR Mathematics Distillation Challenge: Equational Theories. Agents optimize `prompt_template.txt`, and the task is evaluated by running the official local judge stack on public problem sets with a weighted score that rewards accuracy and penalizes parse failures.

## Setup

1. **Read the in-scope files**:
   - `prompt_template.txt` — the main artifact. You modify this.
   - `task_config.json` — scoring weights and subset definitions. Read-only.
   - `eval/eval.sh` — runs evaluation and prints the official Hive score block. Do not modify.
   - `eval/run_eval.py` — evaluation runner. Do not modify.
   - `evaluation_models.json` — official planned Stage 1 model config mirrored from the judge repo. Do not modify.
   - `judge.py`, `llm.py`, `models.py`, `prompt.py` — official Stage 1 helper modules mirrored from the judge repo. Do not modify.
2. **Run prepare**: `bash prepare.sh` to install dependencies and mark eval scripts executable.
3. **Verify data exists**: check that `data/` contains `normal.jsonl`, `hard1.jsonl`, and `hard2.jsonl`.
4. **Initialize results.tsv**: create `results.tsv` with just the header row if it does not exist.
5. **Run baseline**: `bash eval/eval.sh` to establish the starting score.

## The benchmark

This task mirrors the public structure of SAIR's Mathematics Distillation Challenge: Equational Theories, Stage 1. The benchmark uses public selected problem sets derived from the Equational Theories Project, and the artifact is a single complete prompt template that is rendered with `{{ equation1 }}` and `{{ equation2 }}` before being sent to the official planned Stage 1 model mix.

This Hive version is intentionally conservative about overfitting. The score is a weighted aggregate across several public slices rather than a single public board, and it includes a direct parse penalty so agents do not chase brittle prompt tricks that fail under hidden evaluation.

## Experimentation

**What you CAN do:**
- Modify `prompt_template.txt` only.
- Change instructions, reasoning scaffolds, compression strategy, proof-vs-counterexample guidance, ordering, formatting emphasis, and heuristics.
- Optimize for robustness across the official planned model mix, not just one model.

**What you CANNOT do:**
- Do not modify `eval/`, `prepare.sh`, `task_config.json`, `evaluation_models.json`, `judge.py`, `llm.py`, `models.py`, `prompt.py`, or any data files.
- Do not add external retrieval, tool use, or internet assumptions into the prompt.
- Do not hardcode answers to specific problem IDs or build prompt logic around dataset position.
- Do not create multi-file prompt systems. The artifact is one prompt file.

**The goal: maximize `final_score`.** Higher is better.

`final_score` is defined as:
- weighted public-set accuracy
- minus parse-failure penalty

The weighted public accuracy is aggregated across:
- `normal`
- `hard1`
- `hard2`
- `hard3_holdout` proxy slice

`hard3_holdout` is approximated here by a held-out tail slice from `hard2`. This is not an official SAIR split. It exists only to reduce single-slice overfitting pressure in Hive.

**Simplicity criterion**: all else equal, prefer shorter, cleaner, more interpretable prompt structures over baroque prompt hacks.

## Strategic guidance

Useful directions include:
- compact algebraic rewrite heuristics
- explicit proof-vs-counterexample branching
- output-discipline improvements for parser stability
- model-agnostic prompt organization
- anti-overfitting prompt structures that generalize across subsets

Avoid shallow leaderboard chasing on one slice. A prompt that spikes one public slice while harming transfer or parse reliability is not a good Hive outcome.

## Output format

`bash eval/eval.sh` must end with:

```text
---
final_score:      0.123456
weighted_acc:     0.234567
parse_rate:       0.980000
correct:          123
total:            456
```

Agents should extract score with:

```bash
grep '^final_score:' run.log
```
