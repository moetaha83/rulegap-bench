# RuleGap Bench — reproducible AI-agent policy-checking research prototype

**Status:** Exploratory research prototype (November 2026). **Organization:** MH Canada Legacy & Innovation Association.

RuleGap Bench studies a potential AI-agent oversight failure mode: a rule checker can accept an action when deployed policies, reference rules, or versions are incomplete or inconsistent. It includes a **separate bee-colony-inspired safety-test prioritization experiment**, motivated by *Bee Colony Algorithm for Proctors Assignment* (Mansour and Taha, 2015). The 2015 source code was **not** used or recovered.

> **Research limitations:** All experiments are deterministic, synthetic and offline. No live LLMs or production agents were tested. The repository does not demonstrate reduced catastrophic AI risk, certify the safety of an agent, or show that bee-colony optimization outperforms established methods. **Never use this prototype to authorize real-world agent actions.**

## Contents

- [Policy-checking experiment](src/rulegap_bench.py) — compares local-only, revision, fingerprint, conservative evidence gate, and always-withhold baselines.
- [Diagnostic report generation](src/diagnostics.py) — outputs structured evidence and a standalone illustrative HTML report.
- [Bee-inspired test selection](src/rulegap_bee.py) — compares random, greedy, and population-based search under fixed testing budgets.
- [Automated core tests](src/test_rulegap.py) and [bee tests](src/test_rulegap_bee.py) — twelve tests including negative/known blind spots.
- [Scientific limitations](RESEARCH_LIMITATIONS.md) — essential context for interpreting the benchmark.
- [Run everything](run_all.py) — reproduces synthetic results with fixed pseudorandom seeds.

## Reproduce on Python 3.10+

From the repository root:

```bash
python run_all.py
python -m pip install -r requirements-dev.txt
python -m pytest -q src/test_rulegap.py src/test_rulegap_bee.py
python src/diagnostics.py --out results/core
```

The experiments use Python standard library; `pytest` is only for tests. Output CSV/JSON and the illustrative HTML report are generated under `results/`.

## Preliminary results

**Policy gate:** 504 synthetic cases (252 development and 252 held-out); 2,520 simulated checker evaluations. The stricter `rulegap` approach incorrectly approved **0 of 126 modeled unsafe cases** in the held-out split, but allowed only **18 of 126 legitimate cases**. This is too restrictive for a live gate; treat it as an offline diagnostic research subject.

**Bee-inspired test selection:** Across 24 synthetic trials with eight selected tests, mean detected modeled faults (out of 12) were **random 3.04**, **greedy 8.00**, **bee-inspired 7.29**. Bee-inspired search **did not outperform greedy**; future work must justify its extra computational cost.

These scores apply only to engineered test cases, **not real-world safety**. The held-out samples come from the same benchmark generator and are not an independent external benchmark.

## Relationship to existing research

RuleGap Bench overlaps with existing agent policy enforcement, formal verification, and mutation-testing. We **do not claim** to invent missing-rule detection or bee-colony-based testing. Next-stage research could evaluate policy provenance, safety-versus-usability trade-offs, and model-driven agent workflows on stronger external cases.

Earlier research: [Bee Colony Algorithm for Proctors Assignment (2015)](https://it-in-industry.com/issue/archive/45.html).

## Public release and licensing

Published for inspection and reproducibility. **No open-source software license has been granted.** Public visibility alone does not grant reuse rights. Any open-source licensing should follow organizational and IP review.

The repository contains no production credentials or actual agent authorization data.
