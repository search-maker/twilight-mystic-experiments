# Twilight model readiness v1

This package prepares the work that can proceed while the held-out MYSTIC confirmation runs.

It keeps three scientifically distinct objects separate:

1. **Reference anchors** — six audited cross-geometry points. They are external validation points and are never fitted by the surrogate.
2. **Training design** — a deterministic 96-geometry, five-dimensional space-filling proposal with a disjoint internal holdout set and two independent ALIS blocks per geometry. It is pre-split into a 48-geometry provisional tier and a 48-geometry completion tier, so an early surrogate and error map can be produced without changing the final design.
3. **Production validity** — not granted by either object. Observation validation, wider atmospheric sensitivity testing, and explicit model authorization remain required.

The ALIS importance-wavelength policy is variance reduction only. It does not alter the expected radiative-transfer solution. Photon allocation rises with solar depression, and later continuation is permitted only for geometries that fail a predeclared precision target.

Nothing in this package dispatches MYSTIC, trains a surrogate, changes a production default, or claims observational validity.

The provisional tier is not a production shortcut. Its holdout errors decide where extra precision is needed while the second tier remains predeclared and unchanged.
