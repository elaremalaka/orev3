ORE Miner V3 — Project Snapshot 001
Status

Project phase: Foundation / Observer validation

Current implementation state: The read-only Observer can connect to Solana, read the live ORE Board and Treasury accounts, derive the current Round PDA, decode active and finalized Round accounts, and inspect all 25 mining squares.

Live mining: Not implemented

Wallet access: Not implemented

Transaction signing: Not implemented

Strategy logic: Not implemented

Permanent dataset collection: Not yet implemented

1. What Has Been Completed
Repository Foundation

A new standalone repository was created for:

ORE Miner V3

The previous ORE mining projects remain separate and are not being used as the starting architecture.

The repository includes the planned modular structure for:

Observer
Data
Features
Replay
Strategies
Decision Engine
Simulator
Paper Miner
Execution
Analytics

This aligns with the original V3 clean-sheet architecture.

2. Security Foundation

A permanent repository security policy has been added.

The project rule is:

No personal information, passwords, API keys, private keys, wallet seed phrases, access tokens, credentials, secrets, or other sensitive/confidential information may ever be committed to the repository.

The repository now includes:

.gitignore protections
SECURITY.md
.env.example
Rules for local secret handling
Explicit requirements to inspect staged changes before committing sensitive configuration changes

This was not a major structural element in the original V3 architecture, but it has now been added as a permanent cross-cutting requirement.

This is an improvement over the original plan.

3. Observer Foundation

The first executable V3 component has been created:

Read-only ORE Observer

The Observer currently:

Connects to Solana JSON-RPC.
Reads the current confirmed Solana slot.
Reads the global ORE Board account.
Reads the global ORE Treasury account.
Derives the current Round PDA.
Reads the current Round account.
Decodes the state of all 25 mining squares.

The Observer contains:

No wallet
No signing capability
No live transaction code

This directly follows the original V3 architecture.

4. Verified ORE Board State

The Observer successfully reads:

Current round ID
Round start slot
Round end slot
Production-cost EMA

The Board state has been verified against live round progression.

The round window observed was:

150 Solana slots

The Observer correctly tracks the transition from one round ID and Round PDA to the next.

5. Verified Per-Square Round State

For all 25 squares, V3 currently decodes:

SOL deployed
Unique miner count
Mass

The live values for:

SOL deployed
Miner counts

appear coherent and change as expected over the course of the round.

The per-square miner counts can exceed the total unique miner count because one miner can participate on multiple squares.

6. mass Field Investigation

The current mass[25] array has consistently remained zero.

This was observed:

During active rounds
During finalized rounds

Current protocol-code inspection indicates that normal deployment updates:

deployed[square]
count[square]

but does not appear to populate mass[square].

Current V3 classification:

Field: mass

Status: Preserved raw protocol data

Current observed behavior: Always zero

Strategy use: Disabled

Future handling: Continue recording it in case the protocol begins using it later

This is a minor deviation from the original assumption that all Round fields would necessarily represent active mining features.

The architectural principle remains unchanged: raw state is preserved even when its semantics or usefulness are uncertain.

7. Motherlode Validation

An important distinction was discovered and validated.

The accumulating live Motherlode does not live in the current Round account.

It lives in:

Treasury.motherlode

The Observer now reads the global Treasury account.

A live observed value was:

201.8 ORE

This matched the value displayed on ore.com.

This validates the Treasury Motherlode decoder.

The Round account also contains:

round.motherlode

This is separate.

Current interpretation:

Treasury.motherlode = live accumulating Motherlode pool
Round.motherlode = Motherlode amount assigned to a specific round when that round hits the Motherlode

Most rounds therefore correctly show:

round.motherlode = 0

while the Treasury Motherlode may be large.

This was a significant clarification compared with the initial Observer design.

8. Finalized Round Validation

A historical finalized round was inspected:

Round 342054

The finalized account successfully exposed:

Slot hash
Derived entropy
Expiration slot
Final per-square SOL deployments
Final per-square miner counts
Total deployed SOL
Total winnings
Total vaulted SOL
Total unique miners
Round Motherlode payout
Top miner / reward result
Winning square

For Round 342054:

Winning square: 23
Winning-square miners: 144
Winning-square deployment: approximately 0.4533 SOL
Total deployed: approximately 10.7926 SOL
Total winnings: approximately 9.2123 SOL
Total vaulted: approximately 1.0236 SOL
Round Motherlode payout: 0 ORE

This confirms the decoder is reading meaningful post-settlement state.

9. Solo Reward Clarification

The initial assumption that a “solo win” meant being the only miner on the winning square was rejected.

The finalized round contained:

top_miner = SpLiT111...

This indicates that solo/split reward behavior is represented independently from simple winning-square miner count.

V3 therefore will not define:

solo_win = winning_square_miner_count == 1

Instead:

Winning-square miner count will remain a raw fact.
Solo-reward outcome will be tracked independently.
The exact protocol semantics will be modeled explicitly once fully mapped.

