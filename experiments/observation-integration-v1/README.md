# Observation and integration v1

This package freezes three interfaces that can be built before scientific MYSTIC data are available:

1. an observation record that distinguishes calibration nights from untouched validation nights;
2. a radiance-spectrum request/response API;
3. an end-to-end star-visibility integration API.

The included provider and visibility threshold are synthetic contract implementations only. They prove wiring, hashes, validation, out-of-domain propagation, and separation of calibration from validation. They are not physical or psychophysical models and must not be used for production times.
