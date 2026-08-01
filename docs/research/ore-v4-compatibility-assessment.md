# ORE V4 Compatibility Assessment

**Assessment date:** 2026-08-01

**Scope:** ORE Miner V3 Version 1.0 compatibility with the current official ORE protocol

**Method:** Read-only comparison of pinned and current official source, official documentation, the official mining UI, and repository consumers

## Executive summary

ORE Miner V3 Version 1.0 is compatible with the current official ORE source.
The decisive fact is that the ORE source revision used to define RFC-011's
protocol model and the current `master` commit in the official ORE repository
are the same full Git object:

```text
RFC-011 evidence pin: 3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe
official origin/master: 3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe
```

A direct Git comparison from the pin to current `master` is empty. There are
therefore no post-pin account, instruction, serialization, PDA, deployment,
reward, settlement, checkpoint, transaction-flow, authority, or entropy
changes to adapt.

The apparent version conflict is nomenclature, not a source incompatibility.
The official repository merged its explicitly named
[V4 migration in pull request #157](https://github.com/regolith-labs/ore/pull/157)
on 2026-06-25. RFC-011's source pin was taken later, on 2026-07-30, after that
migration and all later changes now present on `master`. The pinned/current
source calls the global account `BoardV4`, while the Cargo workspace is version
`3.8.20` and the deployed program identifier remains
`oreV3EG1i9BEgiAJ8b177Z2S2rMarzak4NMv1kULvWv`. “ORE V4” is consequently not a
different post-RFC-011 source tree in the authoritative material examined.

No Version 1.0 bug fix, Version 1.1 feature, or new RFC is required for the
current protocol revision. The Observer, Dataset Builder, Replay Engine,
Strategy Lab, economic simulator, CLI, and existing research datasets remain
compatible. This conclusion is source-level: this investigation did not
independently attest the live mainnet program binary to the Git commit.

## 1. Evidence and terminology

### 1.1 Authoritative comparison points

| Evidence | Finding |
| --- | --- |
| [Official ORE repository](https://github.com/regolith-labs/ore) | Default branch is `master`. A fresh fetch on 2026-08-01 resolved `origin/master` to `3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe`. |
| [Pinned official source](https://github.com/regolith-labs/ore/tree/3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe) | The source revision recorded by the [ORE Resource Semantics Investigation](ore-resource-semantics.md) and used by RFC-011. |
| Git object comparison | `git diff 3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe..origin/master` produced no output. Both names resolve to the same commit and tree. |
| [RFC-011](../rfcs/RFC-011-ORE-DEPLOYMENT-ECONOMICS.md) | Defines an immutable protocol revision and requires protocol-specific economics to fail closed on a revision mismatch. |
| [Local settlement model](../../src/orev3/strategy_lab/settlement.py) | Names the supported revision `ore-v3-program-3112ab78` and rejects other values. The suffix resolves to the exact official commit above. |
| [Official V4 migration PR](https://github.com/regolith-labs/ore/pull/157) | Merged 24 migration commits into `master` on 2026-06-25, including Board, Config, Round, Treasury, Miner, and Automation migration work. It is an ancestor of the RFC-011 pin. |
| [Official mining documentation](https://ore.com/about) | Describes the 5x5 board, one-minute rounds, proportional SOL settlement, split/solo ORE rewards, motherlode, and refining. |
| [Official mining UI](https://ore.com/mine) | Inspected unauthenticated on 2026-08-01 to distinguish client presentation from on-chain behavior. |

No separate official release tag, version manifest, or announcement was found
that identifies a later “V4” commit after the RFC-011 pin. The official
repository currently has no Git tags. Its only checked-in changelog document
describes top-miner verification and is already part of the pinned tree.

### 1.2 Fact labels used in this assessment

- **Protocol fact** means behavior established by the current official program
  source at the exact pinned/current commit.
- **Official documentation** means content published by ORE on `ore.com` or in
  the official repository.
- **Repository fact** means behavior directly established by ORE Miner V3
  source or its frozen RFCs.
- **Inference** means a compatibility conclusion drawn from those facts. It is
  marked explicitly where it appears.

Community discussion was not needed to reach any conclusion and is not used
as evidence.

## 2. Revision identity and the meaning of “V4”

The official history contains a real V4 migration. Pull request #157 was
merged before the reference study for RFC-011. Its commit history explicitly
includes “migrate boardv4,” Config, Round, Treasury, Miner, and Automation
migrations. The current [Board source](https://github.com/regolith-labs/ore/blob/3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe/api/src/state/board.rs)
still documents the struct as `BoardV4`.

At the same time, the current source retains:

- workspace version `3.8.20`;
- program ID `oreV3EG1i9BEgiAJ8b177Z2S2rMarzak4NMv1kULvWv`;
- the existing ORE mint, Board, Config, and Treasury addresses; and
- account discriminators in the same `OreAccount` enum.

These identifiers show why a label-only comparison is unsafe. The correct
compatibility boundary is the exact source commit. On that boundary, RFC-011
does not precede V4: it pins the present post-migration V4 source.

## 3. Protocol comparison

### 3.1 Identity comparison

| Property | RFC-011 pin | Current official protocol | Change |
| --- | --- | --- | --- |
| Source commit | `3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe` | `3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe` | None |
| Program ID | `oreV3EG1i9BEgiAJ8b177Z2S2rMarzak4NMv1kULvWv` | Same | None |
| Workspace version | `3.8.20` | Same | None |
| Board address | `BrcSxdp1nXFzou1YyDnQJcPNBNHgoypZmTsyKBSLLXzi` | Same | None |
| Config address | `9c9X7aDRAF41faiDs94ELjT19UrGnn72wBW9hPsS4Awy` | Same | None |
| Treasury address | `45db2FSR4mcXdSVVZbKbwojU6uYDpMyhpEi7cC8nHaWG` | Same | None |
| ORE mint | `oreoU2P8bN6jkk3jbaiVxYnG1dCXcYxwhwyK9jSybcp` | Same | None |

**Impact classification:** No impact.

### 3.2 Accounts and state layouts

The current [state module](https://github.com/regolith-labs/ore/blob/3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe/api/src/state/mod.rs)
defines exactly the same six ORE account types as the pin.

| Account | Discriminator | Current immutable field order relevant to compatibility | Pin-to-current change |
| --- | ---: | --- | --- |
| Automation | 100 | amount, authority, balance, executor, fee, strategy, mask, reload, cumulative SOL spent, cumulative ORE earned, conditions | None |
| Config | 101 | `AdminConfig`, then `ProtocolConfig` including fee, timing, and entropy authority/program addresses | None |
| Miner | 103 | authority, auto-return, checkpoint fields, 25-element deployed/mass/cumulative vectors, round and reward state, claim times, lifetime totals | None |
| Treasury | 104 | motherlode, miner rewards factor, total refined ORE, total unclaimed ORE | None |
| Board | 105 | round ID, start slot, end slot, production-cost EMA | None |
| Round | 109 | round ID; 25-element deployed, mass, and miner-count vectors; entropy bytes; expiry; motherlode; rent payer; 25 reward buckets; settlement totals; unique-miner total; top miner | None |

All remain `#[repr(C)]`, POD/Steel accounts with the same discriminators and
field ordering at both comparison points. No serialization change exists
between the pin and current source.

The Entropy `Var` consumed by Deploy and Reset is owned by the separate
official entropy program. It is an external dependency, not a seventh ORE
account type. Its integration is unchanged from the pin.

**Impact classification:** No impact. In particular, the Observer's Board,
Round, and Treasury decoders still match the official layouts.

### 3.3 PDA derivations

| Account | Current and pinned seeds |
| --- | --- |
| Automation | `[b"automation", authority]` |
| Board | `[b"board"]` |
| Config | `[b"config"]` |
| Miner | `[b"miner", authority]` |
| Round | `[b"round", round_id.to_le_bytes()]` |
| Treasury | `[b"treasury"]` |

The program ID and every derivation are identical. No PDA migration is needed.

**Impact classification:** No impact.

### 3.4 Instructions

The current [instruction enum](https://github.com/regolith-labs/ore/blob/3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe/api/src/instruction.rs)
and [program dispatch](https://github.com/regolith-labs/ore/blob/3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe/program/src/lib.rs)
are byte-for-byte the pinned versions.

| Requested area | Current/pinned behavior | Pin-to-current change |
| --- | --- | --- |
| Deploy | `u64` amount plus 25-bit square mask; current-round/timing, authority, checkpoint, and per-square guards in the handler | None |
| Checkpoint | Finalizes one Miner account's prior-round SOL and ORE entitlement and checkpoint state; supports expiry/forfeiture and checkpoint bot fee | None |
| Claim SOL | Claims accumulated SOL from the authority-derived Miner account | None |
| Claim ORE | Supports basis-point partial claims and the unrefined ORE fee/refining flow | None |
| Reset | Finalizes entropy and settlement, emits the reset event, creates the next Round, and advances Board | None |
| Initialization | No active `Initialize` opcode or handler exists in the pinned/current dispatch | None |
| Other mining instructions | Automate, Close, and Log | None |
| Admin/maintenance instructions | Buyback, Bury, Wrap, SetAdmin, and NewVar; `Liq` is explicitly rejected by dispatch | None |

`AutomateV2` is a compatible alternate payload parser for Automate, not a
post-pin instruction addition. No instruction was added or removed after the
RFC-011 pin.

The official README currently lists `Initialize`, `SetFeeCollector`, and
`SetFeeRate`, but those entries do not correspond to active dispatch arms in
the same source tree, and the linked `program/src/initialize.rs` is absent.
For compatibility, the compiled enum and dispatch are authoritative. This is
an official documentation inventory inconsistency, not a Version 1.0 protocol
break and not a pin-to-current change.

### 3.5 Deployment and authority semantics

The pinned/current [Deploy handler](https://github.com/regolith-labs/ore/blob/3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe/program/src/deploy.rs)
retains these facts:

1. One Miner PDA is derived from one authority.
2. A Deploy carries one lamport amount and a 25-bit square mask. The amount is
   applied independently to each newly selected square.
3. A Miner already holding a positive deployment on a square in the same round
   cannot add a second recorded placement to that square; the handler skips it.
4. A Miner entering a new round must have checkpointed its prior Miner round.
5. Deploy must target the Board's current Round during the active slot window.
6. The first deployment starts a waiting round and advances the external
   entropy variable.
7. Direct and automated execution share the same authority-specific Miner and
   Round state. Automation adds Preferred, Random, and Discretionary selection,
   executor, budget, reload, and conditions behavior.

**Impact classification:** No impact. These are the semantics RFC-011's
25-element participant deployment vector and protocol constraint layer were
designed against.

### 3.6 Entropy and winner selection

The pinned/current [Round model](https://github.com/regolith-labs/ore/blob/3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe/api/src/state/round.rs)
and [Reset handler](https://github.com/regolith-labs/ore/blob/3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe/program/src/reset.rs)
retain the same process:

- Deploy requests the next external Entropy `Var` value for the round's end
  slot.
- Reset requires a finalized nonzero entropy value and copies it to Round.
- Round XORs four little-endian `u64` words from that value.
- `entropy % 25` selects the winning square.
- For a solo reward, bit-reversed entropy samples a lamport position in the
  winning square's deployed-capital interval.

No entropy account, derivation, encoding, or winner formula changed after the
pin.

**Impact classification:** No impact to Observer, Dataset, Replay, Strategy
Lab, or RFC-011 economics.

### 3.7 Reward, settlement, dilution, and checkpoint behavior

The current source is the exact settlement source RFC-011 pinned:

- losing-square SOL funds the round payout;
- the program deducts its administrative and vault portions before
  exposing `total_winnings`;
- winning-square SOL principal and the distributable winnings are returned
  pro rata during Checkpoint;
- one base ORE reward is either split pro rata or awarded to a sampled solo
  winner;
- `0.2 ORE` is added to the motherlode each round and the current source uses a
  `1 in 500` hit test;
- a hit motherlode is distributed pro rata on the winning square;
- Checkpoint records claimable ORE and SOL, auto-returns/reloads SOL according
  to Miner/Automation configuration, and enforces the checkpoint reserve;
- claiming unrefined ORE applies the refining fee and redistributes it through
  the Treasury rewards factor.

The [official mining explanation](https://ore.com/about) agrees on the 5x5
board, one-minute prospecting period, proportional SOL distribution, split or
solo ORE reward, `0.2 ORE` motherlode contribution, `1 in 500` motherlode odds,
and 10% refining fee. One wording difference is worth recording: the website
says the solo alternative occurs “half of the time,” while current source
constructs a deterministic distribution mask with 10 solo-labeled squares
out of 25. This source/documentation discrepancy is present inside the pinned
revision and is not a V4-after-RFC-011 change. RFC-011 settlement consumes the
finalized Round's split/solo fact rather than deriving results from the website
frequency statement, so it does not create a compatibility break.

**Impact classification:** No pin-to-current impact. The documentation mismatch
is an existing descriptive limitation, not a protocol delta.

### 3.8 Transaction flow

The transaction-level flow remains:

```text
optional Automate configuration
        ↓
Deploy during current round (possibly more than one square in one mask)
        ↓
Reset after end slot + intermission (finalizes round and opens successor)
        ↓
Checkpoint the authority's prior Miner round
        ↓
Claim SOL and/or Claim ORE when applicable
```

The official UI may submit or schedule these operations differently, but no
on-chain transaction-flow change exists between the two references because
both resolve to the same commit.

## 4. Official mining UI versus protocol

The unauthenticated [official Mine page](https://ore.com/mine) was inspected in
both visible modes on 2026-08-01.

| UI observation | Classification | Protocol correspondence |
| --- | --- | --- |
| Live Deployed, Motherlode, and Time counters | UI/client presentation | Values correspond to Board, Round, and Treasury state, but formatting and refresh behavior are client concerns. |
| Lite and Pro modes | UI/client behavior | No Lite or Pro on-chain instruction or account state exists. |
| Amount input, `+0.01`, `+0.1`, `+1`, and `MAX` controls | UI/client behavior | Ultimately materialize a lamport Deploy amount; the shortcuts are not protocol rules. |
| Pro mode displays 25 selectable tile values | UI over protocol fact | The 25 tiles correspond to the 25-bit Deploy mask and 25-element Round vectors. Selection UX is not serialized on chain. |
| Tiles and Rounds controls plus Per-round summary | Client planning/automation | These controls can configure selection and repeated execution; the protocol only sees individual instructions and Automation state. |
| Miner list and “Last round Split” display | UI/client presentation | Derived from Miner/Round/event data. It does not alter settlement. |
| Connect and disabled Deploy while unauthenticated | Wallet/client gate | Wallet connection is required by the web client, not an additional ORE account layout or protocol revision. |

The UI is therefore consistent with the 5x5 deployment protocol at a high
level but adds presentation, wallet, scheduling, and convenience behavior.
No observed UI feature establishes a new on-chain account or instruction.

## 5. ORE Miner V3 repository impact

### 5.1 Observer

**Repository facts:**

- [`observer/accounts.py`](../../src/orev3/observer/accounts.py) uses the same
  program, Board, and Treasury addresses as current official source.
- It validates current account discriminators: Board 105, Round 109, and
  Treasury 104.
- It decodes the four current Board `u64` fields, the complete current Round
  ordering, and Treasury motherlode.
- It derives Round using `[b"round", round_id little-endian]` and the same
  program ID.

**Inference:** The Observer remains compatible. No decoder or address update
is needed. Automation, Config, and Miner are not necessary for its board/round
observation responsibility, and none is new relative to the pin.

### 5.2 Dataset Builder and research datasets

The Dataset Builder consumes normalized observer snapshots, assembles round
lifecycles, and preserves finalized outcomes. Since the observed layouts,
25-square domain, outcome fields, and entropy formula are unchanged, there is
no dataset schema or rebuild requirement caused by current ORE V4.

Existing datasets remain historical evidence for the protocol revision under
which they were observed. Their identity and provenance must remain intact;
“V4” marketing terminology is not a reason to rewrite or relabel records.

**Inference:** Compatible; no update.

### 5.3 Replay Engine

[`replay/engine.py`](../../src/orev3/replay/engine.py) converts normalized
historical observations into strategy-safe replay points and deliberately
excludes finalized outcomes from pre-decision strategy input. It does not
decode on-chain accounts. Its ordering and no-future-information semantics are
unaffected by a zero source delta.

**Inference:** Compatible; no update.

### 5.4 Strategy Lab

RFC-010 Strategy interfaces consume immutable `DecisionContext` and produce
ranked preferences and abstract deployments. They do not know the ORE program
ID, instruction encoding, PDA layout, transaction flow, or settlement formula.

**Inference:** Compatible by architectural separation; no update.

### 5.5 RFC-011 economic simulator

The settlement layer supports only `ore-v3-program-3112ab78` and fails closed
on another revision. Although the symbolic name contains “v3,” its commit
suffix is the current official post-V4-migration commit. The scenario,
constraints, transaction assumptions, settlement, outcome reconciliation, and
record identities therefore remain bound to the exact current source.

This assessment establishes revision compatibility; it does not repeat the
separate implementation-correctness validation of every simulator formula.

**Inference:** Compatible with current official source; no update.

### 5.6 CLI

The CLI orchestrates the existing Replay, Strategy Lab, and RFC-011 components
and accepts a protocol revision through the immutable Economic Scenario. Since
the supported revision is current, no CLI option, default, or output change is
required.

**Inference:** Compatible; no update.

## 6. Impact classification by finding

| Finding | Classification | Explanation |
| --- | --- | --- |
| Current official commit equals RFC-011 pin | No impact | There is no protocol source delta to consume. |
| V4 migration PR predates the pin | No impact | RFC-011 was designed from the migrated source, not a pre-V4 source. |
| Program ID retains `oreV3` while Board is documented as `BoardV4` | No impact | Naming does not alter bytes, addresses, or behavior. |
| No account, layout, serialization, or PDA difference | No impact | Observer decoding and identities remain exact. |
| No instruction or dispatch difference | No impact | No client or transaction adaptation is required. |
| Lite/Pro UI modes and convenience controls | No impact | These are client presentation/planning features, not protocol changes. |
| README lists inactive initialization/admin entries | No impact | Documentation inventory drift; runtime dispatch is unchanged. |
| Website split-frequency wording differs from source mask | No impact | Existing documentation discrepancy; simulator uses finalized protocol facts. |
| Default branch could change after this assessment | Potential future breaking change | A later source commit must be reviewed under a new exact revision comparison. |
| Live deployed binary was not independently attested | Indeterminate operational evidence | Source compatibility is proven; binary-to-source identity was outside this documentation investigation. |

No identified current change requires an Observer, Dataset, Replay, Strategy
Lab, RFC-011 economic simulation, or breaking-change classification.

## 7. Compatibility matrix

| Component | Compatible | Needs Update | Breaking | Notes |
| --- | :---: | :---: | :---: | --- |
| Observer | Yes | No | No | Program/address constants, discriminators, field order, and Round PDA derivation match current source. |
| Dataset Builder | Yes | No | No | Consumes unchanged normalized 25-square lifecycles and finalized outcomes. |
| Replay Engine | Yes | No | No | Protocol-decoder independent; historical ordering and information boundary unchanged. |
| Strategy Lab | Yes | No | No | Protocol-agnostic RFC-010 layer. |
| Economic Simulator | Yes | No | No | Exact supported source commit is current `master`; symbolic `v3` label does not change binding. |
| CLI | Yes | No | No | Orchestrates current compatible components and scenario revision. |
| Research datasets | Yes | No | No | Historical evidence remains valid and source-bound; no forced rebuild or relabeling. |

## 8. Architectural impact

The repository's separation of responsibilities works as intended:

```text
Official account bytes
        ↓
Observer decoding
        ↓
Immutable historical snapshots and dataset lifecycle
        ↓
Replay information boundary
        ↓
RFC-010 strategy/deployment/evaluation
        ↓
RFC-011 revision-bound economic interpretation
```

An account/layout change would first affect Observer. A historical schema or
outcome change would then affect Dataset and Replay. A deployment or settlement
change could leave RFC-010 intact while requiring a new RFC-011 protocol model.
None of those triggers occurred because the official source is identical.

The exact-commit binding is more authoritative than the human version label.
It prevents Version 1.0 from silently treating a future ORE revision as the
current one. If official `master` advances, the economic simulator should
continue to reject that new identity until a fresh compatibility decision is
made.

## 9. Recommendations

### 9.1 Current operation

Version 1.0 can continue operating against the current official ORE source.
No compatibility remediation is indicated.

This statement assumes the live ORE program serving the Observer remains the
program at the retained ID with the layouts represented by current official
source. The official Mine page's functioning live board is supporting
operational evidence, but this investigation did not perform an independent
binary hash attestation or mainnet account probe.

### 9.2 Change classification

| Work class | Recommendation |
| --- | --- |
| Bug fix | None required for ORE V4 compatibility. |
| Minor enhancement | Optional documentation-only clarification may explain that `ore-v3-program-3112ab78` is the program-ID lineage label for a source commit that already includes the official V4 migration. This is not required for correctness. |
| Version 1.1 feature | Not required by the current protocol comparison. |
| New RFC | Not required while the official source remains at the pinned commit. A future incompatible program/account/economic revision would require an explicit architecture decision rather than silent adaptation. |

### 9.3 Future compatibility gate

For any later official ORE commit, repeat the exact comparison in this order:

1. resolve the official default-branch full SHA;
2. compare program ID, account discriminators, layouts, and PDA seeds;
3. compare instruction enum, payloads, account metas, and dispatch;
4. compare entropy, deployment, reset, checkpoint, claims, and settlement;
5. map the first changed responsibility to Observer, Dataset, Replay, RFC-010,
   or RFC-011; and
6. retain fail-closed RFC-011 revision binding until that review is approved.

## 10. Authoritative conclusion

The protocol revision pinned for RFC-011 and the current official ORE default
branch are identical. ORE V4's migration is already inside the pinned
baseline. No post-pin protocol change, breaking change, or Version 1.0
compatibility update was found. ORE Miner V3 Version 1.0 may continue using its
current Observer, datasets, Replay Engine, Strategy Lab, economic simulator,
and CLI against this exact official revision.
