# Decisions log - Vireo Audio support tickets

Format: what I decided, why, and the evidence. Anything the brief left unclear
is decided here, not asked.

## A. Data handling

| # | Decision | Why | Evidence |
|---|---|---|---|
| 1 | Legacy `resolved_at` + 330 minutes | Policy s9: legacy resolution times were rebuilt from a UTC log, the helpdesk shows IST | Before: 2,379 negative durations, legacy median -202 min. After: 0 negatives, legacy percentiles match helpdesk (median 128 vs 122) |
| 2 | No rescaling of `refund_amount_inr` | I suspected legacy was in paise; the data says no | Median refund 2,499 (helpdesk) vs 2,249 (legacy), same scale |
| 3 | No rows removed as duplicates | Policy s9 says some legacy tickets were re-imported | 0 repeated ticket_ids; 0 cross-system matches on two exact checks (same customer+product+time; same customer+product+message within 2 days) |
| 4 | Dropped a message-text-only duplicate rule | Generic messages ("I haven't received my order") collide across different customers | Flagged 430 rows, example groups were different customers on different dates |
| 5 | 139 tickets dated before 1 Jan 2025 flagged `in_window = False`, excluded from every statistic and money figure | Outside the stated 18-month window; breach rates on 3 to 32 tickets a month are noise | Kept in the file, flagged, never deleted |
| 6 | SLA/breach money figures use tickets from 1 Apr 2025 | Policy v3.2 is effective that date | Used in business number |
| 7 | `transfers` analysed on helpdesk rows only; blank is never filled with 0 | Field exists only after 14 Sep 2025 | 4,052 legacy rows blank |
| 8 | Status `closed` (auto-closed) excluded from handle-time stats | Resolution time is the 72-hour auto-close, not real handling | Policy s8 |
| 9 | Order join: by `order_id`, else latest order for same customer + sku on or before ticket date | 34.1% of tickets have no order_id | 65.9% id, 33.3% fallback, 0.8% none. With order_id hidden, fallback recovered the true order 95.6% of the time |
| 10 | Roster: current headcount, matched by `agent_id` (never name) | Two agents share the name Om Sharma | No joiners or leavers in the window (all start dates before Nov 2024, no end dates), so per-agent figures are not distorted by staffing changes |
| 11 | Escalations & Warranty (Tier 2) excluded from per-agent ranking | Policy s6: not comparable with Tier 1 on volume | |

## B. Categoriser

| # | Decision | Why | Evidence |
|---|---|---|---|
| 12 | Tags treated as the bot's first guess, not truth | Sameer: bot tags from the customer's opening question; agents rarely re-tag | Team shares equal tag shares exactly (Billing 21.8 = 21.8), so assigned_team is the tag |
| 13 | Label from `customer_message` only; agent notes used only as a cross-check | Notes do not exist at intake, so a live tool could not use them | |
| 14 | Rules-based (keywords + regex), no LLM, no paid calls | Rules got OTHER from 27.4% to 12.8% on readable patterns; cheap, explainable, repeatable | Paid API calls: 0. Cost per run: Rs 0 |
| 15 | Angry boilerplate ("I want my money back", "posting on twitter") cannot trigger a label by itself | Appears on login, hardware and refund tickets alike | Seen in samples |
| 16 | Stopped adding rules at 12.8% OTHER (target was under 15%) | More tuning risks fitting rules to samples I had seen | |
| 17 | Rules frozen after validation | Tuning on the 100 scored tickets would inflate accuracy | |
| 18 | Cancellation tickets assigned to Returns Desk | Policy is silent; closest owner is the refund/return team | 342 tickets. If they went to Billing instead: Billing 436 per agent, Returns 379, Logistics still highest at 589 |
| 19 | OTHER reported as "Unclassified", not defaulted to Frontline | 0 of 10 OTHER predictions were correct in validation | Owner accuracy fell from 83% to 79% when I changed this. I report 79% |
| 20 | Hand-labelling conventions: mic problems -> AUDIO_QUALITY; address change -> DELIVERY_NOT_RECEIVED; waiting on repair -> HARDWARE_FAULT_WARRANTY; Bluetooth stutter -> CONNECTIVITY; failure after a firmware prompt -> APP_FIRMWARE; no UNSURE used | No label exists for these; I chose the nearest owner team and kept it consistent | Borderline cases were judgement calls |

