# IPHS 400 Mini-Project #2: report

Yaw Oppong-Krampah · repo https://github.com/yawoppongkrampah-hub/iphs400-mp2-cms · Live site https://yawoppongkrampah-hub.github.io/iphs400-mp2-cms/

## 1. What I built, and the decisions that were mine

I built a small CMS for the African Student Association (ASA) at Kenyon. A local admin console (FastAPI, Jinja, SQLite), never on the public internet, lets an Admin and Editors write Posts and Pages. `cms publish` turns only Published content into plain HTML, and `cms deploy` pushes it to GitHub Pages. The work ran as eight tickets (T01 to T08) plus a design ticket (T07b), and ends with 366 tests.

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

- **Claude Code**; my setup recorded version 2.1.281, and later sessions used updated versions. Models: Sonnet 5 and Sonnet 5.5, the only models in the usage ledger. The course manual and rubric, and the mattpocock-skills plugin.
- **ChatGPT.** I also used ChatGPT to help me understand the assignment, think through CMS decisions, review Claude Code's output, and refine the website design and submission steps.
- I completed the grill, spec and ticket planning first. Each implementation ticket then used a fresh context, test-first development, and independent code review, with findings posted before its closing commit.

## 4. What I would add next, and what the budget data says

One limitation I would change is event scheduling. I chose ordinary Posts to keep the project manageable, but this means the site cannot automatically separate upcoming events from past ones. Adding an event-date field would make the announcements more useful.

I would also end sessions properly. Sessions are signed cookies with no server-side record, so a copied cookie works for 8 hours or until the account is Deactivated, and a password reset does not end sessions already signed in. I accepted this for the demo, because the console only runs on my laptop, and wrote it into the release checklist.

**Budget.** `notes/token-budget-plan.md` estimated about 340% of one 5-hour window. Summed across sessions, the ledger records about 41 percentage points of 5-hour meter increase and about 4 percentage points of weekly meter increase (`usage_report.py --remaining 0`, 2026-10-12). Planned against recorded: `/grill` 15 vs 2, `/to-spec` 10 vs 1, `/to-tickets` 10 vs 3, and 28 per ticket for implementation plus review vs about 4 on average for T01 to T07b.

These are coarse ledger measurements. The meters move in whole percentage points, implementation and review are combined in each ticket's number, and T08's usage is not final because that session was still running.
