# Cross-geometry pilot v1

This is a proposal-only screening batch. It does not authorize `uvspec`, MYSTIC, syntax checks, solver execution, production use, or a default-model change.

The frozen pilot contains six physical geometries. Each geometry has two independent 20-million-photon blocks for `reference-vroom` and two for `alis`, for 24 cases and 480 million configured photon histories total.

Coverage includes:

- Sun depression 4, 8, and 12 degrees;
- target altitude 10, 30, and 45 degrees;
- relative azimuth near the Sun, perpendicular, and opposite;
- AOD550 0.15 and 0.30;
- the exact 12-degree / 10-degree / 120-degree / AOD 0.15 reference bridge.

The pilot can only classify each geometry as screening agreement, screening discrepancy, needing more fresh blocks, or structural/execution failure. It cannot establish final cross-geometry validity. The stage-two rule adds two fresh blocks per method only where the pilot is noisy or discrepant, with a hard maximum of six blocks per method per geometry.
