# Token budget plan

Part 5.4 of the manual. Written **before** the first `/implement` session.

> **Every percentage in this file is a pre-work ESTIMATE, not measured usage.**
> Nothing here comes from `notes/usage-ledger.csv`. Actual numbers will come
> from `uv run python scripts/usage_report.py` after T01 and T03 (Part 5.6),
> and the final report compares this plan against them.

## 1. Which models I can use

- **Confirmed in use:** Sonnet 5 and Sonnet 5.5 (the only models in the ledger so far).
  `~/.claude/settings.json` defaults to `sonnet`, effort `medium`.
- **Not yet confirmed for my Pro account:** Opus and `opusplan`, and Haiku.
  Before T01, run /model and update this table if other models are available.
  If Opus is not offered or is very costly on Pro,
  use the **Sonnet-only** column; the plan still works, just with less headroom
  on planning quality.
- I will not assume model names or availability beyond what `/model` shows.

## 2. Plan by stage (estimates, as % of ONE 5-hour window)

| Stage | Model (if listed by `/model`) | Sonnet-only fallback | Effort | Est. % of a 5h window |
|---|---|---|---|---|
| Setup Exercise A: context-threshold hook | Sonnet | same | medium | 5 |
| Setup Exercise B: `spend()` via `/tdd` | Sonnet | same | medium | 5 |
| `/grill` (one session, fresh window) | Opus / `opusplan` | Sonnet | high | 15 |
| `/to-spec` | Opus / `opusplan` | Sonnet | high | 10 |
| `/to-tickets` | Opus / `opusplan` | Sonnet | high | 10 |
| `/implement` + `/tdd`, **per ticket** (x8) | Sonnet | same | medium | 20 each, 160 total |
| `/code-review`, **per ticket** (x8) | Sonnet | same | high | 8 each, 64 total |
| Publish to Pages + submission chores | Sonnet or Haiku | Sonnet | low | 5 |
| **Subtotal** | | | | **~274** |
| Rework / drift / long-ticket buffer (+25%) | | | | ~68 |
| **Total** | | | | **~340** |

Notes on the numbers:
- Implementation is the biggest line because each ticket is a tracer bullet
  (model + route + template + tests) plus a test-first loop with reruns.
- Planning stages are guessed at high effort because a bad spec is the most
  expensive mistake to fix later, so I would rather spend here.
- The 8 tickets are T01–T08. The manual's 5.4 text says 9 tickets and the
  deliverables list says 7–9. T00 (walking skeleton) is already green and is
  not counted.

## 3. How many 5-hour windows?

~340% of one window is roughly **3.4 windows**, so plan for **3 to 4 windows**,
spread across sessions rather than back to back (a window resets on a rolling
5-hour basis). Rough spread:

| Window | Contents |
|---|---|
| 1 | Exercises A and B, grill, spec, tickets (~50%), then T01 (Stage 1 needs the first 3 tickets) |
| 2 | T02, T03, and their reviews; Stage 1 deploy and tag |
| 3 | T04–T06 with reviews |
| 4 (partial) | T07–T08, publish, buffer |

Stage 1 target is Tue Sep 29, 2:40 pm and Stage 2 is Tue Oct 6, 2:40 pm, so the
5-hour limit is unlikely to be the binding constraint. The weekly cap is.

## 4. The weekly cap is uncertain

Anthropic does not publish a token count for Pro, and does not say how large a
5-hour window is relative to the week. So I cannot convert windows into a
weekly percentage with confidence. Two illustrative scenarios (assumptions,
not facts):

- If one **full** 5h window costs about **5%** of the weekly cap: 3.4 windows is
  about 17% of a week. Comfortable.
- If one full window costs about **20%** of the weekly cap: 3.4 windows is about
  68% of a week. Workable, but with little room if I also use Claude for other
  courses.

The manual's sample output (5h 22% vs weekly 4% for one ticket) hints that a
full window is a meaningful fraction of the week, but that is an illustration
of the report format, not data about my account.

Other unknowns: whether Opus draws the weekly cap faster than Sonnet, when my
weekly meter resets (it may fall between Stage 1 and Stage 2, which would help),
and whether other Claude use this week counts against me.

**How this gets resolved:** the ledger records `five_h_pct` and `weekly_pct` per
turn. After T01 and T03, `usage_report.py --remaining N` gives measured weekly
cost per ticket and a FITS / TIGHT / OVER BUDGET verdict. I will replace the
guesses above with those numbers in the final report.

## 5. If the forecast is too high: what I simplify first

The seven required capabilities stay fixed: login, two roles, posts, pages,
admin console, user management, public site and publish. I reduce *cost per
capability*, in this order (cheapest to give up first):

1. **Effort and model.** Drop `/code-review` from high to medium, use Sonnet
   instead of Opus for planning, and `/clear` between every task.
2. **Polish beyond the requirement.** Plain, minimal CSS and templates; no
   themes, animations, or extra pages beyond what the capabilities need.
3. **Admin console depth.** Dashboard shows only the required counts; the content
   list filters by status and type only (no search, sorting options, or
   pagination); the editor preview is a plain sanitized render.
4. **Pages and posts extras.** Flat navigation ordered by title (no drag order or
   nesting); no tags, categories, or revision history; simple timestamps.
5. **User management minimalism.** Create, change role, deactivate as plain forms;
   no password-reset flow or email.
6. **Split or merge tickets.** Split any ticket that runs long (manual 6.4) and
   merge two thin tickets if overhead outweighs the work.
7. **Last resort:** Plan B backend (Part 9), declared with a `Backend:` trailer
   on commits.

Never simplified, whatever the budget: CSRF tokens, argon2 hashing, Markdown
sanitizing, relative paths, drafts never reaching `site/`, and the review
comment before closing each ticket. Those are hard constraints, not extras.

**Stage I would cut first if my estimates are wrong:** per-ticket code review
effort (step 1), because the review is still done, only at lower depth.

## 6. Ledger labelling reminder

`.claude/state/phase` must hold `grill`, `spec`, `tickets`, or `T01`..`T08` at
the start of each stage so the ledger rows can be compared to this table.
It currently reads `tickets`, so reset it as each stage begins.
