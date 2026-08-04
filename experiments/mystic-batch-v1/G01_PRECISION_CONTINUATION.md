# g01 fixed precision execution

This stage consumes the reviewed fixed proposal from the successful g01 diagnosis workflow. It preserves held-out ALIS blocks 1–4, runs exactly four fresh 600 nm ALIS blocks 5–8 with seeds 84601–84604 and 50M photons each, and makes the final fixed 8% RSEM decision. No threshold relaxation, block deletion, retry, or automatic additional block is permitted.
