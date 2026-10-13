# Release checklist

How Published content becomes **Live**. Marking a Post or Page Published in the admin
console only makes it ready; visitors see it after `cms publish` and `cms deploy`.

**Who runs it.** For the class demo, the project author runs this from their own laptop.
ASA has no known person responsible for this step, and none is assumed. This checklist
describes no ASA approval process either: Photo permission below is a working rule for
this project, not an ASA policy.

## 1. Before you publish

- [ ] **Photo permission.** If a Post or Page shows a real photo, an ASA leader has
      confirmed that ASA has permission to use it. Do this *before* the file is added.
      Without confirmation, use a demo illustration or no image. The Photos page says
      that actual event photos will be added once ASA has permission.
- [ ] **Adding approved image files.** Copy each approved file into `images/`
      (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp` or `.svg`; hidden files and other file
      types are never copied). `cms publish` copies them to `site/images/`.
- [ ] **The limit.** An Editor cannot add an image file alone. An Editor writes the
      caption, the alt text and the Markdown reference (`![Alt text](images/file.jpg)`);
      the release-holder adds the file. A reference to a file that is not in `images/`
      shows only its alt text on the live site.
- [ ] Every image has descriptive alt text, and demo illustrations are labelled
      illustrative, never presented as photos of a real ASA event.

## 2. Publish and check

- [ ] `uv run --env-file .env cms publish` writes `site/` from Published content only.
      Drafts never leave the database. Never edit `site/` by hand: it is rebuilt.
- [ ] **Relative-path check.** This must print nothing:

      grep -rEn '(href|src)="/' site/

      The site is served from a subfolder, so a root-absolute link or image would break.
- [ ] Look at it before it goes out: `python3 -m http.server -d site 8001`, then open
      http://localhost:8001. Check the Navigation, the newest Announcement, and each image.

## 3. Deploy and confirm

- [ ] `uv run --env-file .env cms deploy` pushes `site/` to the `gh-pages` branch.
- [ ] Wait up to ten minutes, then open the Live URL (in the README) and find the change.
      Only now is it Live.

## Before anyone else can reach the console

The console is meant to run only on the author's laptop and never on the public internet
(ADR-001). If that ever changes, do these first.

- [ ] Set a long random `CMS_SECRET_KEY` in `.env`. `cms serve` warns while the key is one
      that is public in this repository.
- [ ] Choose your own passwords in `.env` instead of the `change-me-...` placeholders from
      `.env.example`. `scripts/seed_demo.py` says so while a placeholder is in use.

## Known limits, accepted for the class demo

These were raised as follow-ups on the T01 and T04 reviews. They are accepted because the
console runs only on the author's laptop, and recorded here so no one is surprised.

- **Sessions are signed cookies with no server-side record.** A copied cookie stays valid
  after sign-out until it expires (8 hours) or the account is Deactivated.
- **A Password reset does not end sessions that are already signed in.** Deactivating the
  account does. To close both gaps later: keep a per-account session version and check it
  in `security.current_user`, bumping it on sign-out and on reset.
