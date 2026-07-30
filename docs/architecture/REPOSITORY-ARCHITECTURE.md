# Repository Architecture

**Status:** Draft for Human Review

This document defines the architectural organization of the ORE Miner V3 repository.

Unlike RFCs, this document does not specify software behavior.

Instead, it defines:

- repository domains;
- governance boundaries;
- validation boundaries;
- promotion boundaries;
- release scope.

This document establishes which parts of the repository are governed by which architectural processes.

---

# 1. Purpose

As ORE Miner V3 has evolved, the repository has expanded beyond a single production system.

It now contains multiple architectural domains with different responsibilities, governance requirements, and validation requirements.

The purpose of this document is to define those domains and the boundaries between them.

This document exists to answer questions such as:

- What belongs to production?
- What belongs to research?
- When does RFC-008 governance apply?
- When does production approval become necessary?
- How does research become production?

Repository architecture is intentionally separate from software architecture.

RFCs define how software behaves.

Repository Architecture defines how the repository itself is organized.

---

# 2. Guiding Principles

Repository organization shall be determined by authority rather than directory structure.

Governance shall apply only to software capable of affecting the systems it governs.

Research shall remain independent from production until explicitly promoted.

Promotion from research into production shall be an explicit architectural process.

Repository validation shall respect repository domains rather than assuming every repository change belongs to the same governance model.

---

# 3. Repository Domains

The repository is organized into four architectural domains.

Repository domains are defined by **authority** and **reachability**, not directory location.

A component belongs to the domain whose authority governs its behavior.

Sharing a repository does not imply sharing governance.

---

## 3.1 Production Domain

The Production Domain contains every component capable of influencing operational collection or production evidence.

Examples include:

- RFC-008 operational collection.
- RFC-009 continuation authority.
- Production collectors.
- Supervisors.
- Authorization.
- Recovery.
- Ledger management.
- Outcome resolution.
- Production configuration.
- Production migrations.
- Production approval artifacts.

Production components may directly affect:

- operational correctness;
- governance;
- durable evidence;
- recovery;
- authorization;
- release identity.

The Production Domain is governed by RFC-008 and RFC-009.

---

## 3.2 Research Domain

The Research Domain contains components used exclusively for offline experimentation.

Examples include:

- Strategy Laboratory.
- Replay Engine.
- Historical datasets.
- Feature engineering.
- Offline simulation.
- Offline evaluation.
- Research reports.

Research components:

- never modify production state;
- never require production authorization;
- never submit transactions;
- never interact with production governance.

Research produces evidence.

It does not produce operational authority.

RFC-010 belongs entirely to the Research Domain.

---

## 3.3 Documentation Domain

The Documentation Domain contains descriptive and normative documents.

Examples include:

- RFCs.
- Implementation Plans.
- Architecture documents.
- Design documents.
- Research reports.
- Operational runbooks.

Documentation defines architecture and process.

Documentation alone never grants operational authority.

Operational authority always requires the governance defined by RFC-008 and RFC-009.

---

## 3.4 Promotion Domain

The Promotion Domain defines the boundary between research and production.

Promotion is the explicit architectural process by which research outputs become production candidates.

Promotion exists because research and production operate under different governance models.

No research artifact becomes production merely because it exists within the repository.

---

# 4. Production Release Closure

The Production Release Closure defines the complete set of repository artifacts capable of influencing an approved production release.

RFC-008 and RFC-009 govern the Production Release Closure.

The Production Release Closure consists of the transitive closure of every executable production entry point together with every dependency capable of influencing operational behavior.

This includes:

- executable production modules;
- imported runtime dependencies;
- production configuration;
- production migrations;
- production authorization artifacts;
- production governance artifacts;
- production approval artifacts;
- production markers;
- runtime schemas;
- hash-bound operational documents.

Any artifact capable of influencing production behavior belongs to the Production Release Closure regardless of its directory location.

