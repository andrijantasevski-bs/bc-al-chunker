"""AL file parser — regex + brace-matching approach.

Parses .al source files into structured ``ALObject`` trees without external
dependencies.  Handles all Business Central object types, quoted identifiers,
nested braces, string literals, comments, and preprocessor directives.
"""

from __future__ import annotations

import hashlib
import re
from typing import TYPE_CHECKING

from bc_al_chunker.models import (
    ALObject,
    ALObjectType,
    ALProcedure,
    ALProperty,
    ALSection,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

# ---------------------------------------------------------------------------
# Pre-compiled regexes (case-insensitive)
# ---------------------------------------------------------------------------

_OBJECT_TYPE_PATTERN = "|".join(
    [
        "tableextension",
        "pageextension",
        "pagecustomization",
        "reportextension",
        "enumextension",
        "permissionsetextension",
        "permissionset",
        "controladdin",
        "entitlement",
        "codeunit",
        "xmlport",
        "interface",
        "profile",
        "report",
        "table",
        "query",
        "dotnet",
        "page",
        "enum",
    ]
)

# Matches:  table 50104 "Address"
#           tableextension 50135 TableExt extends "Table With Relation"
#           interface "IAddressProvider"
_RE_OBJECT_HEADER = re.compile(
    rf"""
    ^\s*                                        # leading whitespace
    (?P<type>{_OBJECT_TYPE_PATTERN})             # object type keyword
    \s+
    (?:(?P<id>\d+)\s+)?                         # optional numeric ID
    (?P<name>"[^"]*"|[A-Za-z_]\w*)              # quoted or simple name
    (?:\s+extends\s+(?P<extends>"[^"]*"|[A-Za-z_]\w*))? # optional extends
    (?:\s+implements\s+(?P<implements>"[^"]*"(?:\s*,\s*"[^"]*")*))? # optional implements
    \s*$                                        # up to EOL
    """,
    re.IGNORECASE | re.MULTILINE | re.VERBOSE,
)

_RE_IMPLEMENTS_SPLIT = re.compile(r'"([^"]+)"')

# Sections that appear as top-level blocks inside objects.
_SECTION_KEYWORDS: frozenset[str] = frozenset(
    {
        "fields",
        "keys",
        "layout",
        "actions",
        "views",
        "dataset",
        "requestpage",
        "schema",
        "elements",
        "rendering",
        "labels",
        "trigger",
        "dataitem",
    }
)

# Procedure / trigger header.
_RE_PROCEDURE = re.compile(
    r"""
    ^[ \t]*                                       # leading whitespace
    (?P<attrs>(?:\[.*?\]\s*)*)                     # optional attributes (multi-line OK)
    (?P<access>local\s+|internal\s+|protected\s+)? # optional access modifier
    (?P<kind>procedure|trigger)                    # keyword
    \s+
    (?P<name>"[^"]*"|[A-Za-z_]\w*)                # name
    \s*\(                                          # opening paren
    """,
    re.IGNORECASE | re.MULTILINE | re.VERBOSE | re.DOTALL,
)

# Simple property line:  PropertyName = Value;
_RE_PROPERTY = re.compile(
    r"""
    ^[ \t]*
    (?P<name>[A-Za-z]\w*)          # property name
    \s*=\s*
    (?P<value>.+?)\s*;\s*$         # value up to semicolon
    """,
    re.MULTILINE | re.VERBOSE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unquote(name: str) -> str:
    """Strip surrounding double-quotes from an identifier."""
    if name.startswith('"') and name.endswith('"'):
        return name[1:-1]
    return name


def _parse_implements(raw: str | None) -> list[str]:
    """Parse the ``implements`` clause into a list of interface names."""
    if not raw:
        return []
    return _RE_IMPLEMENTS_SPLIT.findall(raw)


def _line_number(source: str, index: int) -> int:
    """Return 1-based line number for a character offset."""
    return source.count("\n", 0, index) + 1


def _find_brace_block(source: str, start: int) -> int | None:
    """Return the index of the closing ``}`` that matches the ``{`` at *start*.

    Skips braces inside string literals (``'...'``) and comments
    (``// ...`` and ``/* ... */``).  Returns ``None`` if unmatched.
    """
    depth = 0
    i = start
    length = len(source)
    while i < length:
        ch = source[i]
        if ch == "'":
            # AL string literal — skip to closing quote.
            i += 1
            while i < length and source[i] != "'":
                i += 1
        elif ch == "/" and i + 1 < length:
            nch = source[i + 1]
            if nch == "/":
                # Single-line comment — skip to EOL.
                i = source.find("\n", i)
                if i == -1:
                    return None
            elif nch == "*":
                # Block comment — skip to closing */
                end = source.find("*/", i + 2)
                if end == -1:
                    return None
                i = end + 1
        elif ch == '"':
            # Quoted identifier — skip to closing quote.
            i += 1
            while i < length and source[i] != '"':
                i += 1
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return None


def _find_end_semicolon(source: str, start: int) -> int | None:
    """Find the matching ``end;`` from *start*, tracking begin/end nesting.

    *start* should point to the first character of the ``begin`` keyword.
    Returns the index of the ``;`` in the closing ``end;``.
    """
    # We use a simple state machine: count nested begin/end pairs.
    depth = 0
    i = start
    length = len(source)
    while i < length:
        ch = source[i]
        # Skip strings
        if ch == "'":
            i += 1
            while i < length and source[i] != "'":
                i += 1
            i += 1
            continue
        # Skip comments
        if ch == "/" and i + 1 < length:
            nch = source[i + 1]
            if nch == "/":
                nl = source.find("\n", i)
                i = nl + 1 if nl != -1 else length
                continue
            if nch == "*":
                end = source.find("*/", i + 2)
                i = end + 2 if end != -1 else length
                continue
        # Skip quoted identifiers
        if ch == '"':
            i += 1
            while i < length and source[i] != '"':
                i += 1
            i += 1
            continue

        # Case-insensitive keyword check.  We look for word boundaries.
        low5 = source[i : i + 5].lower()
        if (
            low5 == "begin"
            and (i + 5 >= length or not source[i + 5].isalnum())
            and (i == 0 or not source[i - 1].isalnum())
        ):
            depth += 1
            i += 5
            continue
        low3 = source[i : i + 3].lower()
        if (
            low3 == "end"
            and (i + 3 >= length or not source[i + 3].isalnum())
            and (i == 0 or not source[i - 1].isalnum())
        ):
            depth -= 1
            if depth == 0:
                # Advance past "end" and the semicolon.
                j = i + 3
                while j < length and source[j] in " \t\r\n":
                    j += 1
                if j < length and source[j] == ";":
                    return j
                # Tolerate missing semicolon.
                return i + 2
            i += 3
            continue
        i += 1
    return None


# ---------------------------------------------------------------------------
# Top-level section extraction
# ---------------------------------------------------------------------------

_RE_SECTION_START = re.compile(
    r"""
    ^[ \t]*
    (?P<name>"""
    + "|".join(sorted(_SECTION_KEYWORDS, key=len, reverse=True))
    + r""")
    \s*(?:\([^)]*\)\s*)?   # optional parenthesized qualifier, e.g. area(content)
    \s*\{
    """,
    re.IGNORECASE | re.MULTILINE | re.VERBOSE,
)


def _extract_sections(body: str, body_offset: int, source: str) -> list[ALSection]:
    """Extract top-level structural sections from an object body."""
    sections: list[ALSection] = []
    for m in _RE_SECTION_START.finditer(body):
        brace_pos = body.index("{", m.start())
        abs_brace = body_offset + brace_pos
        close = _find_brace_block(source, abs_brace)
        if close is None:
            continue
        raw = source[body_offset + m.start() : close + 1]
        sections.append(
            ALSection(
                name=m.group("name").lower(),
                raw_source=raw,
                line_start=_line_number(source, body_offset + m.start()),
                line_end=_line_number(source, close),
            )
        )
    return sections


# ---------------------------------------------------------------------------
# Procedure / trigger extraction
# ---------------------------------------------------------------------------


def _extract_procedures(body: str, body_offset: int, source: str) -> list[ALProcedure]:
    """Extract procedures and triggers from the object body."""
    procs: list[ALProcedure] = []
    for m in _RE_PROCEDURE.finditer(body):
        kind = m.group("kind").lower()
        is_trigger = kind == "trigger"
        name = _unquote(m.group("name"))
        attrs_raw = m.group("attrs") or ""
        attrs = [a.strip() for a in re.findall(r"\[.*?\]", attrs_raw, re.DOTALL)]
        access = (m.group("access") or "").strip().lower()

        # Find the body: scan for `begin` after the parameter list, then `end;`.
        abs_start = body_offset + m.start()

        # For triggers/procedures that use begin...end:
        search_from = body_offset + m.end()
        # Find 'begin' keyword (skip var block if present)
        begin_pattern = re.compile(r"\bbegin\b", re.IGNORECASE)
        begin_match = begin_pattern.search(source, search_from)
        if begin_match is None:
            continue
        end_pos = _find_end_semicolon(source, begin_match.start())
        if end_pos is None:
            continue
        raw = source[abs_start : end_pos + 1]
        procs.append(
            ALProcedure(
                name=name,
                raw_source=raw,
                line_start=_line_number(source, abs_start),
                line_end=_line_number(source, end_pos),
                is_trigger=is_trigger,
                access_modifier=access,
                attributes=attrs,
            )
        )
    return procs


# ---------------------------------------------------------------------------
# Property extraction
# ---------------------------------------------------------------------------


def _extract_properties(
    body: str, body_offset: int, source: str, sections: list[ALSection], procs: list[ALProcedure]
) -> list[ALProperty]:
    """Extract top-level properties that sit outside sections and procedures."""
    # Build a set of character ranges covered by sections/procs.
    covered: list[tuple[int, int]] = []
    for sec in sections:
        sec_start_abs = source.index(sec.raw_source, body_offset)
        covered.append((sec_start_abs, sec_start_abs + len(sec.raw_source)))
    for proc in procs:
        proc_start_abs = source.index(proc.raw_source, body_offset)
        covered.append((proc_start_abs, proc_start_abs + len(proc.raw_source)))

    props: list[ALProperty] = []
    for m in _RE_PROPERTY.finditer(body):
        abs_pos = body_offset + m.start()
        # Skip if inside a covered range.
        if any(s <= abs_pos < e for s, e in covered):
            continue
        props.append(
            ALProperty(
                name=m.group("name"),
                value=m.group("value").strip(),
                line_start=_line_number(source, abs_pos),
                line_end=_line_number(source, body_offset + m.end()),
            )
        )
    return props


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _normalize_object_type(raw: str) -> ALObjectType:
    """Convert a raw object type string to the enum, case-insensitive."""
    return ALObjectType(raw.lower().replace(" ", ""))


def hash_source(source: str) -> str:
    """Compute a fast content hash of AL source text.

    Uses BLAKE2b with an 8-byte (64-bit) digest — the fastest built-in hash
    algorithm in Python's :mod:`hashlib`.  The resulting 16-character hex
    string is compact and sufficient for file-change detection across hundreds
    or thousands of files.

    The hash is computed on the BOM-stripped, UTF-8-encoded source so the
    value is identical regardless of whether the caller stripped the BOM.

    Args:
        source: AL source text (with or without leading BOM).

    Returns:
        A 16-character lowercase hex string.
    """
    if source.startswith("\ufeff"):
        source = source[1:]
    return hashlib.blake2b(source.encode("utf-8"), digest_size=8).hexdigest()


def parse_source(source: str, *, file_path: str = "") -> list[ALObject]:
    """Parse AL source code and return a list of ``ALObject`` instances.

    A single ``.al`` file typically contains one object, but this function
    supports multiple objects per file.

    Args:
        source: The full text of the AL file.
        file_path: The path of the source file (stored in metadata).

    Returns:
        A list of parsed ``ALObject`` instances.
    """
    # Strip BOM.
    if source.startswith("\ufeff"):
        source = source[1:]

    file_hash = hashlib.blake2b(source.encode("utf-8"), digest_size=8).hexdigest()

    objects: list[ALObject] = []

    for hdr in _RE_OBJECT_HEADER.finditer(source):
        obj_type = _normalize_object_type(hdr.group("type"))
        obj_id = int(hdr.group("id")) if hdr.group("id") else 0
        obj_name = _unquote(hdr.group("name"))
        extends = _unquote(hdr.group("extends")) if hdr.group("extends") else ""
        implements = _parse_implements(hdr.group("implements"))

        # Find opening brace of the object body.
        brace_start = source.find("{", hdr.end())
        if brace_start == -1:
            continue
        brace_end = _find_brace_block(source, brace_start)
        if brace_end is None:
            continue

        raw_source = source[hdr.start() : brace_end + 1]
        body = source[brace_start + 1 : brace_end]
        body_offset = brace_start + 1

        sections = _extract_sections(body, body_offset, source)
        procs = _extract_procedures(body, body_offset, source)
        props = _extract_properties(body, body_offset, source, sections, procs)

        objects.append(
            ALObject(
                object_type=obj_type,
                object_id=obj_id,
                object_name=obj_name,
                raw_source=raw_source,
                file_path=file_path,
                line_start=_line_number(source, hdr.start()),
                line_end=_line_number(source, brace_end),
                extends=extends,
                implements=implements,
                properties=props,
                sections=sections,
                procedures=procs,
                file_hash=file_hash,
            )
        )

    return objects


def parse_file(path: str) -> list[ALObject]:
    """Read an ``.al`` file from disk and parse it.

    Handles UTF-8 and UTF-8 with BOM encodings.
    """
    with open(path, encoding="utf-8-sig") as f:
        source = f.read()
    return parse_source(source, file_path=path)


def parse_files(paths: Sequence[str]) -> list[ALObject]:
    """Parse multiple ``.al`` files and return all objects."""
    objects: list[ALObject] = []
    for p in paths:
        objects.extend(parse_file(p))
    return objects
