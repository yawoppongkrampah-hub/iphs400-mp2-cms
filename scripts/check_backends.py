#!/usr/bin/env python3
"""Check that the README's "Backends used" table, the usage ledger and the commit trailers agree.

    uv run python scripts/check_backends.py

The rubric's H6 asks for three records of which model backend did the work, and that they agree:
  1. the README's *Backends used* table (provider, model, used for, commit trailer),
  2. the `provider` and `model` columns of notes/usage-ledger.csv,
  3. a `Backend: <provider> <model>` trailer on commits made while a non-Anthropic backend was in use.

ChatGPT was planning and review assistance outside Claude Code, so it is a separate thing: it must be
disclosed in the README, and must not be a table row, a ledger provider or a commit trailer.

Exit code 0 when everything agrees, 1 with a list of disagreements or if the history cannot be read.
Reads files and `git log --all` (every branch, tag and stash, not only the current branch).
"""
from __future__ import annotations

import csv
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROVIDER = "anthropic"          # needs no commit trailer
SEPARATE_ASSISTANT = "chatgpt"
# Git trailer keys are case-insensitive. A placeholder such as `Backend: <provider> <model>` is not a trailer.
TRAILER = re.compile(r"(?mi)^[ \t]*Backend:[ \t]*([^\s<>]+)[ \t]+(.+?)[ \t]*$")
FENCE = re.compile(r"(?ms)^[ \t]*(```|~~~).*?^[ \t]*\1[ \t]*$")
# "Sonnet 5 / Sonnet 5.5" lists two models; a model id such as "anthropic/claude-x" stays whole.
MODEL_SPLIT = re.compile(r"\s+/\s+|\s*[;,]\s*")


def without_code(readme: str) -> str:
    """The README with fenced code blocks removed, so an example table in one is not the real table."""
    return FENCE.sub("", readme)


def prose(readme: str) -> str:
    """The README's running text: no code blocks and no table rows."""
    return "\n".join(line for line in without_code(readme).splitlines()
                     if not line.strip().startswith("|"))


def table_models(row: dict) -> set[str]:
    return {token.strip().lower() for token in MODEL_SPLIT.split(row.get("model", ""))}


def parse_table(readme: str) -> list[dict]:
    """The rows of the table under '### Backends used', keyed by lower-case header. [] if none."""
    readme = without_code(readme)
    heading = re.search(r"(?m)^#{2,4}\s+Backends used\s*$", readme)
    if not heading:
        return []
    lines = []
    for line in readme[heading.end():].splitlines():
        if line.strip().startswith("|"):
            lines.append(line)
        elif lines:
            break
    cells = [[c.strip() for c in line.strip().strip("|").split("|")] for line in lines]
    if len(cells) < 3 or not set("".join(cells[1])) <= set("-: "):      # header, separator, a row
        return []
    header = [h.lower() for h in cells[0]]
    return [dict(zip(header, row)) for row in cells[2:] if any(row)]


def trailer_pairs(history: str) -> list[tuple[str, str]]:
    return [(provider.lower(), model) for provider, model in TRAILER.findall(history)]