This is a correction to an early assumption, but it preserves the original V3 principle of avoiding unsupported derived labels.

10. Reward Array Clarification

The finalized Round account contains a 25-element reward array.

However, a finalized test round showed:

Reward index 0 = 1 ORE
Winning square = 23

Therefore this array should not currently be interpreted as:

reward per mining square

V3 will preserve the raw array but should avoid assigning per-square meaning until the protocol semantics are fully understood.

Recommended internal label:

reward_buckets

or another neutral raw-data name.

This is another semantic correction discovered during Observer validation.

11. Current Observer Data Model

The Observer currently supports:

Board State
round ID
start slot
end slot
production-cost EMA
Treasury State
live Motherlode
Round State
round ID
deployed SOL array
mass array
miner-count array
slot hash
expiration slot
round Motherlode payout
reward array
total vaulted
total winnings
total miners
top miner
derived entropy

The data model remains immutable at the application-model level.

12. Alignment With Original V3 Plan
Fully Aligned

The following parts remain exactly aligned with the original plan:

Clean-sheet V3 repository
Previous projects retained only as references
Observer built first
Observer is read-only
No wallet or live transactions
Raw protocol state prioritized before strategy work
Solana slots used as authoritative round timing
25-square board state preserved
Modular architecture retained
No strategy optimization yet
No paper mining yet
No live mining yet
Raw facts separated conceptually from derived features
13. Improvements Beyond the Original Plan

The following were added or strengthened:

Security Policy

Repository security and secret handling became an explicit project-level requirement.

Treasury Observation

The Observer now includes global Treasury state, which was not fully specified in the original architecture.

This is important because the Treasury exposes the live accumulating Motherlode.

Finalized-Round Inspector

A separate tool was added to inspect historical finalized Round accounts.

This improves protocol validation and will likely remain useful during research and debugging.

14. Deviations From Initial Assumptions

Several assumptions were corrected.

Motherlode

Initial assumption:

round.motherlode represented the current accumulating Motherlode.

Corrected understanding:

Treasury.motherlode represents the live pool.

Solo ORE

Initial assumption:

Solo ORE could be inferred from having one miner on the winning square.

Corrected understanding:

Solo/split reward state is represented separately.

Reward Array

Initial assumption:

The 25-value reward array might correspond directly to board squares.

Corrected understanding:

The observed finalized state disproves a direct per-square interpretation.

Mass

Initial assumption:

Mass might be an active board feature.

Current understanding:

It appears unused or dormant in current protocol behavior.

These deviations are semantic discoveries, not architectural failures.

The V3 modular architecture allowed these corrections without requiring a redesign.

15. Current Architecture Position

The original V3 architecture was:

Observer
↓
Historical Dataset
↓
Replay Engine
↓
Strategy Lab
↓
Decision Engine
↓
Portfolio Simulator
↓
Paper Miner
↓
Live Miner
↓
Adaptive Strategy Layer

Current progress:

Observer — In progress / core decoding validated

Historical Dataset — Not started

Replay Engine — Not started

Strategy Lab — Not started

Decision Engine — Not started

Portfolio Simulator — Not started

Paper Miner — Not started

Live Miner — Not started

Adaptive Strategy Layer — Not started

16. Next Planned Step

The next component is:

Immutable Snapshot Logger

Its purpose will be to convert the validated Observer into a continuous fresh-data collector.

The intended flow is:

Solana RPC
↓
Read Board
↓
Read Treasury
↓
Read current Round
↓
Create immutable timestamped snapshot
↓
Append snapshot to raw JSONL dataset
↓
Repeat

The logger should initially prioritize data completeness over storage optimization.

Future processing can downsample raw data.

Missing historical snapshots cannot be reconstructed.

17. Immediate Design Requirements for Snapshot Logging

The snapshot logger should preserve at minimum:

Schema version
UTC observation timestamp
RPC slot
Board state
Treasury state
Current Round state
25-square deployed SOL
25-square miner counts
Mass array
Slot hash
Expiration
Round Motherlode
Live Treasury Motherlode
Reward array
Total winnings
Total vaulted
Total miners
Top miner

Derived features such as:

Slots elapsed
Slots remaining
Estimated seconds remaining
Board concentration
SOL-per-miner metrics
Congestion scores

should not replace raw values.

They should be calculated later in the Feature Layer.

18. Project Snapshot Conclusion

ORE Miner V3 remains strongly aligned with the original architecture.

The work completed so far has focused exactly where intended:

Understand and validate the protocol before collecting data or designing strategies.

The main deviations from the original assumptions have all improved the system:

Motherlode state is now correctly understood.
Solo rewards are no longer incorrectly inferred.
Dormant fields are separated from active features.
Unknown reward semantics are preserved rather than mislabeled.
Repository security is now a first-class architectural requirement.

The Observer foundation is now sufficiently validated to proceed toward permanent raw-data collection.

Next milestone: Immutable JSONL Snapshot Logger.


