# POST_V1 low-altitude libRadtran HTTP decoding provenance probe v1

This is an isolated, solver-free, nonprotected provenance probe. It does not alter the V1 stellar transport floor, production code, scientific identities, seeds, ordinals, Taylor/Jerusalem fitting, or any protected result.

## Frozen question

The build-1 conda recipe binds the literal URL `http://www.libradtran.org/download/libRadtran-2.0.6.tar.gz` to SHA-256 `999e47f4af4b5df6f85a6887fc105fc8f6e1a7cee89a3124f69ac8d8912c8e85`. A prior literal-HTTP recovery recorded wire bytes SHA-256 `64930cc40b6e4a37aa220520974d330fc1563796f466a649b2238131f2d69840` with `Content-Encoding: x-gzip`.

The probe freezes two representations before observing the fresh result:

1. **wire**: bytes returned by the literal HTTP route without content decoding;
2. **http-content-decoded**: deterministic gzip decoding of those exact wire bytes, and only when the response declares `Content-Encoding: gzip` or `x-gzip`.

No HTTPS substitution is permitted. Redirects are recorded. A match is reported only when one of those two byte representations has the exact recipe SHA-256. The matching bytes are preserved as an immutable workflow artifact; nonmatching large bodies are deleted before upload.

## Exact runtime/provenance binding already recovered

Historical provenance artifact `8907428859` (digest `sha256:2428a148fbcac0e68fe9bec41ecf5f53b775373786f025da759297246e9b4467`, head `85248fcf7d0c3f1e1a79df69f362353998ca3e81`) binds:

- exact package `rubin-libradtran-2.0.6-py312pl5321he9373c2_1.conda` SHA-256 `9090033a39a7e963ecabb31d5cbd264330c64ec1c4cb5f44be2e70f10cbc54c2`;
- packaged and installed `bin/uvspec` SHA-256 `2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3`;
- embedded recipe source SHA-256 `999e47f4af4b5df6f85a6887fc105fc8f6e1a7cee89a3124f69ac8d8912c8e85`;
- build metadata `conda-build 26.1.0`, `conda 26.1.1`, `requests 2.32.5`, `urllib3 2.6.3`.

Exact upstream downloader semantics are frozen by source refs:

- conda `26.1.1`, commit `a0b1779edb6df26600b9aa6f2bc9d466f512b0ed`: `download_inner()` writes `resp.iter_content(...)` chunks into the target later checked by SHA-256;
- Requests `v2.32.5`, commit `b25c87d7cb8d6a18a37fa12442b5f883f9e41741`: `iter_content()` invokes urllib3 `raw.stream(..., decode_content=True)`;
- urllib3 `2.6.3`, commit `0248277dd7ac0239204889ca991353ad3e3a1ddc`: `x-gzip` is explicitly treated as gzip.

Thus an exact `999e47...` match in the `http-content-decoded` representation is a named source/runtime equivalence candidate; it does not by itself change any V1 gate or floor. Subsequent source inspection remains POST_V1 and must preserve the >=5.0 degree seam exactly.
