# Model Architecture

Models estimate time-valid relationships between observable features and future
outcomes.

Required practices:

- chronological train/validation/test separation,
- walk-forward evaluation where practical,
- permanent baseline comparison,
- calibration and stability analysis,
- explicit feature lists,
- saved configuration and metrics,
- no tuning against the final holdout.

Simple models should be tested before complex models.
