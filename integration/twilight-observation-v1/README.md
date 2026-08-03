# Twilight observation and integration v1

This package defines the first stable boundary between field observations, instrument calibration, radiance outputs, and the star-visibility layer.

- Observation records require exact time, location, pointing, atmosphere, quality flags, calibration identity, and raw-file hashes.
- Dataset role is assigned by a frozen session-level split, so all records from one observing session are either calibration or validation and cannot leak across both.
- Camera and SQM conversions require explicit calibration parameters; no universal hidden zero point is assumed.
- The visibility API is a transparent signal-to-background margin model. It does not convert stellar magnitude or sky radiance by itself; those upstream conversions must be separately calibrated and validated.

Nothing here establishes that a specific observation, calibration, contrast threshold, or visibility prediction is physically valid.
