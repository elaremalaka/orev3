# RFC-007 Closure — Continuous Paper Collection and Gate B

Status: **Closed**

Closed from branch:
`research/rfc-007-paper-collection-burn-in`

Closure basis commit:
`da25e262390dd2f414e6f63c168c843fbcf5eb0d`

## 1. Decision

RFC-007 succeeded operationally and failed to support the frozen strategy.

The collector demonstrated continuous paper-only operation, persisted restart
and resume evidence, froze a deterministic 1,000-opportunity sample, preserved
the observer boundary, and performed zero live actions. Missing final outcomes
were recovered as a separate, dual-provider, provenance-preserving artifact.
The original ledger and marker were not backfilled.

The frozen `existing_least_crowded` top-four, equal-allocation strategy produced
a negative research result. It is retired from live consideration. RFC-007
does not justify controlled-live or production deployment.

This retirement applies to the frozen RFC-007 configuration. The result may be
retained as a historical comparator in later preregistered research, but it
must not be retuned and reevaluated on the RFC-007 Gate B sample.

## 2. Immutable evidence

| Artifact | Path | SHA-256 |
|---|---|---|
| Gate B marker | `data/ledger/rfc007_gate_b_marker_v1.json` | `660cfa8385a60f338191fe654edde389fc4a585a5bf676aff03bb219a1f8fc51` |
| Recovery evidence | `data/recovery/rfc007_gate_b_outcome_recovery_v1/evidence.jsonl` | `0d04f1b7586963612d784982fd1ca7d4213b8a9466680d5a3a0d9c73611eda77` |
| Recovery manifest | `data/recovery/rfc007_gate_b_outcome_recovery_v1/manifest.json` | `fbb47f3b1dd7c4763f990f1c913bc9efc970cd25eb834a34591e78bea84810ea` |
| Recovery artifact content | recovery manifest field | `4bb69a4088690fbcc41d0cebff9823a768f28e995023d7bcf7a3fe72db72fbae` |
| Derived Gate B dataset | `data/analysis/rfc007_gate_b_dataset_v1/gate_b_analysis_dataset_v1.jsonl` | `1db4b925c55236b60f5d33756f620d2282fd966b06e3950ff8acc1dc7ff3a869` |
| Dataset manifest | `data/analysis/rfc007_gate_b_dataset_v1/manifest.json` | `fd41485dfbbfb9fd97c2095bdff4941a5c7626673387bd2403306e1805445d59` |
| Formal results | `data/analysis/rfc007_gate_b_results_v1/results.json` | `71042b60823f57234d416371619b5b308ec0520d8305a5f0fa2493012f977c22` |
| Human report | `data/analysis/rfc007_gate_b_results_v1/report.md` | `c7c6cd2f666481d5d3884507ee2381e530da25ec5902695eb78d57c9d889acf3` |
| Results manifest | `data/analysis/rfc007_gate_b_results_v1/manifest.json` | `c4d0a265ad45ff29c02aa9ebe46b2da01e59f82c06264778a5f30837e8ebd6e9` |

Frozen sample ID:
`09b577bf-23d5-5aeb-8c6b-5d3eab71e42d`

## 3. Operational result

The frozen sample contains exactly:

- 1,000 consecutive eligible opportunity rows;
- 1,000 linked paper decisions;
- zero duplicate opportunity, decision, or derived analysis identifiers;
- 78 contemporaneously reconciled rows;
- 922 rows labeled with separately recovered finalized outcomes;
- zero unresolved derived rows;
- zero provider disagreements or quarantined recovered rounds; and
- zero live actions.

Recovery covered 13 missing rounds. Round `345107` was validation-only and
matched the contemporaneously captured outcome. It was not used as a recovered
replacement.

The observer, collector, and recovery artifacts remained separate. Recovery
did not alter paper decisions, accounting, sample membership, the marker, or
the original ledger reconciliation state.

## 4. Statistical and economic result

The formal result is:

- 1,000 opportunity rows;
- 14 independent finalized rounds;
- 59 hits and 941 misses;
- opportunity-level hit rate: 5.9%;
- stated random top-four benchmark: 16%;
- exact round-level one-sided p-value for outperforming that benchmark:
  0.881894;
- reconstructed ROI before fees: -68.27%;
- reconstructed ROI after assumed fees: -78.86%;
- round-cluster 95% interval for ROI after assumed fees:
  -110.00% to -23.43%;
- no Motherlode return; and
- base ORE unavailable.

The transparent post-hoc outperformance hypothesis was not supported.
Reconstructed positive economic return was also not supported.

RFC-007 did not preregister a numerical performance threshold. Its result
therefore cannot be described as acceptance or rejection of a preregistered
strategy hypothesis. The post-hoc benchmark is useful evidence, not a
replacement for a locked prospective protocol.

## 5. Why 1,000 rows are not 1,000 independent observations

Every opportunity in a round shares the same finalized winner and round-level
payout state. Repeated observations within the same round are correlated.
Treating all 1,000 rows as independent would understate uncertainty and inflate
effective sample size.

The primary experimental information came from only 14 finalized rounds.
Row-level Wilson intervals were reported descriptively, while the primary
uncertainty assessment resampled or randomized at the round level.

Future sample sizes and stopping rules must count independent eligible rounds,
not observation rows.

## 6. Outcome provenance

The derived dataset preserves two evidence classes:

- `contemporaneous`: 78 rows from one finalized round; and
- `recovered`: 922 rows from thirteen finalized rounds.

The overall and recovered-only results have the same negative predictive and
economic direction. This is a robustness check only. Provenance is confounded
with round, so the comparison cannot establish that recovery has no causal
bias.

Recovered outcomes are post-hoc authoritative labels. They were never strategy
inputs and must never be presented as contemporaneous observations.

## 7. Known limitations

1. Fourteen independent rounds provide limited precision.
2. RFC-007 had no preregistered numerical performance threshold.
3. Outcome provenance is confounded with round.
4. Price-taking accounting does not model deployment impact on the denominator
   or payout pool.
5. The 1,000 paper decisions were not simultaneously executable transactions;
   summing them is a research counterfactual.
6. Deploy and claim fees are configured assumptions, not observed participant
   costs.
7. No wallet-realized SOL return, wallet delta, fee-payer debit, claim receipt,
   or transaction failure cost was captured.
8. Base ORE and total ORE value are unavailable.
9. No Motherlode return occurred in the sample.
10. The contemporaneous provenance stratum contains only one round.
11. The final chronological block was report-only and was not available for
    strategy tuning.
12. Paper performance cannot authorize live capital.

## 8. Closure consequences

- The frozen RFC-007 strategy is retired from live consideration.
- The RFC-007 sample is closed and must not be used to tune a replacement and
  then claim holdout performance for that replacement.
- RFC-007 may be used for engineering tests, historical context, and planning
  assumptions with explicit provenance.
- The next strategy evaluation must be prospectively preregistered, use
  independent rounds as its primary unit, and freeze its candidate before its
  holdout boundary.
- Directly observed participant economics remain a separate evidence gap and
  require separate safety authorization before any transaction-related
  collection.