Conversely, artifacts outside the Production Release Closure are not governed by RFC-008 operational approval solely because they share the same Git repository.

Repository location never determines governance.

Operational reachability determines governance.

---

# 5. Governance Boundaries

Repository governance is domain-specific.

## Production Domain

Changes affecting the Production Release Closure require:

- RFC-008 operational approval;
- RFC-009 continuation governance where applicable;
- production validation;
- operational release workflow.

These changes are capable of affecting operational behavior.

---

## Research Domain

Research components require:

- architectural review;
- implementation review;
- deterministic validation;
- reproducibility validation.

Research components do not require RFC-008 operational approval unless they are explicitly promoted into the Production Release Closure.

---

## Documentation Domain

Documentation requires:

- documentation review;
- consistency validation;
- architectural correctness.

Documentation requires operational approval only when the document itself becomes part of the Production Release Closure.

Examples include:

- production approval artifacts;
- operational runbooks;
- hash-bound governance documents.

Descriptive documentation alone does not require operational approval.

---

## Promotion Domain

Promotion is the only architectural path from Research to Production.

Promotion always requires explicit human approval.

Promotion creates a new production candidate.

Promotion never occurs implicitly.

---

# 6. Validation Boundaries

Validation requirements are determined by repository domain.

Validation shall verify only the invariants relevant to the domain being modified.

## Production Validation

Production validation includes:

- operational correctness;
- governance validation;
- authorization validation;
- recovery validation;
- release-chain validation;
- production integration testing;
- full repository regression testing where applicable.

Production validation shall always preserve operational safety.

---

## Research Validation

Research validation includes:

- deterministic execution;
- reproducibility;
- chronological correctness;
- future-information leakage prevention;
- experiment reproducibility;
- public API stability;
- unit testing;
- integration testing within the Research Domain.

Research validation shall never require production authorization solely because research code exists within the repository.

---

## Documentation Validation

Documentation validation includes:

- architectural consistency;
- internal references;
- formatting;
- terminology consistency.

Documentation shall never grant operational authority.

---

# 7. Promotion Workflow

Promotion defines the only architectural path from Research into Production.

Promotion shall remain explicit.

The promotion workflow is:

```
Research

↓

Reproducible Evidence

↓

Candidate Selection

↓

Frozen Artifact

↓

Operational RFC Approval

↓

Production Release

↓

Operational Collection
```

Every transition across the Promotion boundary requires explicit human review.

Research results never become production automatically.

Promotion always creates a new governed production candidate.

---

# 8. Repository Invariants

The repository shall preserve the following architectural invariants.

## Domain Isolation

Research components shall not directly influence production behavior.

Production components shall not depend upon experimental research artifacts unless those artifacts have crossed the Promotion boundary.

---

## Explicit Promotion

Movement from Research to Production shall always occur through the Promotion Domain.

Promotion shall never occur implicitly.

---

## Governance Scope

RFC-008 and RFC-009 govern only the Production Release Closure.

RFC-010 governs the Research Domain.

Repository Architecture governs the repository itself.

---

## Deterministic Evolution

Repository evolution shall preserve:

- deterministic governance;
- deterministic experimentation;
- deterministic validation.

---

## Single Responsibility

Repository Architecture defines repository organization.

RFCs define software architecture.

Implementation Plans define engineering execution.

Code implements the approved architecture.

Each layer owns exactly one responsibility.

---

# 9. Governance Conclusion

ORE Miner V3 is organized into independent architectural domains.

Each domain operates under governance appropriate to its purpose.

Research remains free to evolve without weakening production governance.

Production remains strongly governed without unnecessarily constraining research.

The Promotion Domain provides the only architectural bridge between these domains.

The Production Release Closure defines the exact scope governed by RFC-008 and RFC-009.

This separation preserves:

- operational safety;
- deterministic research;
- explicit governance;
- reproducible experimentation;
- scalable repository evolution.

Future repository growth shall extend these domains rather than blur their boundaries.
