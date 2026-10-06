# AI log

## 1. What I used

| Tool | Model [fill in] | Used for | Paid API calls in the final tool |
|---|---|---|---|
| Gemini | [e.g. Gemini 2.5 Pro, via the web app] | Wrote the Python scripts (audit, cleaning, exploration, categoriser, validation, charts, business number) | 0 |
| Claude | [model, via claude.ai] | Mentor/reviewer: read the brief, email thread, policy and README for traps; checked Gemini's scripts and arithmetic; challenged my conclusions; drafted the memo | 0 |
| Me (no AI) | n/a | Chose the business goal and the headcount answer; hand-labelled 100 validation tickets blind; decided what to cut | n/a |

Cost: [subscription or free tier; amount, or "free tier, Rs 0"]. The final tool
itself makes no AI calls: one run costs Rs 0.
Time spent: [about X hours total].

## 2. Prompts that mattered (short)

| # | Tool | Prompt (summary) | Result |
|---|---|---|---|
| 1 | Gemini | Long setup prompt: task, files, email facts, policy facts, 9 hypotheses to test, 7 workflow steps. "Reply Ready, write no code until I ask." | Gave Gemini the full context once |
| 2 | Gemini | Step 1: read-only data audit | Wrote 01_audit.py (needed fixes, see section 3) |
| 3 | Gemini | Step 2: cleaning with flag columns, never dropping rows | 02_clean.py: timezone fix, flags, order join |
| 4 | Gemini | Compact exploration scripts (02b to 02e): hand-off map, breaches by team and channel, transfers, repeats, roster | Evidence for the business case |
| 5 | Gemini | Categoriser: ordered regex rules with typo tolerance, plus issue-to-owner mapping from policy s6 | 03_categorise.py: OTHER 27.4% |
| 6 | Gemini | Added rules for patterns seen in OTHER, forbidden to tune on the 100 validation tickets | OTHER 17.7% then 12.8% |
| 7 | Gemini | 04_validate.py: accuracy, Wilson CI, confusions by channel and class | Issue 77%, owner 79% |
| 8 | Gemini | 05_charts.py and 06_business_number.py | Workload tables, charts, the Rs figure |

## 3. Where AI got it wrong, and what I changed

| # | Tool | Mistake | What I did |
|---|---|---|---|
| 1 | Gemini | First audit script never checked Priya's 22% and 16%, printed only 5 months and 5 columns, used mean refund (outliers), and labelled assigned_team as "True Team" | Rewrote with category and team shares, medians, full columns, and "bot tag" labels |
| 2 | Gemini | Duplicate check matched on message text alone; flagged 430 rows, but they were generic phrases from different customers | Dropped the rule; replaced with exact customer+product+time and message+2-day checks (0 matches) |
| 3 | Gemini | Said the Billing hand-off "proves the chatbot is sabotaging Billing" and that hand-offs drive Billing's repeat contacts | Softened to "intake routing"; checked repeats: 31.3% with no transfer vs 23.8% with a transfer, so dropped the claim |
| 4 | Gemini | "Top 5 lots by defect rate" picked lots with only 20 to 25 orders | Discarded the defect-lot story (the larger lots run about 1.5x average) |
| 5 | Gemini | Created the apostrophe fix for "doesn't see it in the list"; OTHER stayed at 12.8% afterwards | [Say whether fixed. If not, list as a known issue] |
| 6 | Gemini | Pandas Timedelta DeprecationWarnings left in scripts | [Say whether fixed] |
| 7 | Claude | Guessed legacy refunds were in paise (100x) | Data showed same scale; no rescaling |
| 8 | Claude | Guessed duplicate re-imports would show up | Two exact checks found none |
| 9 | Claude | Said there was no headcount history in the roster | Wrong: from_date exists. No joiners or leavers in the window |
| 10 | Claude | Misread the 100-ticket label file as 300 because VS Code counts lines inside multi-line cells | Corrected after seeing the Excel view (data ends at row 101) |
| 11 | Claude | Early "workload" ranking counted only who closed the ticket | Re-did on true owner from message text |
| 12 | Claude | Suggested typing the full label list into the Excel dropdown (255-char limit) | Used a helper list in column H |

## 4. What I threw away

- Cross-system duplicate removal (nothing found).
- Message-text duplicate rule (false positives).
- Repeat contacts as a hand-off cost (contradicted by the data).
- Defect-lot theory (weak; consistent with a product launch).
- Rule violations as a money number (29 goodwill over cap, 2 refund+replacement: too small).
- Paid-LLM fallback for OTHER: considered and not built. Rules reached 12.8% for free, and the 0-of-10 OTHER accuracy shows the gap, so I report it as Unclassified instead of hiding it.
- Gemini's exploration summaries and whole-output pastes. I used only the compact tables.
- Further rule tuning after validation (would inflate accuracy).
- Gemini's claim wording ("sabotage", "proves").

## 5. Where AI helped, where it wasted my time

Helped: reading the email thread and policy for traps (timezone, blank vs zero,
shared name, tier 2, closed vs resolved); writing the scripts fast; checking
arithmetic; spotting that "biggest team" and "biggest category" are different
things.

Wasted time: the long outputs I pasted back (token cost and waiting);
Gemini's over-confident conclusions; Excel dropdown instructions; the file-size
confusion.

## 6. What I did without AI

- Read all documents myself first.
- Hand-labelled 100 random tickets blind (no bot tag, no rule output).
- Chose the business number and the hiring recommendation.
- Decided which findings to cut.