# IPHS 400 Mini-Project #2: ASA website CMS

A small web CMS for the African Student Association (ASA) at Kenyon, built for a class
project. A local admin console (FastAPI, Jinja, SQLite) is where an Admin and Editors write
Posts and Pages. `cms publish` renders only Published content into `site/` as plain HTML,
and `cms deploy` sends it to GitHub Pages. The console never goes on the public internet.
Words such as Post, Published and Live are defined in `CONTEXT.md`.

## Live URL

https://yawoppongkrampah-hub.github.io/iphs400-mp2-cms/

Repository: https://github.com/yawoppongkrampah-hub/iphs400-mp2-cms

The demo content is placeholder text and makes no claim about ASA beyond the client brief.

## Run locally

You need [uv](https://docs.astral.sh/uv/) and Python 3.12 or newer.

```bash
git clone https://github.com/yawoppongkrampah-hub/iphs400-mp2-cms.git
cd iphs400-mp2-cms
uv sync
cp .env.example .env
uv run python scripts/seed_demo.py
uv run cms serve
```

Open http://localhost:8000/admin and sign in as `admin` or `editor`, with the matching
`CMS_ADMIN_PASSWORD` or `CMS_EDITOR_PASSWORD` from `.env`. The seed also creates one
Deactivated account (`former-member`) that cannot sign in, plus Published and Draft Posts
and Pages. Run the seed again at any time; it never duplicates anything.

The app reads `.env` from the repository root by itself, so no `--env-file` flag is needed (it
still works). A variable already set in your shell wins over the file, and no value is ever
printed. `.env`, `*.db` and `site/` are in `.gitignore` and are never committed.

To start with your own first Admin instead of the demo accounts, set `CMS_ADMIN_PASSWORD`
and run `uv run cms create-admin --username NAME --display-name "ASA Leadership"`.
The password is read from the environment and never printed.

```bash
uv run cms publish   # write site/ from Published content
uv run cms deploy    # push site/ to the gh-pages branch
uv run pytest -q                     # the test suite
uv run python scripts/check_submission.py --stage 2
```

Making content Live is a short, repeatable routine: see `docs/release-checklist.md`. It also
lists what must change before anyone else can reach the console, and the session limits that
are accepted for the class demo.

## What is here

```text
app/, templates/   the CMS: routes, rules, rendering, admin and public templates
scripts/           seed_demo.py, usage_report.py, check_submission.py
images/            approved image files; `cms publish` copies them into the site
tests/             tests at three seams: the admin console, the published site, the cms command
docs/              ADRs, the release checklist, screenshots, handoffs, transcripts
notes/             field notes, token budget plan, usage ledger
```

Screenshots of the six admin screens at 1280 px and 390 px are in `docs/screenshots/`.

## Generative AI Use Statement

**Models.** Claude Sonnet 5 and Sonnet 5.5, through Claude Code on a Claude Pro account.
I also used ChatGPT to help me understand the assignment, think through CMS decisions, review Claude Code's output, and refine the website design and submission steps. I did not record which ChatGPT model.
**Skills.** The mattpocock-skills plugin: `setup-matt-pocock-skills`, `ask-matt`, `grilling`,
`domain-modeling`, `to-spec`, `to-tickets`, `tdd`, `implement`, `code-review` and `handoff`.
The process was grill, spec, eight tickets, then one ticket per session, each ending in a
`/code-review` comment on its issue before the closing commit.

**Two prompts I really sent** (from the session transcripts in `docs/transcripts/`):

> Choose (b). Editors should be able to update the body of existing Pages so the Photos page can stay current. The admin should control creating and deleting Pages, publishing or unpublishing them, and changing titles or slugs that affect navigation and links. This is a design choice for our ASA site, not something I observed in WordPress.

> Before creating tickets, edit spec issue #1. In the Problem Statement, remove the unverified claim "Today ASA has no site that does this." Do not replace it with another claim about ASA's current website or communication. Change "find upcoming events" to "find event announcements," since this version has no event-date field or automatic upcoming/past sorting. Keep the rest of the spec as written. Show me the revised Problem Statement and confirm the issue was updated.

**One real model failure.** The model's first spec draft claimed that ASA had no website serving these needs, even though I had not provided that information. We caught the claim while reviewing issue #1 and removed it before creating the implementation tickets.

### Backends used

| Provider | Model | Used for | Commit trailer |
|---|---|---|---|
| Anthropic | Sonnet 5 / Sonnet 5.5 | Everything: grill, spec, tickets, all implementation and reviews | none needed |

No other Claude Code backend was used (ChatGPT was a separate assistant outside Claude Code, so it has no row here). The `provider` column of `notes/usage-ledger.csv` says `anthropic`
on every row, and no commit has a `Backend:` trailer.
