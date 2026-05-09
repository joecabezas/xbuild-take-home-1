# Backend Take-Home: Field Report → Proposal Engine

## Goal

Build a small backend service that accepts “field reports” from a mobile app and generates a structured proposal draft.

This mirrors a real XBuild workflow: information captured onsite becomes a proposal for a homeowner.

In production, parts of this transformation may be AI-assisted. For this exercise, you should implement a deterministic proposal generation pipeline.

We care far more about:

- How you model the system  
- How you structure the transformation pipeline  
- API and data design  
- Validation and invariants  
- Clarity of implementation  
- How your design could evolve over time

than we do about construction-domain correctness.

---

## Timebox

Please spend approximately **1–2 hours** on this.

---

## Tech

Use any language/framework you’re comfortable with.

Python is preferred, but not required.

In-memory storage or SQLite is completely fine.

You are encouraged to use AI coding tools (Claude Code, Cursor, Codex, etc.).

---

# Product Context

Assume we have a mobile app used by contractors onsite.

The app submits a “field report” containing:

- Customer info  
- Property info  
- A list of findings  
- Optional notes/photos per finding

Your backend service should:

1. Accept field reports  
2. Store them  
3. Generate proposal drafts derived from them  
4. Expose APIs to retrieve both reports and proposals

No authentication is required.

No real file uploads are required — treat photo references as strings.

---

# API Surface

You may structure your API however you’d like, but at minimum we expect functionality equivalent to:

---

## `POST /reports`

Accepts JSON like:

{

  "customer": {

    "name": "Jane Smith",

    "email": "jane@example.com"

  },

  "property": {

    "address": "123 Main St, Austin, TX",

    "type": "single\_family"

  },

  "findings": \[

    {

      "title": "Missing shingles",

      "severity": "high",

      "notes": "Visible damage on north slope",

      "photos": \["photo-1.jpg", "photo-2.jpg"\]

    },

    {

      "title": "Clogged gutters",

      "severity": "medium",

      "notes": "",

      "photos": \[\]

    }

  \]

}

Returns:

{

  "reportId": "rpt\_123"

}

---

## `GET /reports/:id`

Returns the stored report.

---

## `POST /reports/:id/generate-proposal`

Generates a proposal draft derived from the report.

Returns:

{

  "proposalId": "prop\_456"

}

---

## `GET /proposals/:id`

Returns something like:

{

  "proposalId": "prop\_456",

  "reportId": "rpt\_123",

  "summary": "Exterior repairs for 123 Main St",

  "lineItems": \[

    {

      "code": "roof.patch\_shingles",

      "category": "roofing",

      "description": "Replace missing/damaged shingles in affected areas.",

      "estimatedCost": 1400,

      "sourceFinding": "Missing shingles",

      "matchReason": "Matched roof \+ shingle damage keywords"

    }

  \],

  "total": 1400

}

---

# Proposal Generation

The goal of this exercise is to build a deterministic proposal generation engine.

For each finding in the report:

- Choose the best matching proposal line item from the catalog below  
- Generate an estimated cost using the pricing rules  
- Include some explanation of why the match was chosen

We are intentionally **not** asking you to use AI for proposal generation.

Instead, think of this as building:

- a deterministic fallback system  
- a rules-based proposal engine  
- or an explainable layer underneath a future AI workflow

Your implementation should:

- Always generate a proposal from valid input  
- Be deterministic and explainable  
- Handle ambiguous findings gracefully  
- Prefer simplicity and clarity over complexity

---

# Line Item Catalog

For each finding, generate exactly **one** proposal line item.

If no strong match exists, fall back to:

general.assessment\_tm

| code | category | description | basePrice |
| :---- | :---- | :---- | ----: |
| `roof.leak_investigation` | roofing | Investigate and stop active leak; seal/repair likely entry points. | 650 |
| `roof.patch_shingles` | roofing | Replace missing/damaged shingles in affected areas. | 900 |
| `roof.reflash_penetration` | roofing | Repair/replace flashing at affected areas to restore watertightness. | 750 |
| `roof.vent_repair` | roofing | Inspect and repair/replace roof vent components as needed. | 400 |
| `gutters.clean_flush` | gutters | Clean and flush gutters and downspouts. | 250 |
| `gutters.resecure` | gutters | Re-secure gutters; adjust hangers and slope for proper drainage. | 350 |
| `siding.repair_local` | siding | Repair/replace localized siding/trim damage. | 700 |
| `openings.reseal` | windows\_doors | Reseal/repair window/door trim to reduce water/air intrusion. | 450 |
| `exterior.paint_prep_spot` | paint | Prep and spot-paint affected exterior areas to match existing finish. | 400 |
| `general.assessment_tm` | general | On-site assessment and minor repairs (time & materials). | 300 |

---

# Example Findings

These are intentionally imperfect / ambiguous examples.

\[

  {

    "title": "Missing shingles",

    "severity": "high",

    "notes": "Visible roof damage"

  },

  {

    "title": "Water staining near window",

    "severity": "medium",

    "notes": "Possible failed seal"

  },

  {

    "title": "Loose gutter section",

    "severity": "low",

    "notes": "Pulling away from fascia"

  },

  {

    "title": "Unknown exterior damage",

    "severity": "medium",

    "notes": "Needs review"

  }

\]

---

# Pricing Rules

estimatedCost \= basePrice \* severityMultiplier \+ photoModifier

Severity multipliers:

- low → 0.8  
- medium → 1.0  
- high → 1.5

Photo modifier:

- \+$25 per photo  
- capped at $150

Round to the nearest $10.

---

# Validation & Constraints

You may choose your own validation strategy, but your system should handle invalid input reasonably.

Some examples:

- Missing customer name  
- Missing property address  
- Empty findings array  
- Unknown severity values

No auth required.

No real file uploads.

Keep the system simple and readable.

---

# Deliverables

Please submit:

- A GitHub repository  
- A short README covering:  
  1. How you modeled reports vs proposals  
  2. Important invariants or design decisions  
  3. How you would evolve the system if:  
     - proposal generation became async  
     - AI replaced deterministic matching  
     - proposal versioning/history became important

You’ll receive separate instructions about where to share the repository.

---

# What We Care About

We are evaluating:

- API and data modeling  
- Code organization  
- Deterministic business logic  
- Validation and edge-case handling  
- Clarity and maintainability  
- Tradeoff decisions under time constraints

We are not evaluating:

- Construction-domain expertise  
- Pixel-perfect polish  
- Production-scale infrastructure  
- Fancy UI

A clean, thoughtful, reasonably-scoped solution is much more valuable than a large or over-engineered one.  
