# Scientific limitations and interpretation

## Scope
All experiments are **synthetic deterministic simulations**. There are no live language-model calls, production systems, real agent behaviors, or human-subject data. Test cases were developed within the same project and are not independently sourced external benchmarks.

## Policy checker
Five methods are compared: local-only, revision-label, manifest fingerprint, conservative evidence/critical-rule gate, and always-withhold. The conservative gate has zero false approvals in the **modeled held-out unsafe cases**, but allows only 18/126 legitimate cases. Reporting just the unsafe approvals would be misleading.

A policy fingerprint is not a digital signature and does not prove authenticity or semantic correctness. The independent critical-rule registry is assumed to exist and may itself be incomplete. A requirement omitted from all purportedly authoritative inputs can escape detection.

## Bee-colony experiment
Bee-inspired search optimizes an authored surrogate feature-coverage score; it does not see held-out mutant outcomes when selecting tests. Features and omitted-rule mutants were both designed for this benchmark. The experiment is not a reconstruction of the 2015 historical algorithm. At the eight-test budget, greedy outperformed bee-inspired search, which also uses more search computation.

## Unproven
No live-agent performance, catastrophic-risk reduction, algorithmic novelty, superiority over modern alternatives, or production readiness has been established. All comparisons require independent baselines, realistic workflow traces, and measurement of both missed faults and excessive withholding.
