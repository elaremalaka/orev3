# Replay Architecture

Replay reconstructs historical decision points using only information that
would have been observable at the chosen decision time.

Replay responsibilities:

- load indexed historical rounds,
- reconstruct valid board state,
- enforce decision timing,
- reject incomplete or invalid cases,
- expose outcome labels only after decisions,
- support deterministic reproducibility.

Replay is an extraction and evaluation layer. Routine exploratory analysis
should consume versioned datasets instead of repeatedly replaying history.
