"""T10: the README's Backends used table agrees with the ledger and the commit trailers.

The three places that must agree (the rubric's H6): the table, the ledger's
`provider` and `model` columns, and `Backend: <provider> <model>` commit trailers.
ChatGPT is separate planning assistance outside Claude Code, so it is disclosed in
the README's own words but is never a table row, a ledger provider or a trailer.
`scripts/check_backends.py` does the checking; these tests run it on the real
repository and on deliberately broken copies, so the check cannot pass by accident.
"""
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_backends", ROOT / "scripts" / "check_backends.py")
check_backends = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_backends)


@pytest.fixture
def readme():
    return (ROOT / "README.md").read_text()


@pytest.fixture
def ledger():
    return check_backends.read_ledger()


@pytest.fixture
def history():
    return check_backends.read_history()


def problems(readme, ledger, history):
    return check_backends.check(readme, ledger, history)


def with_extra_table_row(readme, row):
    """The README with one more row directly under the Backends table's separator line."""
    heading = readme.index("### Backends used")
    separator = readme.index("|---", heading)
    end = readme.index("\n", separator)
    return readme[:end + 1] + row + "\n" + readme[end + 1:]


BACKUP_ROW = "| OpenRouter | some-model | the backup | `Backend: openrouter some-model` |"


# -- the real repository -----------------------------------------------------------------

def test_the_real_readme_ledger_and_history_agree(readme, ledger, history):
    assert problems(readme, ledger, history) == []


def test_the_real_check_reads_what_it_should(readme, ledger, history):
    table = check_backends.parse_table(readme)
    assert [row["provider"].lower() for row in table] == ["anthropic"]
    assert {r["provider"].lower() for r in ledger} == {"anthropic"}
    assert check_backends.trailer_pairs(history) == []


def test_the_command_passes_on_this_repository():
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_backends.py")],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0 and "agree" in result.stdout


# -- every kind of disagreement is caught, each by its own message -----------------------------

def test_a_ledger_provider_missing_from_the_table_is_caught(readme, ledger, history):
    ledger = ledger + [{"provider": "openrouter", "model": "some-model"}]
    found = problems(readme, ledger, history)
    assert any("Ledger provider 'openrouter' has no row in the Backends table" in p for p in found)


def test_a_ledger_backup_with_no_commit_trailer_is_caught(readme, ledger, history):
    ledger = ledger + [{"provider": "openrouter", "model": "some-model"}]
    found = problems(with_extra_table_row(readme, BACKUP_ROW), ledger, history)
    assert any("in the ledger but no commit has a 'Backend: openrouter" in p for p in found)


def test_a_commit_trailer_for_a_provider_not_in_the_table_or_the_ledger_is_caught_twice_over(
        readme, ledger, history):
    found = problems(readme, ledger, history + "\nBackend: openrouter some-model\n")
    assert any("trailer names 'openrouter'" in p and "no row in the Backends table" in p for p in found)
    assert any("trailer names 'openrouter'" in p and "ledger's provider column never records" in p
               for p in found)


def test_a_table_row_nobody_used_is_caught(readme, ledger, history):
    found = problems(with_extra_table_row(readme, BACKUP_ROW), ledger, history)
    assert any("lists 'openrouter', but neither the ledger nor any commit trailer shows it used" in p
               for p in found)


def test_a_ledger_model_missing_from_the_table_is_caught(readme, ledger, history):
    ledger = ledger + [{"provider": "anthropic", "model": "Haiku 5.5"}]
    found = problems(readme, ledger, history)
    assert any("Ledger model 'Haiku 5.5'" in p for p in found)


def test_a_trailer_model_the_table_does_not_list_is_caught(readme, ledger, history):
    found = problems(readme, ledger, history + "\nBackend: anthropic Opus 9\n")
    assert any("'Backend: anthropic Opus 9' names a model that is not in the table" in p for p in found)


def test_a_backup_row_whose_trailer_column_says_none_is_caught(readme, ledger, history):
    readme = with_extra_table_row(readme, "| OpenRouter | some-model | the backup | none needed |")
    ledger = ledger + [{"provider": "openrouter", "model": "some-model"}]
    history = history + "\nBackend: openrouter some-model\n"
    found = problems(readme, ledger, history)
    assert any("trailer column for 'openrouter' says none" in p for p in found)


def test_a_complete_backup_declaration_passes(readme, ledger, history):
    """The positive control: table row, ledger rows and a trailer, all agreeing, give no problem."""
    readme = with_extra_table_row(readme, BACKUP_ROW)
    ledger = ledger + [{"provider": "openrouter", "model": "some-model"}]
    assert problems(readme, ledger, history + "\nBackend: openrouter some-model\n") == []


# -- trailers are found however git or a person writes them -----------------------------------------

