# Tier-1 precision continuation proposal v1

Proposal-only infrastructure for bounded precision continuation after an independently audited Tier-1 dataset exists.

Safety boundary:

- no scientific dispatch;
- no active authorization;
- no GitHub re-run;
- no seed reuse;
- no threshold changes;
- no block deletion or selective inclusion;
- no surrogate fitting or production promotion.

Frozen classifications use RSEM: `<= 0.05` is `PRECISION_TARGET_MET`, `> 0.05 and <= 0.08` is `PRECISION_ACCEPTED`, and `> 0.08` is `ADAPTIVE_CONTINUATION_REQUIRED`.
