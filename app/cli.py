"""The `cms` command: serve, publish, deploy, create-admin.

    uv run cms create-admin --username NAME --display-name "ASA Leadership"
                          # password is read from CMS_ADMIN_PASSWORD, never typed or printed
    uv run cms serve      # admin console + public preview at http://localhost:8000
    uv run cms publish    # render site/ from published content
    uv run cms deploy     # push site/ to the gh-pages branch (Pages serves it)
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

from app import accounts, settings
from app.publish import render_site


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cms")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="run the admin console locally")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true", default=True)
    admin = sub.add_parser("create-admin", help="create the first Admin account")
    admin.add_argument("--username", required=True)
    admin.add_argument("--display-name", required=True,
                       help="the public byline, e.g. 'ASA Leadership'")
    sub.add_parser("publish", help="render site/ from published content")
    deploy = sub.add_parser("deploy", help="push site/ to gh-pages")
    deploy.add_argument("--message", default="Publish site")
    args = parser.parse_args(argv)

    if args.command == "serve":
        import uvicorn

        uvicorn.run("app.main:app", port=args.port, reload=args.reload)
        return 0

    if args.command == "create-admin":
        password = os.environ.get("CMS_ADMIN_PASSWORD")
        if not password:
            print("Set CMS_ADMIN_PASSWORD in the environment (see .env.example).")
            return 1
        try:
            accounts.create_account(
                settings.DATABASE_PATH, username=args.username, password=password,
                role="admin", display_name=args.display_name)
        except accounts.AccountError as error:
            print(error)
            return 1
        print(f"Created Admin account '{args.username}'.")
        return 0

    if args.command == "publish":
        out = render_site()
        print(f"Wrote {out}. Preview it with:  python3 -m http.server -d {out} 8001")
        return 0

    if args.command == "deploy":
        if not settings.SITE.exists():
            print("site/ does not exist yet — run `uv run cms publish` first.")
            return 1
        result = subprocess.run(
            [sys.executable, "-m", "ghp_import", "-n", "-p", "-m", args.message,
             str(settings.SITE)],
        )
        if result.returncode == 0:
            print("Pushed to gh-pages. Settings -> Pages -> Deploy from a branch -> "
                  "gh-pages / root, then wait up to 10 minutes.")
        return result.returncode
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
