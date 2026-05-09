# Proposal Engine

A backend service that accepts field reports from a mobile app and generates structured repair proposal drafts via a deterministic, distributed pipeline.

## Running

```bash
docker-compose up --build
```

API available at `http://localhost:8000`. RabbitMQ management UI at `http://localhost:15672` (guest/guest).

### Quick test

```bash
# 1. Submit a field report
curl -s -X POST http://localhost:8000/reports \
  -H "Content-Type: application/json" \
  -d '{
    "customer": {"name": "Jane Smith", "email": "jane@example.com"},
    "property": {"address": "123 Main St, Austin, TX", "type": "single_family"},
    "findings": [
      {"title": "Missing shingles", "severity": "high", "notes": "Visible damage on north slope", "photos": ["photo-1.jpg", "photo-2.jpg"]},
      {"title": "Clogged gutters", "severity": "medium", "notes": "", "photos": []}
    ]
  }'
# → {"reportId": "rpt_..."}

# 2. Generate a proposal (runs the async pipeline)
curl -s -X POST http://localhost:8000/reports/rpt_.../generate-proposal
# → {"proposalId": "prop_..."}

# 3. Fetch the proposal
curl -s http://localhost:8000/proposals/prop_...

# 4. View proposal version history for a report
curl -s http://localhost:8000/reports/rpt_.../proposals
```

### Running tests (no Docker needed)

```bash
pip install -e shared/ pika pytest fastapi pydantic
pytest tests/ -v
```

---

## Design

### How reports and proposals are modeled

A **report** is the raw input as submitted — customer, property, and a list of findings. It is stored verbatim and never mutated. Each finding is also stored as a normalized row (title, severity, notes, photos as a JSON string array).

A **proposal** is a derived, immutable output generated from a report. It contains one line item per finding, a computed total, and an explicit `matchReason` for every line item explaining which keywords drove the catalog match. Proposals are never updated in place.

The two are linked by `report_id` but intentionally separate: a report is ground truth, a proposal is an interpretation of it. Regenerating a proposal creates a new version — it does not overwrite the previous one.

### Invariants and design decisions

**One line item per finding, always.** The matcher scores each finding against the 10-item catalog using keyword counts. If nothing scores above zero, it falls back to `general.assessment_tm`. This guarantees every valid report produces a complete proposal.

**Deterministic matching.** Given the same finding title and notes, the matcher always returns the same catalog item. Ties (equal keyword scores) are broken by catalog order, which is fixed. This makes proposals reproducible and auditable.

**Proposals are append-only.** Each call to `POST /reports/:id/generate-proposal` inserts a new proposal row with an incrementing version number. Old proposals remain retrievable by their ID. The `GET /reports/:id/proposals` endpoint lists the full history.

**The catalog is code, not data.** The 10 catalog items and their keyword trigger lists live in `workers/matcher/catalog.py`. Changing the catalog requires a deploy, but the matching rules are version-controlled alongside the code that uses them.

**Photos are strings throughout.** No binary storage, no S3 — a photo reference is just a string in the findings array. The photo count affects pricing (via the photo modifier), nothing more.

**SQLite with WAL mode** is shared between the gateway and assembler containers via a named Docker volume. WAL mode allows concurrent reads without blocking the writer.

### Architecture: distributed pipeline over RabbitMQ

Each pipeline step runs as an independent Docker container consuming from its own RabbitMQ queue:

```
gateway → [validate] → ValidatorWorker
                     → [normalize] → NormalizerWorker
                                   → [match] → MatcherWorker
                                             → [price] → PricerWorker
                                                        → [assemble] → AssemblerWorker
                                                                      → [results] → gateway
```

The `PipelineContext` dataclass is the message body — it carries all state as a JSON-serializable dict. Each worker reads from it, enriches it, and publishes it to the next queue. Workers never share memory or call each other directly.

The gateway uses the RabbitMQ **request-reply pattern**: it declares a temporary `reply_{job_id}` queue per request, publishes the initial context, and waits up to 30 seconds for a result. This keeps the gateway stateless.

Any worker can short-circuit the pipeline by publishing directly to `results` with `status=failed` — the gateway surfaces this as an HTTP error.

### How this evolves

**If proposal generation became async (returning a job ID immediately):** The gateway route already publishes to a queue and waits — the only change needed is to stop waiting. Return `{jobId, status: "pending"}` immediately, persist the `reply_to` queue name, and poll or use a webhook to notify when complete. The workers and pipeline are untouched.

**If AI replaced deterministic matching:** Only `MatcherWorker` changes. Its queue contract is identical — it receives a context with `report_input` and publishes one with `matches`. The `matchReason` field already accommodates free-text LLM reasoning. Every other worker, the gateway, and the DB schema are unaffected.

**Proposal versioning/history:** Already implemented. The `proposals` table is append-only with a `version` column. `GET /reports/:id/proposals` returns the full history. Each `prop_` ID permanently addresses a specific version.