@pytest.mark.parametrize("line", ["backend: openrouter some-model", "BACKEND: openrouter some-model",
                                  "    Backend: openrouter some-model", "Backend:openrouter   some-model  "])
def test_a_trailer_is_found_in_any_case_and_spacing(line):
    assert check_backends.trailer_pairs(f"Subject\n\nBody\n\n{line}\n") == [("openrouter", "some-model")]


@pytest.mark.parametrize("line", ["Backend: <provider> <model>", "> Backend: openrouter some-model",
                                  "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>",
                                  "The Backend: line is explained in the README"])
def test_a_placeholder_a_quotation_or_another_trailer_is_not_a_trailer(line):
    assert check_backends.trailer_pairs(f"Subject\n\n{line}\n") == []


def test_a_model_id_containing_a_slash_is_one_model(readme, ledger, history):
    readme = with_extra_table_row(readme, "| OpenRouter | vendor/model-x | the backup | `Backend:` trailer |")
    ledger = ledger + [{"provider": "openrouter", "model": "vendor/model-x"}]
    assert problems(readme, ledger, history + "\nBackend: openrouter vendor/model-x\n") == []


# -- ChatGPT is separate planning assistance ---------------------------------------------------

def test_chatgpt_as_a_backends_row_is_caught(readme, ledger, history):
    readme = with_extra_table_row(readme, "| OpenAI | ChatGPT | planning | none needed |")
    assert any("ChatGPT is listed in the Backends table" in p for p in problems(readme, ledger, history))


def test_chatgpt_as_a_ledger_provider_is_caught(readme, ledger, history):
    ledger = ledger + [{"provider": "chatgpt", "model": "ChatGPT"}]
    assert any("ChatGPT appears in the ledger" in p for p in problems(readme, ledger, history))


def test_chatgpt_as_a_commit_trailer_is_caught(readme, ledger, history):
    history = history + "\nBackend: openai ChatGPT\n"
    assert any("trailer names ChatGPT" in p for p in problems(readme, ledger, history))


def test_a_note_that_is_not_chatgpt_in_the_used_for_column_is_not_a_backend_row(readme, ledger, history):
    readme = readme.replace("| none needed |", "| none needed (ChatGPT was not used here) |")
    assert not any("listed in the Backends table" in p for p in problems(readme, ledger, history))


def test_chatgpt_help_that_is_not_disclosed_is_caught(readme, ledger, history):
    undisclosed = readme.replace("ChatGPT", "an assistant")
    assert any("not disclosed" in p for p in problems(undisclosed, ledger, history))


def test_a_mention_of_chatgpt_only_inside_a_code_block_is_not_a_disclosure(readme, ledger, history):
    hidden = readme.replace("ChatGPT", "an assistant") + "\n```\nChatGPT\n```\n"
    assert any("not disclosed" in p for p in problems(hidden, ledger, history))


def test_the_real_readme_discloses_chatgpt_in_prose_and_keeps_it_out_of_the_table(readme):
    assert "chatgpt" in check_backends.prose(readme).lower()
    assert all("chatgpt" not in " ".join(row.values()).lower() for row in check_backends.parse_table(readme))


# -- the table must be readable, and the history must be readable -------------------------------

def test_a_readme_with_no_backends_table_is_caught(ledger, history):
    found = problems("# Project\n\nNothing here.\n", ledger, history)
    assert len(found) == 1 and "no readable 'Backends used' table" in found[0]


def test_a_table_inside_a_code_block_is_not_the_real_table(readme, ledger, history):
    start = readme.index("### Backends used")
    table = re.search(r"(\|.*\n)+", readme[start:]).group(0)
    fenced = readme.replace(table, "```\n" + table + "```\n")
    found = problems(fenced, ledger, history)
    assert len(found) == 1 and "no readable 'Backends used' table" in found[0]


def test_an_unreadable_or_empty_history_is_an_error_not_a_pass(monkeypatch, capsys):
    def fail():
        raise RuntimeError("git log returned no commits, so the trailers cannot be checked.")
    monkeypatch.setattr(check_backends, "read_history", fail)
    assert check_backends.main() == 1
    assert "Cannot check the backends" in capsys.readouterr().out


def test_read_history_refuses_an_empty_log(monkeypatch):
    class Done:
        stdout = "\n"
    monkeypatch.setattr(check_backends.subprocess, "run", lambda *a, **k: Done())
    with pytest.raises(RuntimeError, match="no commits"):
        check_backends.read_history()


def test_read_history_reports_a_git_failure_plainly(monkeypatch):
    def broken(*args, **kwargs):
        raise subprocess.CalledProcessError(128, "git")
    monkeypatch.setattr(check_backends.subprocess, "run", broken)
    with pytest.raises(RuntimeError, match="Could not read the commit history"):
        check_backends.read_history()
