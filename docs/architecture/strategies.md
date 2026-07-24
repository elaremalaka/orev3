# Strategy Architecture

A strategy converts observable board state or model output into an allocation.

Every strategy must define:

- evidence source,
- decision time,
- required features,
- eligibility gate,
- allocation method,
- sizing,
- retry and failure behavior,
- duplicate-deployment protection,
- capital limits,
- kill conditions.

The strategy layer should remain small. Research complexity belongs upstream.
