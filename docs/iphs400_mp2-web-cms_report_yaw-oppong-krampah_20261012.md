# IPHS 400 Mini-Project #2: report

Yaw Oppong-Krampah · repo https://github.com/yawoppongkrampah-hub/iphs400-mp2-cms · Live site https://yawoppongkrampah-hub.github.io/iphs400-mp2-cms/

## 1. What I built, and the decisions that were mine

I built a small CMS for the African Student Association (ASA) at Kenyon. A local admin console (FastAPI, Jinja, SQLite), never on the public internet, lets an Admin and Editors write Posts and Pages. `cms publish` turns only Published content into plain HTML, and `cms deploy` pushes it to GitHub Pages. The work ran as eight tickets (T01 to T08) plus a design ticket (T07b, opened after the redesign was built), and ends with 409 tests.

My decisions in the grill:

- **Ordinary Posts for announcements.** No separate Event type. The date, time, location and who can attend go in the Body.
- **Editors can update the Body of an existing Page**, so the Photos page can stay current. Admins control Page structure and users.
- **Slugs come from the title on first save and then stay put**, so shared links keep working.
- **Accounts are deactivated, never deleted**, and bylines use a public Display name.
- **Published is not Live.** Content goes Live only after `cms publish` and `cms deploy`, which I run myself from my laptop (`docs/release-checklist.md`).

After the first public design looked sparse, I asked for a warmer, more inviting one (T07b).

## 2. Where the AI drifted, and what caught it

**The invented claim.** The model's first spec draft said "Today ASA has no site that does this." I had not supplied that fact, and the client brief does not say it. With ChatGPT's help, I caught the unsupported claim while reviewing issue #1 and asked Claude Code to remove it before creating tickets. The same edit changed "upcoming events" to "event announcements".

**The `.env.example` defect.** While setting up the T08 demo, Claude Code found that the README's setup failed from `.env.example`: `uv` could not parse `CMS_SITE_TITLE=African Student Association` because the multi-word value was not quoted. The unquoted style came from the starter template, and my own `.env` had quotes, so I had never hit it. This was found before the clean-clone run. Claude Code's first seed test parsed the file by hand and passed anyway; the bug only showed when `uv` read the file. Claude Code then changed the test to run the seed through `uv --env-file` and quoted the line, and a fresh clone signed in as both roles.

## 3. Resources and workflow

- I used Claude Code with Sonnet 5 and Sonnet 5.5, plus ChatGPT for planning and review assistance. The only models in the usage ledger are Sonnet 5 and Sonnet 5.5. I also used the course manual and rubric and the mattpocock-skills plugin.
- **ChatGPT.** I also used ChatGPT to help me understand the assignment, think through CMS decisions, review Claude Code's output, and refine the website design and submission steps. No ChatGPT conversation is saved in this repository, so this rests on my own account.
- I completed the grill, spec and ticket planning first. The transcripts show the sessions for T01 to T07 each began after `/clear` or with the `/implement` command; the work was test-first, and each ticket's code review was posted on its issue before it closed. T08 also began with `/clear`, but its transcript is written when the session ends, so it is not in the repository yet. The repair work for issue #11 happened in that same session, with no fresh context. T07b is the other exception: it was built in a resumed session after T07 was pushed, and its issue (#10) was opened after the redesign already existed. Its dependency on T07 was recorded afterwards, and #10 says so.

## 4. What I would add next, and what the budget data says

One limitation I would change is event scheduling. I chose ordinary Posts to keep the project manageable, but this means the site cannot automatically separate upcoming events from past ones. Adding an event-date field would make the announcements more useful.

I would also end sessions properly. Sessions are signed cookies with no server-side record, so a copied cookie works for 8 hours or until the account is Deactivated, and a password reset does not end sessions already signed in. I accepted this for the demo, because the console only runs on my laptop, and wrote it into the release checklist.

**Budget.** `notes/token-budget-plan.md` estimated about 340% of one 5-hour window. A ledger snapshot taken on 2026-10-13 at 02:37 UTC (90 rows, the last at 02:30 UTC, from 16 sessions) shows about 53 percentage points of 5-hour meter increase and 6 points of weekly increase (`usage_report.py --remaining 0`). Planned against recorded: `/grill` 15 vs 2, `/to-spec` 10 vs 1, `/to-tickets` 10 vs 3, and 28 per ticket for implementation plus review vs 4 on average for T01 to T07b (2 to 7 each). The T08 label (12 points) also covers the release, the submission checks and the rubric self-assessment, so it is not comparable with the other tickets. The repair work for issue #11 has its own label, T09, which shows 3 points so far; it continued after the snapshot, so the final figure will be higher.

These are coarse ledger measurements. The meters move in whole percentage points, and implementation and review share one number per ticket. The ledger is also incomplete: it has no rows for four of the 19 transcript sessions (04, from 2026-09-29, and 10, 11 and 12, from 2026-10-01), so it covers 15 of 19, or 79%. I have not added or estimated rows for them, so the totals leave them out.
