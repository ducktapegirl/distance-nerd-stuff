#!/usr/bin/env python3
"""Fail if any git-tracked text file contains a British spelling.

Enforces the "Writing prose — US English" rule in CLAUDE.md. That rule used
to live only as a note in `Project Docs/Specs/2026-09-07-us-english-follow-ups.md`
describing a one-off cleanup -- nothing stopped the next new file (in
practice, the Art views added afterward) from reintroducing British spelling,
because nothing ever re-checked it. This script is the re-check.

Scope, matching the exclusions that doc already established:
  - Only git-tracked files (`git ls-files`), so build output and local scratch
    files are never scanned.
  - Activity data and historical input logs are prose-free data, not writing:
    `running-log/running_log.csv`, `strava-data/data/**`, `running-log/source/**`.
  - `2026-09-07-us-english-follow-ups.md` itself is skipped: it intentionally
    quotes British-spelled identifiers (`colour=`, `centre(ring)`) as its own
    subject matter, not prose to correct.
  - Any file with an extremely long line is skipped as a heuristic for an
    embedded binary/base64 blob inside a text-typed file (seen in a design-tool
    HTML export) -- a byte scan finding letters in binary is not a spelling bug.

Word matching, to avoid the exact false positive that motivated this note:
`recentRelayFailures` contains "centRe" as a case-insensitive substring but is
not the word "centre" -- a bare `re.search(r"centre", ..., re.I)` fires on it.
Every stem below requires a trailing word boundary; the `centre`/`colour`
families additionally allow no *leading* boundary, since a prefixed British
form (`recentred`, `discoloured`) is exactly what this check exists to catch.

Identifiers are out of scope by construction, not by exclusion: Python files
are tokenized and only COMMENT/STRING tokens are checked (never NAME), and
Markdown files have fenced code blocks and inline `backticks` stripped first.
A renamed identifier is a separate, deliberate decision (see CLAUDE.md) --
this script must never be the thing that silently proposes one.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tokenize
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SKIP_DIRS = ("running-log/source/", "strava-data/data/")
SKIP_FILES = {
    "running-log/running_log.csv",
    # Intentionally quotes already-renamed identifiers as its own subject
    # matter -- see the module docstring.
    "Project Docs/Specs/2026-09-07-us-english-follow-ups.md",
}
CHECKED_SUFFIXES = {".py", ".js", ".md", ".html"}

# Longest legitimate line in this repo's prose files is nowhere near this;
# a line past it is almost certainly an embedded binary/base64 blob.
MAX_LINE_LEN = 4000

# (stem pattern without \b, allow a prefix like "re-"/"dis-" before it)
_PREFIXABLE = ["centre", "colour"]
_STEMS = [
    "behaviour", "neighbourhood", "neighbour", "grey", "optimise",
    "analyse", "organise", "recognise", "favourite", "favour", "licence",
    "defence", "travelled", "travelling", "traveller", "cancelled",
    "cancelling", "modelled", "modelling", "labelled", "labelling",
    "catalogue", "programme", "metre", "litre", "fibre", "theatre",
    "aluminium", "honour", "flavour", "humour", "rumour", "artefact",
    "realise", "utilise", "characterise", "capitalise", "emphasise",
    "summarise", "manoeuvre", "mould", "sceptic", "jewellery", "pyjamas",
    "signalling", "counselling", "levelled", "levelling", "fuelled",
    "fuelling", "channelled", "channelling", "marvellous", "woollen",
    "aeroplane", "tyre", "kerb", "plough", "storey", "cosy", "colonise",
    "memorise", "categorise", "prioritise", "customise", "minimise",
    "maximise", "apologise", "criticise", "synchronise", "standardise",
    "specialise", "generalise", "localise", "visualise", "finalise",
    "initialise", "stabilise", "mobilise", "symbolise", "harmonise",
    "familiarise",
]

_SUFFIX = r"(?:s|d|ed|ing|ation|ations)?\b"
_parts = [rf"{stem}{_SUFFIX}" for stem in _PREFIXABLE]  # no leading \b
_parts += [rf"\b{stem}{_SUFFIX}" for stem in _STEMS]
WORD_RE = re.compile("|".join(_parts), re.IGNORECASE)

FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
BACKTICK_RE = re.compile(r"`[^`\n]*`")


def _tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return out.stdout.splitlines()


def _skip(rel_path: str) -> bool:
    if rel_path in SKIP_FILES:
        return True
    if any(rel_path.startswith(d) for d in SKIP_DIRS):
        return True
    return Path(rel_path).suffix not in CHECKED_SUFFIXES


def _has_binary_blob(text: str) -> bool:
    return any(len(line) > MAX_LINE_LEN for line in text.splitlines())


def _prose_spans_py(text: str) -> list[tuple[int, str]]:
    """[(lineno, text)] for COMMENT/STRING tokens only -- never NAME."""
    spans = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                spans.append((tok.start[0], tok.string))
    except tokenize.TokenizeError:
        pass
    return spans


def _blank_preserving_newlines(m: re.Match) -> str:
    """Replace a fenced block with the same number of blank lines, so every
    later line's number still matches the original file."""
    return "\n" * m.group(0).count("\n")


def _prose_spans_md(text: str) -> list[tuple[int, str]]:
    """Whole file, minus fenced blocks and inline backticks -- line numbers
    preserved so hits point at the real file."""
    stripped = FENCE_RE.sub(_blank_preserving_newlines, text)
    stripped = BACKTICK_RE.sub("", stripped)
    return [(i + 1, line) for i, line in enumerate(stripped.splitlines())]


def _prose_spans_raw(text: str) -> list[tuple[int, str]]:
    return [(i + 1, line) for i, line in enumerate(text.splitlines())]


def check_file(rel_path: str) -> list[str]:
    path = ROOT / rel_path
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, FileNotFoundError):
        return []
    if _has_binary_blob(text):
        return []

    suffix = Path(rel_path).suffix
    if suffix == ".py":
        spans = _prose_spans_py(text)
    elif suffix == ".md":
        spans = _prose_spans_md(text)
    else:
        spans = _prose_spans_raw(text)

    hits = []
    for start_line, chunk in spans:
        for m in WORD_RE.finditer(chunk):
            # start_line is where the span (a whole comment/string token, or a
            # single physical line) begins; add how many newlines precede the
            # match *within* that span so multi-line docstrings still report
            # the real line the word is on, not just the token's first line.
            lineno = start_line + chunk[: m.start()].count("\n")
            hits.append(f"{rel_path}:{lineno}: {m.group(0)!r}")
    return hits


def main() -> int:
    all_hits: list[str] = []
    for rel_path in _tracked_files():
        if _skip(rel_path):
            continue
        all_hits.extend(check_file(rel_path))

    if all_hits:
        print("British spelling found (see CLAUDE.md, 'Writing prose - US English'):")
        for hit in all_hits:
            print("  " + hit)
        print(f"\n{len(all_hits)} instance(s). Fix the prose, not the identifier --")
        print("renaming a live function/parameter is a separate, deliberate change.")
        return 1

    print(f"US-English spelling check: {len(_tracked_files())} tracked files scanned, no hits.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
