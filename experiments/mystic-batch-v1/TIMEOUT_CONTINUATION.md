# Held-out timeout continuation

Run 30871800549 produced four valid g01 held-out blocks and four g06 timeouts at the exact 1,800-second process limit. The timeout records contain no radiance output and are not scientific observations.

This continuation never re-runs g01 and never uses GitHub's Re-run feature. It audits and preserves the four immutable g01 artifacts, then replaces the four timed-out 400-million-photon g06 jobs with eight fresh 200-million-photon subblocks using new seeds. Total requested g06 photons remain 1.6 billion, while eight independent blocks improve variance estimation and are expected to fit the bounded per-case runtime.

A new one-purpose ordinal-6 authorization is required. Passing computational confirmation still does not establish atmospheric realism, observational validity, or production-model readiness.
