# Handoff: IPHS 400 MP2 CMS, repairs done, submission steps remaining

Repo: /Users/yawoppong-krampah/code/iphs400-mp2-cms (branch `main`, in sync with `origin/main` once this file is pushed).

## State
- **Code is finished.** The last code commit is `75332b0` (T10). 447 tests pass, `check_submission.py --stage 2` is 22/22, `--stage 1` is 12/12, and `scripts/check_backends.py` says the README Backends table, the ledger and the commit trailers agree.
- **Tags are untouched.** `mp2-final` is `e3b0788d6086397d4c9daa638ce9321553fd6921` and `mp2-mvp` is `06a30700441c06853352aeae52b1bd77b9946e33`. `mp2-final` does **not** contain any repair (T09, T10, the `.env` loader, the mobile fixes, the navigation and messages, the deploy and Backends tests).
- **Issues:** #1 (spec) is open on purpose. #2 to #9 are the eight core tickets, #10 is the design follow-up (opened after the redesign was built; its "Blocked by" was added afterwards and says so). #11 and #12 are the repairs, labelled `repair`, not `ticket`. All of #2 to #12 are closed.
- **Self-assessment:** `docs/mp2-self-assessment.md` (version 2.5): **93/100 on `main`, 89 for the tag as it stands** (about 73 if a grader follows the rubric's setup commands literally, because the tag's seed command fails without `--env-file`).
- **The submission is late.** Stage 2 closed Wed Oct 7, 2:40 pm EDT; `mp2-final`'s commit was pushed 2026-10-13T01:23Z. There is no extension in the repo and none was assumed. The rubric sends lateness to the instructor.
- The public site (`gh-pages` at `ac7e311`) is unchanged by the repairs; they only touch the admin console and tooling.

## Warning: the compaction log is at its limit
`docs/process/compaction-log.md` now has one `auto` entry (this long session, 2026-10-13 05:17 UTC), written by the hook. The rubric's B6(b) allows at most one. **A second automatic compaction would cost a point.** Do the steps below in fresh sessions (`/clear`) and keep each short, instead of continuing this one.

## Remaining steps, in order
1. **Save the T08 transcript.** It is written by the SessionEnd hook when this session ends, so it is not in the repo yet. It may appear untracked, possibly with `your-name` in the filename. Rename it to the pattern `iphs400_mp2-cms_chat-session_NN_yaw-oppong-krampah_YYYYMMDD.md` (the number follows the existing files; do not renumber them), scan it for real secrets (the checker's regex, and the values in your `.env`; those were placeholders when last checked), then commit it.
   - Confirm from it that this session began with `/clear` and then `implement #9`. If so, the report's "T08 did too, but its transcript is not saved yet" can be made definite.
   - **Trap:** `notes/usage-ledger.csv` has uncommitted rows. The report's budget section cites "the ledger as committed ... 90 rows, 16 sessions, **unchanged since**". The moment a newer ledger is committed, "unchanged since" becomes false. Either leave the ledger uncommitted, or re-run `uv run python scripts/usage_report.py --remaining 0`, update the figures and the date in section 4, and drop that phrase. Do not add or estimate rows for sessions 04, 10, 11 and 12; the report says they are missing.
2. **Verify the repaired submission** from a fresh clone of `origin/main`:
   - `uv sync --locked`, `cp .env.example .env`, `uv run python scripts/seed_demo.py`, `uv run cms serve` (no `--env-file`), then sign in as `admin` and `editor` with the `.env.example` passwords.
   - `uv run pytest -q` (447), `uv run python scripts/check_submission.py --stage 2` (22/22), `uv run python scripts/check_backends.py`, and `uv run python scripts/admin_screenshots.py --check-only` (needs Chrome; checks 15 screens at 390 and 1280 px).
   - The grader will use Playwright; I only used HTTP scripts and headless Chrome, so a browser walkthrough of the Preview and the editors is still worth one look.
3. **Update `mp2-final` to include the repairs.** This is your decision, and it rewrites a tag after the deadline. If you do it: finish steps 1 and 2 and your own items first, so the tag moves once. Then `git tag -f mp2-final <sha of origin/main>` and `git push --force origin mp2-final`, and confirm with `git ls-remote --tags origin` and a rerun of both checkers. Leave `mp2-mvp` alone. Moving the tag makes the tag's push time later still; it does not change H5, which is already 0.
4. **Submit the email.** Subject `IPHS400 MP2 Stage 2 — Yaw Oppong-Krampah`; body: repo URL https://github.com/yawoppongkrampah-hub/iphs400-mp2-cms, Pages URL https://yawoppongkrampah-hub.github.io/iphs400-mp2-cms/, tag `mp2-final`; attach `/Users/yawoppong-krampah/code/iphs400-mp2-cms/docs/iphs400_mp2-web-cms_report_yaw-oppong-krampah_20261012.md`. Say plainly that it is after the deadline. Do not claim an extension unless you have one.

## Yours, not the assistant's (from the self-assessment)
- **A5 (2 points):** write at least three comments in your own words on the issues, dated truthfully.
- **A3:** read the report once and adjust anything that is not how you would say it.
- **A2 (optional, 1 point):** a dated addendum to the field notes tying them to ASA; never edit the 2026-09-28 text.
- Cannot be earned honestly: B7(b) (no ledger data for four sessions) and H5 (lateness).

## Things not obvious from the code
- `.env` is read from the repo root by `python-dotenv` (declared in `pyproject.toml`, already locked); a variable already in the environment wins, `${...}` is not expanded. `CMS_ENV_FILE` names another file; the tests point it at nothing so they never read your `.env`.
- Phase label for the usage ledger is in `.claude/state/phase` (gitignored); it read `T10` at the end of this session.
- `scripts/admin_screenshots.py` starts a throwaway console and Chrome and never touches your `cms.db` or `.env`. `scripts/check_backends.py` reads the README, the ledger and `git log --all`.
- The deploy tests use a temporary local bare repository with only the `file` protocol allowed; nothing contacts GitHub.
- Commit trailer used throughout: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. No `Backend:` trailer is needed (everything was Anthropic; ChatGPT was separate assistance, disclosed in the README and the report).
- Never invent usage rows, comments, timestamps or an extension, and never backdate anything.

## Update: step 1 done (2026-10-13, fresh session)
- The T08 transcript is saved as `docs/transcripts/iphs400_mp2-cms_chat-session_20_yaw-oppong-krampah_20261013.md` (renamed from `..._your-name_...`). It has no matches for the checker's regex or the other secret patterns; the `.env` values that appear in it equal the committed `.env.example` placeholders. It begins with `/clear` then `implement #9`, so the report now says T01 to T08 each began fresh.
- The report cites the ledger as committed in `afd69bd` instead of "unchanged since", so the newer ledger could be committed. The current ledger covers 16 of 20 sessions (still missing 04, 10, 11 and 12). Self-assessment is version 2.6; scores are unchanged (93 on `main`, 89 for the tag).
- Steps 2 to 4 and both tags are untouched.
