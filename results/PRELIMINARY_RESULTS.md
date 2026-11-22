# Preliminary synthetic experimental results

These are offline deterministic experiments, **not validated AI-agent safety results**. Full raw CSV/JSON outputs can be regenerated with `python run_all.py`.

## Core rule-checking experiment

- Total cases: 504 (development 252; held-out 252)
- Evaluations: 2,520 (five approaches for each case)
- Held-out: 126 modeled unsafe and 126 legitimate cases
- Conservative RuleGap gate: **0/126 modeled unsafe cases incorrectly approved**, **18/126 legitimate cases allowed**; 108 legitimate cases withheld.
- Fingerprint comparator: **12/126 modeled unsafe cases incorrectly approved**, **33/126 legitimate cases allowed**.
- Local-only comparator: **24/126 modeled unsafe cases incorrectly approved**, **126/126 legitimate cases allowed**.

False-approval avoidance alone is not a valid success metric: always withholding everything also yields zero false approvals.

## Bee-inspired test-selection experiment

Twenty-four deterministic synthetic trials; eight selected tests per trial; 12 modeled single-rule omissions.

| Selection | Mean omissions detected (of 12) |
| --- | ---: |
| Random | 3.042 |
| Greedy | 8.000 |
| Bee-inspired search | 7.292 |

Bee minus greedy: mean **-0.708**; bee won **0**, tied **8**, lost **16** of 24 trials. Therefore no bee superiority has been shown.

## What is not established

No real AI model requests were executed, no deployment-grade gate exists, no generalization beyond the authored test scenarios has been proven, and the novelty or effectiveness of the full proposed research has not been independently validated.

See [RESEARCH_LIMITATIONS.md](../RESEARCH_LIMITATIONS.md) and the runnable source for complete details.
