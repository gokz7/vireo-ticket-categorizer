# Vireo Ticket Categorizer

Reads Vireo Audio's support tickets, labels each ticket's real issue from the
customer's message, works out which team should own it, and compares that with
where the chat bot sent it. The output answers one question: which team needs
headcount?

It uses fixed keyword rules. There are no paid API calls, so one run costs Rs 0.

## What you need
- Python 3.10 or newer
- The data pack files in `data/`: `tickets.csv`, `agents.csv`, `orders.csv`,
  `customers.csv`, `products.csv`
- `validation/hand_labels.csv` (included): my hand labels for 100 random
  tickets, used to measure accuracy. Do not overwrite it.

## Setup
1. `python -m venv .venv`
2. Activate it:
   - Windows: `.venv\Scripts\activate`
   - Mac/Linux: `source .venv/bin/activate`
3. `pip install -r requirements.txt`
4. Put the 5 CSV files in `data/`.

## Run
From the project root:

```
python src/run_all.py
```

This runs the six steps in order and stops at the first error. It takes about
[X] seconds on a laptop.

| Step | Script | What it does |
|---|---|---|
| 1 | `01_audit.py` | Read-only data checks (shapes, missing values, duplicates, timestamps) |
| 2 | `02_clean.py` | Fixes legacy timestamps (+330 min), adds flags, joins orders. Removes no rows |
| 3 | `03_categorise.py` | Labels each ticket's issue and owning team from the message text |
| 4 | `04_validate.py` | Scores the labels against my 100 hand labels |
| 5 | `05_charts.py` | Workload tables and two charts |
| 6 | `06_business_number.py` | The hand-off cost and the value of the goal |

## Outputs (in `outputs/`)
- `tickets_clean.csv`, `tickets_labelled.csv`: row-level data
- `validation_detail.csv`: my label vs the tool's label, 100 rows
- Two charts (PNG): monthly tickets by issue, and by assigned team vs owning team
- Tables printed in the terminal (see below)

## What a correct run shows
If your numbers differ much from these, something is wrong.

| Check | Expected |
|---|---|
| Rows in `tickets.csv` | 11,780 (11,641 in the 18-month window) |
| Legacy resolution times | No negative values after cleaning |
| Tickets left unclassified | 12.8% |
| Issue accuracy (n=100) | 77% (95% range 67.8 to 84.2) |
| Owning-team accuracy (n=100) | 79% (95% range 70.0 to 85.8) |
| Billing-assigned tickets handed to another team | about 31% |
| Value of cutting those hand-offs to 10% | about Rs 1.3 lakh a year |
| Tickets per agent, by true owner | Logistics highest (about 589) |

## Key decisions
Written in `logs/decisions.md`. AI use is in `logs/ai_log.md`.

## Known limits
- Ticket counts are not effort: there is no time-spent data.
- The tool left 12.8% of tickets unclassified, and none of the 10 sampled
  unclassified tickets were correct. They are reported as their own group.
- Accuracy comes from 100 tickets I labelled myself, so it is a range of about
  +/-8 points. The rules were written after reading real tickets, so it may be
  slightly optimistic.
- 19.7% of ticket numbers are missing from the export; the cause is unknown.
- Cancellations are assigned to Returns Desk by assumption.
- The 10% hand-off target is a judgement, not measured.
- Per-agent figures use one roster for the whole window.