def check(readme: str, ledger: list[dict], history: str) -> list[str]:
    """Every disagreement between the table, the ledger and the trailers, as sentences."""
    table = parse_table(readme)
    if not table:
        return ["The README has no readable 'Backends used' table "
                "(a Markdown table under a 'Backends used' heading)."]
    found: list[str] = []
    table_providers = {row.get("provider", "").lower() for row in table}
    ledger_providers = {r.get("provider", "").strip().lower() for r in ledger} - {""}
    pairs = trailer_pairs(history)
    trailer_providers = {provider for provider, _ in pairs}

    # ChatGPT: disclosed in the README's own words, but never a backend.
    if SEPARATE_ASSISTANT not in prose(readme).lower():
        found.append("ChatGPT assistance is not disclosed in the README.")
    if any(SEPARATE_ASSISTANT in f"{row.get('provider', '')} {row.get('model', '')}".lower() for row in table):
        found.append("ChatGPT is listed in the Backends table; it is separate assistance, not a backend.")
    if any(SEPARATE_ASSISTANT in f"{r.get('provider', '')} {r.get('model', '')}".lower() for r in ledger):
        found.append("ChatGPT appears in the ledger's provider or model column; it is not a backend.")
    if any(SEPARATE_ASSISTANT in f"{provider} {model}".lower() for provider, model in pairs):
        found.append("A 'Backend:' commit trailer names ChatGPT; it is not a backend.")

    # Providers: table, ledger and trailers.
    for provider in sorted(ledger_providers - table_providers):
        found.append(f"Ledger provider '{provider}' has no row in the Backends table.")
    for provider in sorted(table_providers - ledger_providers - trailer_providers):
        found.append(f"The table lists '{provider}', but neither the ledger nor any commit trailer shows it used.")
    for provider in sorted((ledger_providers - {DEFAULT_PROVIDER}) - trailer_providers):
        found.append(f"Provider '{provider}' is in the ledger but no commit has a 'Backend: {provider} ...' trailer.")
    for provider in sorted(trailer_providers - table_providers):
        found.append(f"A commit trailer names '{provider}', which has no row in the Backends table.")
    for provider in sorted((trailer_providers - {DEFAULT_PROVIDER}) - ledger_providers):
        found.append(f"A commit trailer names '{provider}', which the ledger's provider column never records.")

    # Models: every model the ledger records for a provider is in that provider's table rows.
    for provider in sorted(ledger_providers & table_providers):
        listed = set().union(*(table_models(row) for row in table
                               if row.get("provider", "").lower() == provider))
        recorded = {r.get("model", "").strip() for r in ledger
                    if r.get("provider", "").strip().lower() == provider} - {""}
        for model in sorted(recorded):
            if model.lower() not in listed:
                found.append(f"Ledger model '{model}' ({provider}) is not in the table's Model column.")

    # A trailer's model must be one the table lists for that provider.
    for provider, model in pairs:
        listed = set().union(*(table_models(row) for row in table
                               if row.get("provider", "").lower() == provider), set())
        if provider in table_providers and model.lower() not in listed:
            found.append(f"A commit trailer 'Backend: {provider} {model}' names a model that is not "
                         f"in the table's Model column for {provider}.")

    # A backup row must point at its trailers.
    for row in table:
        provider = row.get("provider", "").lower()
        if provider != DEFAULT_PROVIDER and "none" in row.get("commit trailer", "").lower():
            found.append(f"The table's trailer column for '{provider}' says none, but a non-Anthropic "
                         "backend needs 'Backend:' trailers.")
    return found


def read_ledger() -> list[dict]:
    with (ROOT / "notes" / "usage-ledger.csv").open() as handle:
        return list(csv.DictReader(handle))


def read_history() -> str:
    """Every commit message in the repository. Raises RuntimeError if it cannot be read or is empty."""
    try:
        history = subprocess.run(["git", "log", "--all", "--format=%B"], cwd=ROOT, capture_output=True,
                                 text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as error:
        raise RuntimeError(f"Could not read the commit history with git ({error}).") from None
    if not history.strip():
        raise RuntimeError("git log returned no commits, so the trailers cannot be checked.")
    return history


def main() -> int:
    try:
        readme, ledger, history = (ROOT / "README.md").read_text(), read_ledger(), read_history()
    except (RuntimeError, OSError) as error:
        print(f"Cannot check the backends: {error}")
        return 1
    found = check(readme, ledger, history)
    if found:
        print("The Backends table, the ledger and the commit trailers disagree:")
        for line in found:
            print(f"  - {line}")
        return 1
    providers = sorted({r["provider"] for r in ledger if r.get("provider")})
    print(f"Backends table, ledger ({', '.join(providers)}) and commit trailers "
          f"({len(trailer_pairs(history))} found) agree. ChatGPT is disclosed as separate assistance.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
