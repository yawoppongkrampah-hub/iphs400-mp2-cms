# CONTEXT.md glossary

## Content

**Post**
A dated piece of writing with a title, a Markdown body, a status, an author and timestamps. Posts are for things that need to go out quickly.

**Slug**
The URL-safe form of a title, such as `afrobeat-night`. A Post's slug is generated from its title on the first save, with a number added if it already exists. Editors never enter it. It does not change when the title or event details are corrected, so shared links keep working. Only the Admin may change a slug, and is warned that this can break an old link. A Page's slug is also Admin-only.

**Event announcement**
A Post that announces an event, such as the Afrobeat event. It has no event-date field of its own. The event's date, time, location and who can attend are written clearly in the body. _Avoid_: "Event" as a separate kind of content.

**Announcements**
The public list of Published Posts, ordered by First-published date, newest first. The Home page shows the five most recent, with a link to the full list. It is not "Upcoming Events": newest Posts are not necessarily future events. _Avoid_: "Upcoming Events" for this list.

**First-published date**
The date a Post was first Published. Announcements are ordered by it, newest first, and each Event card shows it. It is kept if the Post is unpublished and later Published again. It is never labeled as the event's date: the event's actual date and time stay in the Body.

**Updated date**
Shown on an Event card when a Post's content changes after it was first Published, so visitors can tell details were corrected. Editing does not reorder the Announcements list.

**Page**
Permanent content, such as information about ASA and cultural resources. A published Page appears in the public navigation.

**Photo**
An image shown inside a Post or Page. Photos are not uploaded through a separate feature and there is no gallery. Every photo has descriptive alt text. An Editor writes the caption, alt text and Markdown reference but cannot add a new image file alone: the release-holder adds approved image files, and publishing copies them into the public site. Demo illustrations are labeled as illustrative and have usable rights.

**Photos page**
A Page that collects selected photos from past activities.

**Photo permission**
A working rule for this project: an ASA leader checks that ASA has permission to use a real photo before it is added to a Post or Page. ASA's formal approval process, if any, is unknown and is not described here. The class demo uses placeholders or images we have permission to use.

**Author**
The account that wrote a Post. Recorded in the admin console for every Post.

**Display name**
The public name shown as a Post's byline, set by the Admin when creating the account. It can be a name, a nickname or a team name such as "ASA Events Team", so no member's real name is public without their agreement. _Avoid_: showing the **Username** as the byline.

**Deactivated account**
An account whose owner can no longer sign in. Its published Posts stay public and the original Author relationship is kept. If a former member wants their name removed, the Admin changes the account's Display name (for example to "ASA Events Team"). Accounts are deactivated, never deleted.

**Username**
The private name an account signs in with. It is never shown publicly as a byline by default.

## Public site

**Home page**
A short Welcome text followed by the latest Announcements.

**Welcome text**
The short greeting at the top of the Home page. It uses the wording from `notes/client-brief.md`: ASA is a Kenyon student group primarily for African students and students with African backgrounds, while welcoming anyone interested in African cultures and community. No other claims about ASA are made.

**Navigation**
The public menu: Announcements plus every published Page. The starter Pages for the demo are About ASA, Resources and Photos. They are placeholders, not a claim about ASA's real pages.

**Event card**
How an Announcement appears in the Announcements list. It is clear and readable on a phone.

**Decorative graphic**
A licensed image or graphic used for looks only. It is never presented as a photo of a real ASA event. Until ASA has permission for real photos, the Photos page says that actual event photos will be added then.

## Admin console

**Dashboard**
The first screen after signing in. It shows four content counts: Published Posts, Draft Posts, Published Pages and Draft Pages. Only the Admin also sees the number of active accounts and Deactivated accounts. It carries a clear reminder that marking content Published does not make it Live until `cms publish` and `cms deploy` run. It has no "Changes not live yet" indicator unless the app can determine that reliably. It stays simple on a phone.

**Content list**
One list of Posts and Pages, filtered by type (Post or Page) and by status (Draft or Published). Each row shows title, status, Display name and last-updated time.

## Writing

**Body**
The Markdown text of a Post or Page. Allowed: headings, emphasis, lists, links, and images with alt text. Raw HTML, scripts, iframes and forms are stripped and never run. Sanitizing happens in both the Preview and the public export.

**Preview**
The editor's view of a Post or Page. It shows the same rendered, sanitized content as the public page, not a separate approximation.

**Event details hint**
A short hint near the Post editor suggesting the body cover What, When, Where and Who can attend. It is not pre-filled into the body, and an Editor can hide it without deleting any content.

## Publishing

**Published**
A status in the admin console meaning a Post or Page is ready for the public site. It is not yet visible to visitors. Drafts are never Published and never leave the database.

**Live**
Visible to visitors: someone has run `cms publish` and `cms deploy` after the content was marked Published. _Avoid_: saying "published" when you mean Live.

**Release checklist**
A short, repeatable list of steps for making Published content Live. It also states the limit that an Editor cannot add a new image file alone, and is where Photo permission is confirmed before a real photo is added. For the class demo, the project author runs it from their own laptop. ASA has no known person responsible for this step, and none is assumed.

## Roles

**Admin**
An ASA leader. Manages accounts and permanent Pages: creates and deletes Pages, publishes or unpublishes them, and changes Page titles or slugs (which affect navigation and links).

**Editor**
Another ASA member. Creates and publishes Posts directly, because speed matters for announcements. May edit any Post, including another editor's, so event details can be corrected close to the event. May not delete a Post; only the Admin can. May update the body of an existing Page, so the Photos page can stay current, but may not create, delete, publish, unpublish, retitle or re-slug a Page. This is a design choice for the ASA site, not something observed in WordPress.

**Permission refusal**
What an Editor sees on any attempt at an Admin-only action, whether by button, typed address or direct submission: a clear "You don't have permission" page with a link back to the dashboard. Admin-only controls are also hidden from an Editor's normal screens, but hiding is never the protection. Editors may manage Posts and update the body of existing Pages; they may not manage users, delete content, change Page structure or publication status, or change slugs.

**Password reset**
The only way to recover a lost password. The Admin sets a new password for an existing account and cannot view the old one. The new password is stored hashed and is never printed or logged. The Admin passes it to the account owner outside the CMS through a trusted channel. There is no email link and no self-service reset.

## Out of scope for this version

Mentioned as possible later features, not built now.

- A separate Event content type, an event-date field, and automatic upcoming/past sorting.
- Photo upload forms, automatic gallery management, and photo approvals enforced by software. (The Photos page with approved images is in scope.)
- Account deletion, and a first-login password change flow.
- Email sending, including email-based password reset.
- A "Changes not live yet" indicator.
- RSVPs and sign-ups, comments, search, and tags or categories.
- Multi-site support, drag-and-drop page building, and a rich-text WYSIWYG editor.
- Any claim about ASA's real history, members, leaders, schedule or approval process.
