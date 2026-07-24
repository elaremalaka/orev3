# Analysis Architecture

Analysis modules read versioned datasets and produce reproducible tables,
figures, and reports.

They must:

- validate their input assumptions,
- identify unavailable fields,
- separate descriptive findings from predictive claims,
- emit machine-readable results,
- emit a human-readable report,
- include dataset metadata.

Analysis code does not create live allocations.
