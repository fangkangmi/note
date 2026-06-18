# Skill-vs-No-Skill Code-Review Evaluation Workflow

Goal: measure what a code-review **skill** actually changes, by reviewing real PRs
**with** the skill and **without** it, k times each, then **confirming** findings against
ground truth. Output is a per-condition scorecard, not anecdotes.

## Parameters
- `REPO` — internal repo
- `SKILL` — the review skill under test (its SKILL.md + every file it references: rules/, checklists, CLAUDE.md/AGENTS.md)
- `PRS` — selected PRs (see Phase B)
- `K` — repeats per cell (≥3; 5–10 for real rates) — your pipeline supplies the loop
- `MODEL`, `TEMPERATURE` — held identical across conditions
- `CONDITIONS = { without_skill, with_skill }`
- `STABILITY_THRESHOLD` — e.g. finding counts as "stable" if it appears in ≥0.6·K runs

## The one rule that makes this valid
**Isolate exactly one variable.** Same model, temperature, diff, instructions, and output
format in both conditions. The *only* difference is whether the skill bundle is injected.

---

## Phase A — Extract the skill's checkable knowledge
1. Resolve the skill into one **bundle**: SKILL.md + all referenced rule/checklist/convention files.
2. Enumerate its **concrete, checkable rules** (each becomes a "signal"), e.g.
   "no raw SQL interpolation", "soft-delete filter on joins", "no new class-based services",
   "logger not console", "index large-table filters". Note its **"do-NOT-flag"** list too —
   you will test calibration against it.

## Phase B — Select skill-RELEVANT PRs (do not pick blind)
Picking PRs at random produces no signal. For each candidate PR diff, scan **added lines**
for patterns that map to the skill's rules (one regex/heuristic per rule). Keep PRs that hit
≥1 signal, and spread selection so the set **covers multiple rules**.
- **Best PRs = ground-truth bug-fixes:** take a `fix:` PR, review the **pre-fix** code
  (strip the fix). The merged fix/tests are your objective oracle for "was the real bug caught?"
- Record, per PR, which rule(s) it exercises.

## Phase C — Build the isolated harness
- Two prompt templates, identical except the skill block (see Appendix).
- **Compact, structured output** — one line per finding:
  `SEVERITY | short-title (<=9 words) | cited-rule | file:line`.
  Without this, aggregating k·2·|PRS| reviews is intractable.
- For ground-truth PRs, feed the pre-fix snapshot, not the diff.

## Phase D — Run the matrix (k times)
For every `pr × condition`, run the review `K` times as **independent** samples
(your internal pipeline's k-runner). Total reviews = `|PRS| × 2 × K`.

## Phase E — Aggregate / tally
- **Canonicalize** findings: cluster by (file, rule, semantic title).
- Compute **reproduction frequency** `f = hits/K` per finding, per condition.
- Split **stable** (`f ≥ STABILITY_THRESHOLD`) vs **flaky**. Flaky = noise; report but discount.

## Phase F — CONFIRM against ground truth  ← the non-skippable step
**Stability ≠ correctness.** A wrong finding can reproduce K/K. For every **stable** finding,
verify against the actual code and classify `TRUE_POSITIVE | FALSE_POSITIVE`:
- Automatable checks first: does the column/index/endpoint/contract it references actually
  exist? (grep the schema/migrations; check the sibling function it claims to contradict).
- Then an **independent verifier agent** (adversarial: *"refute this finding using the repo;
  default to FALSE_POSITIVE if you can't prove it"*).
- For ground-truth PRs: did the review catch the **known** bug the fix addressed? (recall).

## Phase G — Score & compare (per condition)
- **Ground-truth recall** — % of known bug-fix PRs where the real bug was caught (best metric).
- **Confirmed true positives** — count of stable findings verified real.
- **False-positive rate** — confirmed-wrong / total stable. (Skills can *raise* this.)
- **Unique coverage** — confirmed-real findings only this condition produced.
- **Calibration** — # of "do-NOT-flag" items wrongly flagged (lower = better).
- **Noise** — low-value nits per review.

**Skill value ≈ (Δ unique confirmed-real findings) − (Δ false positives) − (Δ real off-checklist bugs missed).**
Recommend "run both + merge" unless one condition strictly dominates on every metric.

---

## Failure modes to measure explicitly (observed in this study)
1. **Convention-shaped false positives** — the skill demands a pattern where it doesn't apply
   (e.g. "add `deletedAt IS NULL`" on a table that has no soft-delete column), reproducibly.
2. **Tunnel vision** — the skill narrows attention to its checklist and **stably misses** real
   bugs outside it that the unguided model catches.
3. **Distraction on deep bugs** — on logic bugs, an over-specific skill can anchor the model and
   make it *miss* a defect it would otherwise find.
→ Your scorecard must reward off-checklist real-bug recall, or you'll over-credit the skill.

## Gotchas
- k ≥ 3, and always report the rate **with K** ("3/3", "7/10"), never a bare checkmark.
- Confirm BOTH conditions — the unguided model also emits stable false positives.
- If results feed an external/published artifact, check the repo license; internal-only is fine.

---

## Appendix — prompt templates (only difference is the SKILL block)

WITHOUT skill:
> You are a senior code reviewer. Review {DIFF_OR_PREFIX} for correctness/security/perf/maintainability.
> OUTPUT ONLY: `SEVERITY | title (<=9 words) | file:line`. Max 8 findings. No prose.

WITH skill:
> You are a senior code reviewer for {PROJECT}. FIRST read and apply {SKILL_BUNDLE}, INCLUDING its
> "do-NOT-flag" lists. Drop any finding you can't tie to a stated convention or a real bug.
> THEN review {DIFF_OR_PREFIX}.
> OUTPUT ONLY: `SEVERITY | title (<=9 words) | cited-rule | file:line`. Max 8 findings. No prose.

## Pipeline sketch (maps to your k-runner)
```
for pr in PRS:
  code = prefix_snapshot(pr) if pr.is_ground_truth else diff(pr)
  for cond in [without_skill, with_skill]:
    runs        = k_runner(review_agent, inputs={code, skill if cond else None}, k=K)
    findings    = canonicalize_and_tally(runs)          # f = hits/K per finding
    stable      = [x for x in findings if x.f >= STABILITY_THRESHOLD]
    confirmed   = [verify(x, REPO) for x in stable]      # TP/FP via grep + verifier agent
    score[pr][cond] = metrics(confirmed, oracle=pr.fix_if_ground_truth)
report = compare(score)   # recall, TP, FP-rate, unique coverage, calibration, noise
```
