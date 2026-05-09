# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A take-home backend service for XBuild. It accepts field reports (customer + property + findings) from a mobile app and generates structured repair proposal drafts via a deterministic rules-based pipeline.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server (from repo root)
uvicorn gateway.main:app --reload

# Run all tests
pytest

# Run a single test file
pytest tests/workers/test_matcher.py

# Run a single test by name
pytest tests/workers/test_matcher.py::test_shingle_match -v
```

The SQLite database is created automatically at `data/proposals.db` on first run.

## Architecture

The system is organized as a simulated multi-service architecture — each top-level folder represents a service that could be independently deployed.

```
gateway/        HTTP layer (FastAPI). Thin adapter only — no business logic here.
orchestrator/   Pipeline coordinator. Sequences workers; owns error handling.
workers/        One subfolder per pipeline step (each = a simulated microservice).
storage/        Data access layer. The only code that touches SQLite.
```

### The Transformation Pipeline

`POST /reports/:id/generate-proposal` runs a `PipelineRunner` that sequences five workers in order:

```
ValidatorWorker → NormalizerWorker → MatcherWorker → PricerWorker → AssemblerWorker
```

A single `PipelineContext` dataclass (defined in `orchestrator/context.py`) flows through all steps. Each worker reads from context fields set by prior steps and writes its own output fields. Workers are pure functions over context — they don't touch the database and don't call each other.

The `PipelineRunner` in `orchestrator/pipeline.py` is a simple loop: `for worker in self.workers: ctx = worker.run(ctx)`. Adding a new step means creating a new worker class and inserting it in the list in `gateway/main.py`.

### Worker Responsibilities

| Worker | Input (from ctx) | Output (to ctx) |
|--------|-----------------|-----------------|
| `ValidatorWorker` | `raw_input` | raises `ValidationError` → HTTP 422, or sets `ctx.validated = True` |
| `NormalizerWorker` | `raw_input` | `ctx.report_input` (typed dataclasses) |
| `MatcherWorker` | `ctx.report_input.findings` | `ctx.matches` — list of `(finding, catalog_item, match_reason)` |
| `PricerWorker` | `ctx.matches` | `ctx.priced_items` — list of `PricedLineItem` |
| `AssemblerWorker` | `ctx.priced_items` | `ctx.proposal_draft` — the final `ProposalDraft` |

### Matching Logic

`workers/matcher/catalog.py` holds the 10-item line item catalog as Python dataclasses (not in the DB — it's code, not runtime data). Each catalog item has a `keywords` list. The matcher scores each catalog item by counting keyword hits in `(finding.title + " " + finding.notes).lower()`. Highest score wins; ties resolved by catalog order. Score of 0 → fallback to `general.assessment_tm`.

### Pricing Formula

```python
severity_mult = {"low": 0.8, "medium": 1.0, "high": 1.5}[severity]
photo_mod = min(len(photos) * 25, 150)
estimated_cost = round((base_price * severity_mult + photo_mod) / 10) * 10
```

All monetary values stored as integer dollars (nearest $10 — no fractional values exist).

### Storage / Versioning

The `proposals` table is **append-only**. Every call to `generate-proposal` inserts a new row with `version = MAX(version) + 1` for that report. Proposals are never updated or deleted — this gives a free audit trail. `GET /proposals/:id` returns the latest version; `GET /reports/:id/proposals` lists all versions.

Findings are stored normalized in their own table (one row per finding) linked by `report_id`. The full submitted JSON is also stored in `reports.raw_json` as a belt-and-suspenders measure.

### ID Format

All IDs use a type prefix + 12-char hex: `rpt_`, `prop_`, `fnd_`, `li_`. This makes misrouted IDs immediately visible (passing a `prop_` ID to a reports endpoint returns 404, not wrong data).

## Key Invariants

- Every finding produces **exactly one** line item — never zero, never more than one.
- Proposals are immutable once created. Re-running `generate-proposal` creates a new version, never overwrites.
- The pipeline is deterministic: same input always produces the same proposal.
- Workers never import from `storage/` — only the route handlers and orchestrator do.
