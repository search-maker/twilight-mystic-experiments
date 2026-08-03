# Twilight sampling and surrogate v1

This package prepares the non-executing modeling path that can proceed while the MYSTIC reference and batch infrastructure are reviewed.

It contains three deliberately bounded components:

1. **Two-stage allocation** — a fixed pilot block count followed by at most one deterministic second allocation. Every additional block must use a fresh seed. There is no open-ended sequential stopping.
2. **Adaptive baseline selection** — proposes midpoint cases where a frozen interval-width or curvature-plus-uncertainty target is exceeded.
3. **Surrogate harness** — performs group-safe train/validation/withheld splitting, weighted log-luminance regression, withheld metrics, and explicit out-of-domain detection.

The split unit is `groupId`, representing one physical input point. All independent seeds or blocks for the same point must share that group so no geometry leaks between training and validation/withheld sets.

Nothing in this package invokes `uvspec`, MYSTIC, or any scientific workflow. Synthetic success does not authorize a LUT, production model, physical-validity claim, or default-model change.