## C. Validation

| # | Decision | Why |
|---|---|---|
| 21 | 100 random tickets, labelled blind (no bot tag, no rule output) by me | Independent accuracy check; the form asks how I know it works |
| 22 | Report accuracy as a range, not a single number | n=100 gives about +/-8 points. Issue 77% (67.8 to 84.2); owner 79% (70.0 to 85.8) |
| 23 | Billing-tagged accuracy (n=19) reported as "similar to overall", nothing stronger | Sample too small |
| 24 | Per-class accuracy not reported | Several classes have 2 to 4 tickets |

## D. Business case

| # | Decision | Why / evidence |
|---|---|---|
| 25 | Business goal = cut Billing hand-offs from 31.4% to 10% | Hand-offs cost Rs 305 each plus excess SLA breaches. Hand-offs breach 33.3% vs 12.9% when Billing resolves (since 1 Apr 2025). Cost per hand-off about Rs 376 |
| 26 | Value of that goal about Rs 1.3 lakh a year (about Rs 33,000 a quarter), roughly 29% of one hire | 1,624 Billing tickets a year x 21.4% avoided x Rs 376 |
| 27 | 10% target is a judgement | Some hand-offs are legitimate (payment problem that turns out to be delivery), so it is a floor, not zero. Not measured |
| 28 | Hand-off = ticket resolved by a team other than `assigned_team` (resolved/closed only) | The transfers field is blank for legacy rows, and 5.1% of helpdesk tickets with transfers = 0 still ended in another team |
| 29 | Dropped "hand-offs cause repeat contacts" | Billing repeat rate is 31.3% with no transfer and 23.8% with a transfer, so the data points the other way |
| 30 | Dropped these money candidates | Repeat contacts: not driven by hand-offs. Rule violations (29 goodwill over cap, 2 refund + replacement): too small. Defect lot: weak (large PL2 lots run about 1.5x average, which a launch explains as well) |
| 31 | Wording: "intake routing", not "the chatbot is sabotaging Billing" | The data shows where tickets end up, not why. Customer choice and legitimate triage also contribute |
| 32 | Recommendation: do not give the two hires to Billing; fix routing; trial moving 2 Chat Frontline agents to Logistics for a quarter; hire in Logistics only if still over capacity | Billing is 12.0% of tickets by true owner (not 20.8%); Logistics is highest per agent (589, 676 with Unclassified spread). Chat Frontline is lightest (136) |
| 33 | I pushed back on the client's rule ("biggest team gets the hires") | Even on her own tags the biggest team is Chat Frontline (26.0%), not Billing; Billing was only the biggest category |
| 34 | Cost arithmetic uses 650 tickets a week, as the form asks | The export averages about 150 a week (about 190 recently), so the form figure does not match the data. Flagged here |

## E. Known problems (feeds "what is wrong with my work")

- Ticket numbers have gaps: 2,855 of 14,496 (19.7%) are missing. Cause unknown; if the gap is not random, shares could be biased.
- Ticket counts are not effort. No time-spent data exists; handle time is elapsed time including waiting.
- 12.8% of tickets are Unclassified. The validation errors are mostly address changes, repair waits, mic issues and "stuck connecting" cases that fall through to OTHER.
- Rules were written after reading real tickets, so accuracy may be slightly optimistic.
- 100-ticket sample: wide margin; Billing-tagged subset only 19.
- Per-agent figures are 18-month totals on one roster, for comparison only.
- Cancellation owner is an assumption.
- Hand-off target of 10% is a judgement.
- Apostrophe rule ("doesn't see it in the list"): OTHER stayed at 12.8% after the fix; not verified that it works.