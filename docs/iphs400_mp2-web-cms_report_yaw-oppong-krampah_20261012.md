# IPHS 400 Mini-Project #2: report

Yaw Oppong-Krampah · repo https://github.com/yawoppongkrampah-hub/iphs400-mp2-cms · Live site https://yawoppongkrampah-hub.github.io/iphs400-mp2-cms/

## 1. What I built, and the decisions that were mine

I built a small CMS for the African Student Association (ASA) at Kenyon. A local admin console (FastAPI, Jinja, SQLite), never on the public internet, lets an Admin and Editors write Posts and Pages. `cms publish` turns only Published content into plain HTML, and `cms deploy` pushes it to GitHub Pages. The work ran as eight tickets (T01 to T08), a design ticket (T07b) and the later repairs in issues #11 and #12, and ends with 447 tests.

My decisions in the grill:

- **Ordinary Posts for announcements**, with the date, time, location and who can attend in the Body. No separate Event type.
- **Editors may update the Body of an existing Page**, so the Photos page stays current. Admins control Page structure and users.
- **Slugs come from the title once, then stay put**, so shared links keep working.
- **Accounts are deactivated, never deleted**, and bylines use a public Display name.
- **Published is not Live.** I run `cms publish` and `cms deploy` myself from my laptop (`docs/release-checklist.md`).

After the first public design looked sparse, I asked for a warmer one (T07b).

## 2. Where the AI drifted, and what caught it

**The invented claim.** The model's first spec draft said "Today ASA has no site that does this." I had not supplied that fact, and the client brief does not say it. With ChatGPT's help, I caught it while reviewing issue #1 and asked Claude Code to remove it before creating tickets. The same edit changed "upcoming events" to "event announcements".

**The `.env.example` defect.** While setting up the T08 demo, before the clean-clone run, Claude Code found that the README's setup failed: `uv` could not parse `CMS_SITE_TITLE=African Student Association`, because the multi-word value was not quoted. The unquoted style came from the starter template. Claude Code's first seed test parsed the file by hand and passed anyway; the bug showed only when `uv` read the file. It changed the test to run the seed through `uv`, quoted the line, and a fresh clone signed in as both roles.

## 3. Resources and workflow

I used Claude Code with Sonnet 5 and Sonnet 5.5, the course manual and rubric, and the mattpocock-skills plugin. I also used ChatGPT to help me understand the assignment, think through CMS decisions, review Claude Code's output, and refine the website design and submission steps. No ChatGPT conversation is saved in this repository, so this rests on my own account.

I used the grill so the decisions were mine: the first README prompt is me choosing who may edit Pages. Eight small tickets gave each session one slice to check, and test-first development judged what the app does, not how it is built. Independent review caught mistakes, such as a form field that would crash on an unusual character; the second README prompt removes the invented claim. The committed transcripts show T01 to T08 each began in a fresh session; T08's (session 20) opens with `/clear` and then `implement #9`. The design follow-up and the repairs (#11, #12) continued in existing sessions, and the design ticket (#10) was opened after the redesign existed.

## 4. What I would add next, and what the budget data says

One limitation I would change is event scheduling. I chose ordinary Posts to keep the project manageable, but this means the site cannot automatically separate upcoming events from past ones. Adding an event-date field would make the announcements more useful.

I would also end sessions properly. Sessions are signed cookies with no server-side record, so a copied cookie works for 8 hours or until the account is Deactivated, and a password reset does not end sessions already signed in. I accepted this for the demo, because the console only runs on my laptop, and wrote it into the release checklist.

**Budget.** `notes/token-budget-plan.md` estimated about 340% of one 5-hour window. The ledger as committed in `afd69bd` (2026-10-13, 02:37 UTC; 90 rows, 16 sessions, last row 02:30 UTC; `git show afd69bd:notes/usage-ledger.csv`) shows about 53 percentage points of 5-hour meter increase and 6 of weekly increase (`usage_report.py --remaining 0`). Planned against recorded: `/grill` 15 vs 2, `/to-spec` 10 vs 1, `/to-tickets` 10 vs 3, and 28 per ticket for implementation plus review vs 4 on average for T01 to T07b. T08 (12 points) also covers the release and submission checks, so it is not comparable. These figures use that snapshot only: the current ledger has later rows (the T09 and T10 repairs, and the sessions after them) that they do not include.

These are coarse measurements: the meters move in whole percentage points, and implementation and review share one number per ticket. The ledger is also incomplete. At that snapshot it had no rows for four of the 19 transcript sessions (04, 10, 11 and 12), so it covered 15 of 19, or 79%. The T08 transcript has since been saved as session 20 and its session has rows, so the current ledger covers 16 of 20, or 80%; the same four are still missing. I have not added or estimated rows for them, so the totals leave them out.
