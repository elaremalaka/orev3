# RFC-008 Frozen Decision Table

Status: **Approved and frozen**

All rates use started rounds as the denominator unless explicitly stated.
All statistical units are independent rounds.

| Disposition | Exact criteria |
|---|---|
| **Success** | At least 600 primary-analyzable rounds; exact one-sided McNemar `p < 0.025` for candidate versus random; candidate-minus-random hit-rate point estimate `>= +0.06`; lower two-sided 95% paired round-bootstrap bound `> 0`; reconstructed candidate after-fee ROI `> 0`; lower two-sided 95% round-bootstrap ROI bound `> 0`; one-sided paired economic randomization `p < 0.025` versus no-deploy; missing/conflicted/quarantined/unusable rate `<= 5%`; marker and configuration unchanged; no safety failure. |
| **Failure** | Upper two-sided 95% paired hit-difference bound `<= 0`; or upper two-sided 95% after-fee ROI bound `<= 0`; or missing/conflicted/quarantined/unusable rate `> 5%`; or any marker, provenance, source-integrity, live-action, or safety boundary is violated. |
| **Inconclusive** | A terminal boundary is reached without every success criterion and without a failure criterion; fewer than 600 primary-analyzable rounds at 632 started rounds or 14 days; positive hit advantage below +0.06; a confidence interval crossing zero; predictive and economic gates disagree; or evidence required by the locked analysis is unavailable. |

Recovered outcomes are excluded from the primary count and may appear only in
a labeled sensitivity analysis. Failure takes precedence over inconclusive
when both descriptions could otherwise apply. Paper success does not authorize
live action.

The +6-point gate was retained after the economic-threshold validation in
`RFC-008-ECONOMIC-THRESHOLD-APPROVAL-AMENDMENT.md`. The calculated
conservative break-even improvement was +4.96 points, rounded upward to +5;
the approved +6 threshold is stricter.
