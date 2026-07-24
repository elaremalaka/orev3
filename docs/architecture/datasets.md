# Dataset Architecture

A research dataset is an immutable snapshot derived from a defined replay
configuration.

Every dataset must record:

- dataset version,
- schema version,
- feature version,
- source path,
- replay timing,
- acceptance and rejection counts,
- row counts,
- missingness,
- generation time,
- content path,
- manifest path.

Changing feature semantics requires a new version.
