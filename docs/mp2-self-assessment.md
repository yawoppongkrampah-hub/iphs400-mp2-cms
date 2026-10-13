# MP2 self-assessment, version 2.6 (rubric `mp2-v1-20260922`)

Re-run on 2026-10-13 after the T09 repairs (#11), their review follow-up, the T10 checks (#12), and the final report wording. Version 2.6 adds the T08 transcript (session 20), checks it for secrets, and replaces the report's "unchanged since" ledger wording with a reference to commit `afd69bd`. The scores do not change. The first version (written the evening of 2026-10-12) scored the tag at 85 and found the defects that #11 fixed. This version scores both the tag as it stands and the current `main`.

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

### T10 (#12): `cms deploy` and the Backends table, now tested

- **`cms deploy` is tested without GitHub** (`tests/test_t10_deploy.py`, 6 tests): the real `cms publish` then the real `cms deploy`, run from a working repository whose `origin` is a temporary **local bare** repository. Git is limited to the `file` protocol and its global and system config are nulled, so nothing can reach GitHub; a test proves an https remote is refused by git itself (`transport 'https' not allowed`). The tests check that every exported file reaches `gh-pages` byte for byte plus `.nojekyll` only, that no `main` is created, that another branch on the remote is left alone, that a Draft never appears even on a second deploy, that an unpublished Post disappears on the next deploy, and that `deploy` refuses and pushes nothing when `site/` is missing.
- **The Backends table is checked against the ledger and the commit trailers** (`scripts/check_backends.py`, 32 tests): ledger providers and models, table rows, `Backend:` trailers, and ChatGPT kept out of all three while disclosed in the README's own words. Negative controls cover each kind of disagreement. This is what the rubric's H6 asks for.
- **Mutation check of both:** 28 of 29 deliberate breakages are caught, each by a named test. The one that is not: adding `-f` (force) to the push of the same `gh-pages` branch. It behaves identically unless someone else has pushed to `gh-pages` in between, and no test sets that up. I am calling it an equivalent-in-tests gap, not a pass.
- **My first mutation run of the Backends check was invalid** (the file was untracked, so my restore step did nothing and mutations piled up). I discarded it, restored the file, and redid it with a copy-based restore. The honest run exposed four loose assertions, which I tightened before this commit. Both reviewers also found real problems (a dead filename assertion, a network test that could pass for the wrong reason, missing Git isolation variables, trailers in other cases or indented, a table hidden in a code block, model ids containing `/`, and an empty history passing), all fixed.

## The score

| | Max | `mp2-final` as tagged | `main` (if the tag were moved) |
|---|---|---|---|
| Stage 1 | 15 | 15 | 15 |
| A Authenticity | 17 | 14 | 14 |
| B Workflow | 17 | 16 | 16 |
| C Functionality | 15 | **15 only if the grader passes `--env-file`; about 0 if it uses the rubric's literal commands** | 15 |
| D Security | 8 | 8 | 8 |
| E Tests and code | 8 | 7 (E4 is part of the same setup risk) | 8 |
| F Site and admin UX | 7 | 4 | 7 |
| G Docs | 6 | 5 | 5 |
| H Compliance | 7 | 5 | 5 |
| Stage 2 | 85 | 74 (or about 58 on the literal-commands reading) | 78 |
| **Total** | 100 | **89** (or about 73) | **93** |

Why the tag column moved from 85 to 89 without any code change: issue #10's missing "Blocked by" line was recorded (S1.5 +1, B2 +1), and A3 was rescored from 2 to 4 after the recheck below. Issues are read live from GitHub, so that applies to the tag too. Everything that needed code or the new report lives only on `main`, including the `cms deploy` and Backends tests that lift E2 on `main` (on the tag, E2 stays 1).

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
| A2 | 3 | 2 | Tier 3 needs the notes, the glossary **and** the site content to be specific to the client; tier 2 is "specific in one or two". Glossary and site content are ASA-specific (33 terms; ASA Pages and Posts). **The field notes are not**: `notes/cms-field-notes.md` never mentions ASA or any client, and the only named thing in it is an "About the Helpline" test page. See the recheck section | See recheck section |
| A3 | 4 | 4 (medium) | By the item's own wording the measure is met: at least 2 specifics and at most 2 tells. See the recheck section. My earlier 2 added a requirement the rubric does not have | none |
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
| B6 | 2 | 2 | (a) Hook tests pass (18); `docs/process/compaction-log.md` exists. It now holds **1 auto compaction** (this long session, `a77ef331`, 2026-10-13 05:17 UTC), written by the hook, which is the rubric's limit ("<=1"), so there is no margin left. (b) **9 of 9 sessions that invoked `/implement` began fresh** (after `/clear`, or with the command as the first input), per the committed transcripts: sessions 07 (#2), 09 (#3), 18 (#4), 13 (#5), 14 (#6), 15 (#7), 17 (#8), 20 (#9; `/clear` at 00:58:40Z, `implement #9` at 00:58:47Z), and 16 (#7 again, which implemented nothing because #7 was already done). Session 09 also received `implement #4`, and declined it under the one-ticket-per-session rule; T03 was built in fresh session 18. 1 auto compaction in the log (at the limit); 2 handoffs saved | Do not let another session auto-compact: a second entry would cost B6(b). Do the remaining steps in fresh sessions |
| B7 | 3 | 2 | (a) plan committed before the first `/implement` commit: 1. (c) the report cites the ledger as committed in `afd69bd` (2026-10-13 02:37Z, 90 rows, last row 02:30Z), which I re-ran with `usage_report.py --ledger` and which gives the report's 53 and 6 points: 1. **(b) the ledger covers 16 of 20 transcript sessions (80%; it was 15 of 19 at the snapshot): 0** | (b) not achievable honestly: sessions 04, 10, 11, 12 have no ledger rows. The report now says so; I did not add rows |

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
| E1 | 3 | 3 | Fresh clone of `origin/main`: 409 passed at the last verified clone; 447 pass in the working tree after T10 (includes the Chrome-based test) | none |
| E2 | 2 | 2 on `main` (medium); 1 at the tag | Read at the rubric's own grain (each acceptance *criterion* needs at least one test that names or clearly exercises it), every testable criterion of all nine tickets now has one on `main`. The two gaps named earlier are closed by #12: T03 criterion 7 by `tests/test_t10_deploy.py`, T08's Backends table by `scripts/check_backends.py` and `tests/test_t10_backends.py`. See the recheck section | Residual risk only, see the recheck section |
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
| G1 | 3 | 2 | All four questions are answered, and (c) is not thin: it says why the grill, small tickets, test-first development and independent review were used, and ties them to the two real README prompts. What is left is the "claims verifiable in the repo" part of the 3 tier: the ChatGPT use (rests on your account), and the fresh-session claim for T08, now settled by the committed session 20 transcript (`/clear`, then `implement #9`). The report says the committed transcripts show T01 to T08 began fresh, and that the design follow-up and repairs continued in existing sessions | See recheck section |
| G2 | 2 | 2 | Live URL, Run locally steps (now simpler and verified on a fresh clone), AI Use Statement with the Backends table | none |
| G3 | 1 | 1 | 12 screenshots, retaken without cropping; a test checks their pixel widths | none |

### H. Compliance (7): 5

| ID | Max | Earned | Evidence | Fix needed |
|---|---|---|---|---|
| H1 | 2 | 2 | `check_submission.py --stage 2`: 22/22 on the current files | none |
| H2 | 1 | 1 | Report and 20 transcripts match the patterns (session 18 is the 2026-09-29 T03 session, named with the Oct 12 date) | none |
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

## Remaining deductions (`main`: 93, so 7 points)

| Item | Lost | Achievable? | What would earn it |
|---|---|---|---|
| A2 | 1 | Partly | Field notes that name the client and use its vocabulary: a dated addendum, since the original is from 2026-09-28 |
| A5 | 2 | Yes, only you | Three comments in your own words, dated truthfully |
| B7(b) | 1 | **No** | The ledger has no data for four sessions |
| G1 | 1 | Only if the judge accepts an attestation | The T08 transcript is now committed, so the fresh-session claim is verifiable. What is left is the ChatGPT use, a claim about a tool outside the repo. I kept G1 at 2 for it |
| H4 | 1 | Yes, only you | Send the email |
| H5 | 1 | **No** | Lateness; the instructor decides |

Realistic ceiling: 93 now, up to 97 if A5, A2 and H4 land (A5 +2, the others +1 each), and 98 if the judge also accepts the ChatGPT attestation for G1. B7(b) and H5 cannot be earned.

## Recheck of A2, A3, E2 and G1 against the rubric's exact wording

Only the rubric's own words are used as requirements. I do not require a ChatGPT export, a hand-written report, or a wording test.

### A2: client specificity (3): 2 stands

*Wording:* "Field notes and `CONTEXT.md` name a real or plausible client and use its vocabulary ... (3 = specific and consistent across notes, glossary, and site content; 2 = specific in one or two; 1 = generic)."

| Part | Specific to the client? | Evidence |
|---|---|---|
| Glossary | Yes | `CONTEXT.md` has 33 bold terms (Event card, Display name, Permission refusal, Photo permission, Announcements...) and names ASA throughout |
| Site content | Yes | Demo Posts and Pages are ASA placeholders (About ASA, Resources, Photos; an Afrobeat event); the Welcome text is the client brief's wording |
| **Field notes** | **No** | `notes/cms-field-notes.md` has five WordPress observations and one admission. It contains **zero** mentions of ASA and names no client. Its only named item is a test page, "About the Helpline", which is not the client. It was committed in the same planning commit as the brief (`49e1c16`, 2026-09-28 22:26 EDT) |

**Unmet requirement:** the notes do not name the client or use its vocabulary, so the three parts are not consistent. That is exactly the tier-2 description (specific in two of three). The default "Knox County Historical Society" clause does not apply. I am not calling the notes wrong: they record the tool, which is what S1.1 asks. The deduction is genuine and small. The honest way to address it is a clearly dated addendum, never an edit of the original text.

### A3: report voice (4): the earlier 2 was wrong, now 4

*Wording:* "Report contains >=2 specifics only you could write (a named bug, a dated decision, an admission of something that failed) and no more than 2 tells from the list below (4 = both, 3 = specifics with 3-4 tells, 2 = one specific, 1 = none but edited, 0 = unedited model output)."

My earlier score of 2 rested on "the report was drafted mostly by the assistant". That is not the measure: section A says heavy AI use is expected and only *unedited* output costs points. The report was edited in several rounds, with your own sentences and facts in it, so the 0 and 1 tiers do not apply.

| Requirement | Evidence in the report |
|---|---|
| Specific 1: named bug | The `.env.example` defect: `CMS_SITE_TITLE=African Student Association`, unquoted, which `uv` could not parse |
| Specific 2: admission of something that failed | "My first seed test parsed the file by hand and passed anyway"; also T07b's issue "opened after the redesign already existed" |
| More | The quoted invented claim "Today ASA has no site that does this", the ledger gap (sessions 04, 10, 11, 12), the dated snapshot (2026-10-13 02:37 UTC), your event-scheduling limitation |
| Tells, at most 2 | Listed word-tells: none. Uniform paragraph length: no (5 to 206 words). Three-item parallel lists "everywhere": no (one group of 3 bullets, one of 5). Closing summary restating the opening: no (the last paragraph is the ledger caveat). So 0 to 1 |
| Human tells present | Dates and names (#1, #10, T07b, 2026-10-13), admissions, sentence lengths from 5 to 39 words (standard deviation 8.8) |

**Residual risk, not a deduction:** the `.env.example` paragraph is written about Claude Code in the third person ("Claude Code found..."), so a judge could read that specific as less "only you". The T07b and invented-claim specifics still make two.

### E2: tests trace to acceptance criteria (2): 2 on `main`, 1 at the tag

*Wording:* "Judge samples 3 tickets; each acceptance criterion has >=1 test that names or clearly exercises it (2 = all, 1 = >=half)."

**A correction to my earlier reading.** Version 2.3 kept E2 at 1 because a few *clauses inside* T08's release-checklist criterion had no test (Photo permission confirmed by a leader; the checklist says the author runs it; no ASA owner or approval process is claimed). The rubric's unit is the **criterion**, and it asks for at least one test that names or clearly exercises it. It does not ask for a test of every clause. I was holding the item to a stricter standard than its wording, so I withdraw that deduction.

I re-read every criterion of all nine tickets (#2 to #10). Against the two tests added in #12:

| Criterion | Test that names or exercises it |
|---|---|
| T03 (#4) criterion 7, "`cms deploy` pushes the export to the GitHub Pages branch ... does not show a Draft" | `tests/test_t10_deploy.py` (6 tests): real `cms publish` then `cms deploy` into a temporary local bare repository; every exported file reaches `gh-pages` byte for byte, no `main` is pushed, a Draft is absent on the first and the second deploy, an unpublished Post disappears, a missing `site/` is refused, and git itself refuses an https remote. The "live URL" half of the sentence was checked by hand against the live site |
| T08 (#9) "The README has Live URL, Run locally and Generative AI Use Statement sections, with the Backends used table" | Live URL, Run locally and the statement: `check_submission.py`; the setup steps themselves: `tests/test_t09_setup.py`; the Backends table: `tests/test_t10_backends.py::test_the_real_readme_ledger_and_history_agree` and the command test, with 14 negative controls |
| T08 (#9) the release checklist | Named by `tests/test_t08_release.py::test_the_checklists_relative_path_check_is_quiet_on_a_real_export_and_catches_a_bad_one`; also exercised by the publish test (`test_cms_cli.py`), the deploy tests, the approved-image copy tests (`test_t07_public_site.py`) and `test_no_screen_or_route_accepts_a_file_so_an_editor_cannot_add_an_image` |
| T08 (#9) the Preview, the hint, the seed, the clean-clone smoke test, the screenshots | `test_t08_preview.py` (23), `test_t08_release.py`, `test_t09_setup.py`, `test_t09_mobile.py` (screenshot pixel widths) and `check_submission.py` (names) |
| T01 (#2) AC9 ".env.example lists every variable needed"; T07 (#8) contrast, focus, keyboard | `test_t09_setup.py`; `test_t07_public_site.py` |

**What is not covered by a test, and why I set it aside.** Two criteria are process steps that no test can exercise: T02 (#3) AC10, "the tests are read before they are allowed to pass", and T07b (#10)'s single criterion, a review comment posted before closing. Also, "the Stage 2 submission checker passes" (T08) and "the Stage 1 checker passes" (T03) are exercised by running the checker itself, which is an existing submission check, not a pytest test.

**Residual risk, not a deduction:** a strict judge could count those process and checker criteria as untested. I put that at low, so E2 is 2 with medium confidence.

**At the tag:** `mp2-final` does not contain the deploy or Backends tests, so T03 criterion 7 and T08's Backends table have no test there, and E2 stays 1 at the tag. That is part of the case for moving the tag.

### G1: report answers the four questions (3): 2 stands, for a different reason now

*Wording:* "(a) what you built and which grill decisions were yours; (b) one place the AI drifted or made something up, and how the workflow caught it; (c) skills, prompts, and resources used and why; (d) future improvements. 3 = all four, claims verifiable in the repo; 2 = all four with one unverifiable claim or one thin answer; 1 = one question missing."

| Question | Met? | Evidence |
|---|---|---|
| (a) built, and your grill decisions | Yes | Section 1 lists the decisions, which match your session 03 answers; the later repairs are named as #11 and #12 |
| (b) AI drift and how it was caught | Yes | The quoted invented claim, caught while reviewing issue #1; the `.env.example` defect, which a hand-parsing test missed and `uv` exposed |
| (c) skills, prompts, resources, and why | **Yes, no longer thin** | Section 3 names the tools, then gives a reason for each step (grill so the decisions were yours, small tickets, test-first, independent review) and points to the two real prompts quoted in the README |
| (d) future improvements | Yes | Event-date field; session invalidation, with why it was accepted |

**What is left (the tier-3 requirement "claims verifiable in the repo"):**
1. The ChatGPT use is a claim about a tool outside the repository. The report says it rests on your account. I do not require an export. A judge may treat it as an attestation; if so this item is not affected.
2. ~~The fresh-session claim for T08.~~ Resolved in version 2.6: the T08 transcript is committed as session 20 and begins with `/clear`, then `implement #9`. The report now says T01 to T08 each began fresh.

The aside "my own `.env` had quotes" (a claim about a git-ignored file) has been removed from the report.

If a judge accepts the ChatGPT attestation, G1 is 3; if not, 2. I keep 2.

**The fresh-context sentence against the transcripts**

| Ticket (issue) | Session | How it began | `implement` invoked |
|---|---|---|---|
| T01 (#2) | 07 | `/clear` | #2 |
| T02 (#3) | 09 | `/clear` | #3 |
| T03 (#4) | 18 | `/clear` | #4. Session 09 had also received `implement #4`, and the assistant declined to start it ("one ticket per session"), so no T03 work happened in that context |
| T04 (#5) | 13 | the `implement` command as the first input | #5 |
| T05 (#6) | 14 | `/clear` | #6 |
| T06 (#7) | 15 | `/clear` | #7. Session 16 invoked `implement #7` again, implemented nothing (already done), and pushed the commit |
| T07 (#8) | 17 | `/clear` | #8 (three invocations within the one session) |
| T08 (#9) | 20 | `/clear` (2026-10-13T00:58:40Z), then `implement #9` (00:58:47Z) | #9. This session also carried the T09 and T10 repairs afterwards, until 17:06Z |
| T07b (#10) | 19 | "Resume the ASA CMS project..." at 00:31Z, a status and push session. The T07 push was at 00:33Z, the design request at 00:38Z in the same session | The design follow-up **continued in an existing session**, as the report says |

## Decision for you: `mp2-final`

The tag still points at `e3b0788`, which lacks the repairs and the dependency declaration. The evaluated commit is whatever the tag points at.

| Option | Effect |
|---|---|
| Leave it | About 89 if the grader uses `--env-file`; about 73 if it follows the rubric's commands literally. Editors overflow at 390 px; no success messages; no `cms deploy` or Backends tests |
| Move it to `main` (`git tag -f`, then a forced tag push) | About 93, no setup risk. A rewritten tag after the deadline is visible; I will not do it without your say-so |

My suggestion is to do your own items (A3, A5, G1, A2, H4) first and move the tag once, afterwards. Nothing was moved by any of this work.
