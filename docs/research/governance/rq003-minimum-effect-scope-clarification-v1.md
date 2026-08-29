# RQ-003 Minimum-Effect Scope Clarification v1

## Status

- Type: Prospective research-governance scope decision
- State: Adopted and frozen prospectively
- Historical authority mutation: None
- Outcome evidence used: None
- Implementation authorized: No
- Experiment execution authorized: No

This decision clarifies the prospective scope of the tracked
[RQ-003 Minimum Scientifically Relevant Effect policy](rq003-minimum-scientifically-relevant-effect.md).
It does not select a numeric `delta_min`, revise a completed experiment,
authorize Experiment 005 execution, or waive later Strategy, economic, paper,
launch, safety, or capital materiality requirements.

## 1. Authority and history

The governing chain is:

1. [RQ-003](../questions/RQ-003-winning-square-predictability.md) owns the
   direct scientific question: whether a fixed decision-time ranking contains
   reproducible winner-ranking information beyond both uninformed baselines.
2. The minimum-effect policy was committed as
   `9c85ed63ad6963658c174fd00033e6b42c85e752` to govern the minimum-potential-
   effect continuation gate defined by
   [Experiment 2A](../experiments/rq003-experiment-002a-deployment-per-miner-characterization.md).
   That gate compares the outcome-blind upper bound `U` for Deployment per
   Miner versus raw Deployment with an approved `delta_min` before it may
   authorize the dependent Experiment 2B predictive comparison.
3. The later direct-information protocols for
   [Experiment 3](../experiments/rq003-experiment-003-miner-count-predictive-evaluation.md)
   and
   [Experiment 4](../experiments/rq003-experiment-004-deployment-per-miner-predictive-evaluation.md)
   were frozen after that policy at commits
   `7f0418fbefa78de883d9e2590f7f6de031989811` and
   `c42e2ef2727bcf86c1cad87d42b065b44c0e5ffd`. Each prospectively fixed a
   zero-improvement statistical decision boundary against both permanent
   uninformed baselines, reported effect magnitude, and produced a valid
   bounded direct-information result without a positive `delta_min` gate.
4. This decision makes that tracked distinction explicit for future direct-
   information protocols. It does not rewrite the earlier documents or their
   historical meanings.

## 2. Governed distinction

Two scientific decisions remain separate.

### 2.1 Characterization-to-dependent-evaluation promotion

The existing minimum-effect policy continues to govern a prospective gate
whose question is whether an outcome-blind characterization demonstrates
enough *potential* improvement over a specified scientific comparator to
justify authorizing a dependent outcome-bearing evaluation. This includes the
Experiment 2A-to-Experiment 2B gate.

For such a gate:

- `delta_min` must be positive, contrast-specific, prospectively justified,
  and bound by an immutable governance identity;
- a potential-effect upper bound, difference count, statistical power, or
  observed result cannot supply the threshold;
- missing threshold authority fails the dependent continuation closed; and
- this clarification does not authorize Experiment 2B or retroactively pass
  Experiment 2A's unresolved gate.

### 2.2 Direct predictive-information evaluation

A direct RQ-003 predictive-information protocol asks whether one fixed,
scientifically justified ranking procedure contains reproducible winner-
ranking information beyond both permanent uninformed baselines. When that
protocol is not dependent on a minimum-potential-effect characterization gate,
it does not require a separate positive numeric `delta_min` merely to answer
that direct information question.

It must instead freeze before outcome access:

- the exact signal and ranking direction;
- both permanent uninformed baselines and population parity;
- the direct estimands and effect-magnitude reporting;
- the uncertainty construction, multiplicity control, and exact statistical
  decision boundary;
- chronology, population, missingness, stability, and confirmation controls;
- bounded positive, negative, insufficient, and invalid dispositions; and
- an explicit prohibition on material, Strategy, economic, paper, launch,
  safety, or capital interpretation.

For this class, a zero-improvement null boundary answers only whether positive
predictive information is established under the frozen controls. It does not
mean that an arbitrarily small effect is scientifically material for later
use. A favorable initial result remains provisional until disjoint
confirmation and cannot establish Strategy or economic suitability.

## 3. Experiment 005 boundary

Experiment 005's primary direct estimands compare descending exact Signed
Share Imbalance with the deterministic and seeded-random uninformed baselines.
They fall within Section 2.2 when the Experiment 005 protocol and this decision
are both frozen prospectively before any Experiment 005 outcome access.

Experiment 005's gated Deployment-per-Miner comparison asks only whether the
fixed Share-Imbalance ordering has a positive paired ranking-quality
difference on the same eligible labeled population. It does not authorize the
experiment, select the signal, establish conditional information, or claim
material incremental superiority. Consequently, that descriptive/gated
secondary contrast does not receive or waive a positive `delta_min` under
this decision. Its effect estimate and interval must be reported, and any
future claim of material incremental superiority requires separate
prospective governance.

This decision authorizes no implementation or execution. Experiment 005 must
still undergo protocol review, freeze, implementation, Execution Readiness,
launch validation, and every later authority step separately.

## 4. Claims not authorized

Absence of a numeric `delta_min` for a governed direct-information test does
not establish or authorize:

- practical or scientific materiality beyond the bounded information claim;
- independent, conditional, causal, or learned-model information;
- Strategy admission or Decision Engine use;
- economic or portfolio value;
- Paper Miner or Live Miner suitability;
- launch, control, allocation, or attempt authority; or
- real-SOL or other capital deployment.

Those questions require their own prospectively frozen evidence thresholds,
simulation assumptions, confirmation, operational controls, and safety
authority. Nothing here weakens them.

## 5. Historical and prospective boundary

This clarification is prospective from its adoption commit. It does not alter
the bytes, identities, dispositions, or interpretation of RQ-003, the
minimum-effect policy, Experiment 2A, Experiments 3 or 4, or their findings.
It does not promote inherited uncommitted material into authority.
The minimum-effect policy remains controlling for the
characterization-to-dependent-evaluation promotion class in Section 2.1.
This decision controls the narrower direct-information class in Section 2.2
after the adoption commit is pushed and independently remote-verified.

## 6. Information-flow and side-effect boundary

This decision was derived from tracked protocols, governance, Git history,
and outcome-blind scientific reasoning. No raw outcome or winner data was
opened, queried, or used. Frozen historical findings were used only to verify
the existing authority sequence and bounded interpretations.

This decision creates no implementation, adapter, projection, candidate,
`READINESS_VALIDATED`, E, R, `EXECUTION_READY`, launch, experiment result,
Strategy, paper, live, or capital authority.
