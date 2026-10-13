# MP2 self-assessment, version 2.1 (rubric `mp2-v1-20260922`)

Re-run on 2026-10-13 after the T09 repairs (#11) and the review follow-up below. The first version (written the evening of 2026-10-12) scored the tag at 85 and found the defects that #11 fixed. This version scores both the tag as it stands and the current `main`.

| Ref | Commit |
|---|---|
| `mp2-final` (unchanged) | `e3b0788d6086397d4c9daa638ce9321553fd6921` |
| `mp2-mvp` (unchanged) | `06a30700441c06853352aeae52b1bd77b9946e33` |
| `main` after the repairs | the latest commit on `main` (`afd69bd` is the T09 commit; later commits add behaviour tests, this assessment, and the review follow-up) |

This is an estimate by the assistant that wrote most of the code, the report draft and the README. It is not the instructor's judge, and a passing checker or test suite is not treated as full credit for any item. Anything I could not reach is marked **unverified**. Nothing here backdates or invents evidence; where a fix was made after the fact, it says so.

## Review follow-up (this round)

Done after the Spec review finished and before the follow-up commit:

- **`python-dotenv` is now declared in `pyproject.toml`** (`python-dotenv>=1.0`), as you asked, because `app/settings.py` imports it directly. The resolved version is unchanged (1.2.3). `uv.lock` changed by exactly two lines (the new direct edge and its specifier), and `uv lock --check` and `uv sync --locked --dry-run` are clean. A test guards that it stays declared and locked. This closes the Standards reviewer's one "ask before adding a dependency" finding.
- **The six older tests I had amended for the shared navigation were checked by mutation.** The amendments only set the navigation aside (the original assertions on each screen's own content are unchanged), so I broke the behaviour each test protects and confirmed it goes red. All 10 mutations were caught, each by a real assertion and not a crash: a Delete form pointing at the wrong route; the publish route that stops publishing; the refusal page's link pointing elsewhere; **an Editor allowed to delete a Post**; the role form posting to the wrong route; a Delete form added to the Preview; the navigation showing Accounts to an Editor (twice); the navigation's Sign out posting to the wrong route; and an extra form in the navigation. The files were restored from git after each run.
- **Because those tests no longer look at the navigation, a new test holds it to an exact list.** For each role on every admin screen the navigation's links must be exactly `[/admin, /admin/content, /admin/posts, /admin/pages]` (plus `/admin/users` for the Admin) and its only form must be `/logout` with a CSRF token. That includes the refusal page and the Preview. Permission enforcement itself is unchanged and was not weakened: the refusal tests still run against the unchanged rule table.

## The score

| | Max | `mp2-final` as tagged | `main` (if the tag were moved) |
|---|---|---|---|
| Stage 1 | 15 | 15 | 15 |
| A Authenticity | 17 | 12 | 12 |
| B Workflow | 17 | 16 | 16 |
| C Functionality | 15 | **15 only if the grader passes `--env-file`; about 0 if it uses the rubric's literal commands** | 15 |
| D Security | 8 | 8 | 8 |
| E Tests and code | 8 | 7 (E4 is part of the same setup risk) | 7 |
| F Site and admin UX | 7 | 4 | 7 |
| G Docs | 6 | 5 | 5 |
| H Compliance | 7 | 5 | 5 |
| Stage 2 | 85 | 72 (or about 56 on the literal-commands reading) | 75 |
| **Total** | 100 | **87** (or about 71) | **90** |

Why the tag column moved from 85 to 87 without any code change: issue #10's missing "Blocked by" line was recorded (S1.5 +1, B2 +1). Issues are read live from GitHub, so that applies to the tag too. Everything that needed code or the new report lives only on `main`.

Separate from the score: **the submission is late** (see "Deadline compliance"). The extra points above do not change that.

## Items that include the follow-ups, versus the original eight tickets

| Rubric item | Original eight (#2 to #9) | With #10 (T07b) | #11 (T09 repair) |
|---|---|---|---|
| S1.5 tickets with criteria and "Blocked by" (3 = at least 90%) | 8 of 8 | 9 of 9, but **#10's line was added afterwards** and #10 says so | Not counted: labelled `repair`, not `ticket`, so it does not push the count past nine |
| B2 ticket structure | 8 of 8 | 9 of 9 (same caveat) | Not counted |
| B3 vertical slices | 8 of 8 | 9 of 9 (T03, T07, T07b touch 3 of 4 layers) | n/a |
| B4 ticket before code | 8 of 8 | 9 of 9 by timestamp. **Integrity caveat:** #10 was opened after the redesign was built (its title says so). A judge who discounts it still sees 8 of 8 | Created 02:19:30Z, before the commits (02:37Z). Not counted anyway |
| B5 review before close | 8 of 8 | 9 of 9 | Review comment 02:37:31Z, close 02:37:46Z. Not counted |

So the numbers are the same either way; the follow-up changes how the evidence reads, not the points.

## Stage 1 (15): 15

| ID | Max | Earned | Evidence | Fix needed |
|---|---|---|---|---|
| S1.1 | 1 | 1 | `notes/cms-field-notes.md`: 5 numbered WordPress Playground observations | none |
| S1.2 | 2 | 2 | `CONTEXT.md`: 33 bold, ASA-specific terms | none |
| S1.3 | 1 | 1 | Session 03 transcript runs `grill-with-docs` | none |
| S1.4 | 2 | 2 (medium) | Spec #1: problem, user stories by role, out-of-scope. The seven capabilities are covered by story sections but not listed as seven | Optional: add a short "seven capabilities" section to #1 (visible in issue history) |
| S1.5 | 3 | 3 | 9 of 9 `ticket` issues have criteria and a "Blocked by" line (see table above for #10) | none |
| S1.6 | 3 | 3 | #2, #3, #4 closed by commits with `Closes #N`; review comments at 02:32:21Z, 02:59:33Z, 03:33:25Z, each before the close | none |
| S1.7 | 2 | 2 | Live URL 200 over HTTPS; no `href="/` or `src="/` on `gh-pages`. Re-fetched 11 URLs after the T09 push: the public site is unchanged (`gh-pages` is still `ac7e311`) | none |
| S1.8 | 1 | 1 | `mp2-mvp` created and pushed 2026-09-29T03:45:51Z (session 18 transcript). `--stage 1` check: 12/12 | none |

## Stage 2

### A. Authenticity (17): 12

| ID | Max | Earned | Evidence | Fix needed |
|---|---|---|---|---|
| A1 | 5 | 5 (medium) | Session 03: the first 10 user turns each add an ASA fact, constraint or reason | none |
| A2 | 3 | 2 | Glossary, brief and demo content are consistently ASA. `notes/cms-field-notes.md` has no mention of ASA | Optional dated addendum linking the notes to ASA; do not edit the 2026-09-28 text |
| A3 | 4 | 2 (low) | Specifics exist, no listed word-tells, varied paragraph lengths. But the report was **drafted mostly by the assistant**; a few sentences are yours verbatim | Rewrite sections 2 and 4 in your own voice, with two things only you could say |
| A4 | 3 | 3 | Both quoted prompts verified verbatim in the session 03 transcript; failure named; models and skills named | Re-read the failure paragraph |
| A5 | 2 | 0 (unverified) | Every commit after setup has a `Co-Authored-By: Claude` trailer. Issue comments (including the #10 note and the #11 review) were written by the assistant. Your own words are only in prompts | Write at least 3 comments yourself, dated now. I have not written any for you |

### B. Workflow (17): 16

| ID | Max | Earned | Evidence | Fix needed |
|---|---|---|---|---|
| B1 | 1 | 1 | Spec 02:10:30Z precedes every ticket (first at 02:16:22Z) | none |
| B2 | 2 | 2 | 9 of 9 (8 of 8 original) | none |
| B3 | 3 | 3 | All closing commits touch at least 3 of 4 layers | none |
| B4 | 3 | 3 (integrity caveat) | By timestamp 9 of 9; #10 was written after the work | Disclosed in #10, the report and this document |
| B5 | 3 | 3 | Review comment before close on every closed ticket | none |
| B6 | 2 | 2 | Hook tests pass (18); `compaction-log.md` exists with 0 entries; every implement session starts fresh per transcripts; 1 handoff | none |
| B7 | 3 | 2 | (a) plan committed before the first `/implement` commit: 1. (c) report now uses a dated ledger snapshot (2026-10-13 02:37Z, 90 rows, last 02:30Z) and matches `usage_report.py --remaining 0`: 1. **(b) the ledger covers 15 of 19 transcript sessions (79%): 0** | (b) not achievable honestly: sessions 04, 10, 11, 12 have no ledger rows. The report now says so; I did not add rows |

### C. Functionality (15): 15 on `main`

| ID | Max | Earned | Evidence |
|---|---|---|---|
| C1 to C7 | 15 | 15 | My HTTP walkthrough of the tag passed 32/32 (as admin and editor, with a real server restart). On `main`, from a fresh clone: `cp .env.example .env`, `uv run python scripts/seed_demo.py`, `uv run cms serve` with **no** `--env-file` seeds, starts and signs in as both roles. `pytest` also runs `cms serve` itself. **Not Playwright.** |

At the tag, the same commands exit 1 ("Set CMS_ADMIN_PASSWORD…"), which is the risk behind the tag column. The Preview is a button that opens a new tab, not an inline pane.

### D. Security (8): 8

| ID | Max | Earned | Evidence |
|---|---|---|---|
| D1 | 1 | 1 | All seeded hashes start `$argon2id$` |
| D2 | 2 | 2 | 24 of 24 POST routes reject a missing token; forged token 403 |
| D3 | 2 | 2 | 19 of 19 admin-only routes: editor 403, anonymous to `/login`; tests cover all 19 for the editor |
| D4 | 2 | 2 | `<script>` and `onerror` probe: `window.__xss` undefined in the Preview, the editor page and the export, in headless Chrome |
| D5 | 1 | 1 | No `.env`, database or key in any branch's history. `.env` is now read by the app, but stays untracked and git-ignored; a test checks `git ls-files` |

### E. Tests and code (8): 7

| ID | Max | Earned | Evidence | Fix needed |
|---|---|---|---|---|
| E1 | 3 | 3 | Fresh clone of `origin/main`: 409 passed (includes the Chrome-based test); 409 again after the follow-up | none |
| E2 | 2 | 1 | T04 and T06 criteria map to named tests; T06's phone-width criterion is now covered by a browser test. T08's criteria are covered by behaviour tests or `check_submission.py`, **except** the README Backends table and the checklist's step list and wording, which are reviewed by reading only (see the #11 review comment) | Deliberate: I declined a test that only checks documentation wording. This costs a point only if T08 is sampled |
| E3 | 2 | 2 | Largest file 498 lines (`tests/test_t04_users.py`); split by concern; no commented-out blocks. The new files are smaller | none |
| E4 | 1 | 1 | `tests/test_t09_setup.py` runs the rubric's commands in a clean copy | none |

### F. Site and admin UX (7): 7 on `main`

| ID | Max | Earned | Evidence |
|---|---|---|---|
| F1 | 1 | 1 | HTTPS 200 |
| F2 | 2 | 2 | 11 live URLs, all 200; no root-absolute paths |
| F3 | 2 | 2 | Headless Chrome at 390 px: 15 admin screens plus the live public pages fit; each screen is checked to be the one intended. Negative control: the old textarea measured 542 px and failed. At the tag the two editors overflow, so 1 |
| F4 | 2 | 2 | Labels clear; the same navigation on every screen with Sign out; a status message after each redirecting action and a readable error for failures. At the tag: 0 |

### G. Docs (6): 5

| ID | Max | Earned | Evidence | Fix needed |
|---|---|---|---|---|
| G1 | 3 | 2 | All four questions answered. The stale and inaccurate sentences are corrected. **Unverifiable: the ChatGPT use** (no ChatGPT conversation is in the repository; the report says it rests on your account) | A saved export or link would make it verifiable |
| G2 | 2 | 2 | Live URL, Run locally steps (now simpler and verified on a fresh clone), AI Use Statement with the Backends table | none |
| G3 | 1 | 1 | 12 screenshots, retaken without cropping; a test checks their pixel widths | none |

### H. Compliance (7): 5

| ID | Max | Earned | Evidence | Fix needed |
|---|---|---|---|---|
| H1 | 2 | 2 | `check_submission.py --stage 2`: 22/22 on the current files | none |
| H2 | 1 | 1 | Report and 19 transcripts match the patterns (session 18 is the 2026-09-29 T03 session, named with the Oct 12 date) | none |
| H3 | 1 | 1 | Both tags are on `origin` | none |
| H4 | 1 | 0 (**unverified**) | The email has not been sent | Send it with the report attached |
| H5 | 1 | 0 | See below | Not fixable |
| H6 | 1 | 1 | Backends table, no `Backend:` trailers and the ledger's `provider` column all say Anthropic. ChatGPT is disclosed as a separate assistant | none |

## Deadline compliance (flagged separately)

- Stage 2 deadline: Tue Oct 6, 2026, 2:40 pm EDT. Grace ended Wed Oct 7, 2:40 pm EDT.
- `mp2-final` points at `e3b0788`, pushed 2026-10-13T01:23:30Z (Oct 12, 9:23 pm EDT): **5 days 6 h 43 min after the grace period**.
- T04 to T08 and T07b were all closed after the grace period. **The T09 repairs were pushed at 2026-10-13T02:37Z, later still.**
- **Moving `mp2-final` to `main` would make it later again.** It would not change H5 (already 0) but it replaces the tag's push time with a new, later one.
- There is no evidence of an approved extension, and I have not assumed one. Lateness is routed to the instructor by the rubric.

## Remaining deductions (`main`: 90, so 10 points)

| Item | Lost | Achievable? | What would earn it |
|---|---|---|---|
| A2 | 1 | Partly | Dated addendum to the field notes, from you |
| A3 | 2 | Yes, only you | Rewrite the report in your own voice |
| A5 | 2 | Yes, only you | Three comments in your own words, dated truthfully |
| B7(b) | 1 | **No** | The ledger has no data for four sessions |
| E2 | 1 | Only by a wording test I declined | Or the judge does not sample T08 |
| G1 | 1 | Yes | A saved ChatGPT export or link |
| H4 | 1 | Yes, only you | Send the email |
| H5 | 1 | **No** | Lateness; the instructor decides |

Realistic ceiling: 90 now, about 96 if A3, A5, A2, G1 and H4 land.

## Decision for you: `mp2-final`

The tag still points at `e3b0788`, which lacks the repairs and the dependency declaration. The evaluated commit is whatever the tag points at.

| Option | Effect |
|---|---|
| Leave it | About 87 if the grader uses `--env-file`; about 71 if it follows the rubric's commands literally. Editors overflow at 390 px; no success messages |
| Move it to `main` (`git tag -f`, then a forced tag push) | About 90, no setup risk. A rewritten tag after the deadline is visible; I will not do it without your say-so |

My suggestion is to do your own items (A3, A5, G1, A2, H4) first and move the tag once, afterwards. Nothing was moved by any of this work.
