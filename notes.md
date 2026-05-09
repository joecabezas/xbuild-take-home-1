# Notes and Future Work

## Tradeoffs

- **Code organization**
  - Each worker is currently a module within this repository for simplicity. In a production setup, each worker should live in its own repository to allow independent versioning, deployment, and ownership by separate teams.

- **Matching strategy**
  - The initial implementation used a keyword-based scoring system, where each catalog item had a list of keywords and the matcher counted hits against the finding's title and notes. This approach is brittle: it requires manually maintaining keyword lists, fails on synonyms and varied field language, and is prone to ambiguous matches when keywords overlap across catalog items.
  - A separate branch (`semantic-matcher`) replaces this with a local embedding model (`all-MiniLM-L6-v2` via `sentence-transformers`). Catalog descriptions are embedded once at startup and stored as a matrix. At match time, the finding text is embedded and scored against all catalog items using cosine similarity. The highest-scoring item above a configurable threshold wins; otherwise the request falls back to `general.assessment_tm`.
  - The embedding model runs fully locally — no external API calls.
  - The matcher runs in its own isolated Docker container with the model baked in at build time, so there is no download on startup.
  - The matching is deterministic: the same input always produces the same embedding vector and therefore the same match. The only theoretical source of non-determinism would be floating-point tie-breaking across platforms, but `np.argmax` resolves ties by returning the first occurrence (i.e., catalog order), so the output is stable.
  - The `SIMILARITY_THRESHOLD` (default `0.35`) was calibrated by scoring all known-good test inputs to find the minimum score of a correct match, then verifying that genuinely unrelated inputs fall below it. The threshold and model name are both configurable via environment variables.
