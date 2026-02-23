# AGENTS.md — bc-al-chunker

## Project Overview

`bc-al-chunker` is a **zero-dependency** Python library that statically parses Business Central AL (`.al`) files and produces semantically-aware chunks optimized for embedding and retrieval-augmented generation (RAG). It understands every AL object type (tables, pages, codeunits, reports, queries, enums, interfaces, and all extension types) and splits large objects at natural semantic boundaries while keeping small objects whole.

- **Language:** Python ≥ 3.12 (uses `StrEnum`, PEP 604 unions, `slots=True` dataclasses)
- **Build system:** Hatchling
- **Package manager:** uv (preferred), pip also works
- **Core dependencies:** None — `httpx` is only needed for optional remote adapters
- **License:** MIT

## Repository Layout

```
pyproject.toml                     # Build config, deps, tool settings (ruff, mypy, pytest)
README.md                          # User-facing documentation
src/bc_al_chunker/
    __init__.py                    # Public API façade: chunk(), chunk_source(), re-exports
    models.py                      # All dataclasses + enums (ALObject, Chunk, ChunkMetadata, etc.)
    config.py                      # ChunkingConfig dataclass
    parser.py                      # Regex + brace-matching AL parser (no external deps)
    chunker.py                     # Hierarchical chunking algorithm
    serializers.py                 # JSON/JSONL import/export, dict conversion
    py.typed                       # PEP 561 typed marker
    adapters/
        __init__.py                # FileSource Protocol definition
        local.py                   # Local filesystem adapter (os.scandir, stdlib only)
        github.py                  # GitHub Git Trees + Blobs API adapter (requires httpx)
        azure_devops.py            # Azure DevOps REST API adapter (requires httpx)
tests/
    conftest.py                    # Shared fixtures: FIXTURES_DIR, read_fixture(), fixtures_dir
    test_parser.py                 # Parser tests (object detection, sections, procedures, properties, edge cases)
    test_chunker.py                # Chunking tests (whole vs split, context headers, metadata)
    test_api.py                    # Integration tests for top-level chunk() and serializer roundtrips
    test_serializers.py            # JSON/JSONL roundtrip and dict conversion tests
    test_adapters/
        test_local.py              # LocalAdapter tests
        test_github.py             # GitHubAdapter tests (uses respx for HTTP mocking)
        test_azure_devops.py       # AzureDevOpsAdapter tests (uses respx for HTTP mocking)
    fixtures/                      # 11 real .al files covering all major AL object types
        simple_table.al, simple_enum.al, large_codeunit.al, page_card.al,
        page_list.al, page_extension.al, table_extension.al,
        table_with_triggers.al, report.al, query.al, interface.al
```

## Architecture

### Module Dependency Graph

```
__init__.py  (public façade — wires everything together)
  ├── config.py         (ChunkingConfig dataclass)
  ├── models.py         (all data types — bottom of the dependency tree)
  ├── parser.py         (depends on models)
  ├── chunker.py        (depends on models + config)
  ├── serializers.py    (depends on models only)
  └── adapters/
        ├── __init__.py (FileSource Protocol — no internal deps)
        ├── local.py    (stdlib only, no internal deps)
        ├── github.py   (optional httpx, no internal deps)
        └── azure_devops.py (optional httpx, no internal deps)
```

Dependencies flow strictly downward. Adapters are fully independent of the core.

### Core Data Model (models.py)

All types use `@dataclass(slots=True)`. Value objects use `frozen=True`.

| Type            | Purpose                                                                                  |
| --------------- | ---------------------------------------------------------------------------------------- |
| `ALObjectType`  | `StrEnum` — 19 BC object types (e.g. `"table"`, `"pageextension"`)                       |
| `ChunkType`     | `StrEnum` — `WHOLE_OBJECT`, `HEADER`, `SECTION`, `PROCEDURE`, `TRIGGER`                  |
| `ALProperty`    | Name/value pair with line range                                                          |
| `ALSection`     | Named section (fields, layout, actions, etc.) with optional children                     |
| `ALProcedure`   | Procedure/trigger with access modifier, attributes, return type                          |
| `ALObject`      | Complete parsed AL object (the AST root); includes `file_hash` (BLAKE2b hex)             |
| `ChunkMetadata` | Frozen — rich metadata for each chunk (object info, line range, attributes, `file_hash`) |
| `Chunk`         | Frozen — `content` + `metadata` + `token_estimate` (the embedding-ready output)          |

### Parser (parser.py)

The parser uses **regex + brace-matching** with no external dependencies:

1. **Object header detection** — Multiline regex matching all 19 AL object types (longer keywords listed first to prevent partial matches)
2. **Brace-block resolution** — Correctly skips AL string literals (`'...'`), line/block comments, and quoted identifiers (`"..."`)
3. **Section extraction** — Matches top-level section keywords (`fields`, `keys`, `layout`, `actions`, `views`, `dataset`, etc.)
4. **Procedure/trigger extraction** — Matches attributes, access modifiers, `procedure`/`trigger` keywords; resolves body via nested `begin`/`end` tracking
5. **Property extraction** — Matches `Name = Value;` lines, filtering out matches inside sections/procedures6. **File hashing** — `hash_source()` computes a 16-character BLAKE2b hex digest (8-byte, stdlib `hashlib`) of the BOM-stripped source; called automatically inside `parse_source()` and stored on every `ALObject.file_hash`

### Chunker (chunker.py)

Hierarchical, size-gated splitting:

1. If object source ≤ `max_chunk_chars` → one `WholeObject` chunk
2. Otherwise split into: **Header** (declaration + properties) → **Sections** (one per section, sub-split if oversized) → **Procedures/Triggers** (one each)
3. Sub-chunks get a synthetic context header (`// Object: ... // File: ...`) prepended for self-contained embedding
4. Token estimation: `chars // 4`, minimum 1

### Adapters

`FileSource` is a `@runtime_checkable` Protocol with:

- `iter_al_files_sync() -> list[tuple[str, str]]` (synchronous)
- `iter_al_files() -> AsyncIterator[tuple[str, str]]` (async)

`chunk_source()` tries sync first, falls back to `asyncio.run()` for async adapters.

## Setup & Development Commands

### Install dependencies

```bash
uv sync --all-extras --group dev
```

### Run tests (75 tests, ~1.5s)

```bash
uv run pytest tests/ -v
```

To run a single test file:

```bash
uv run pytest tests/test_parser.py -v
```

To run a specific test class or method:

```bash
uv run pytest tests/test_parser.py::TestObjectDetection -v
uv run pytest tests/test_chunker.py::TestChunkObject::test_small_object_stays_whole -v
```

### Lint and format

```bash
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

### Type check

```bash
uv run python -m mypy src/
```

> **Note:** Use `python -m mypy` rather than bare `mypy` — the latter may fail to resolve the installed package on some environments.

### Full validation sequence (always run before committing)

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run python -m mypy src/
uv run pytest tests/ -v
```

## Code Style & Conventions

### Python Style

- **Always** use `from __future__ import annotations` at the top of every module
- Use `TYPE_CHECKING` guards for type-only imports (avoids runtime import of optional deps)
- Full type annotations on all functions (public and private)
- Use PEP 604 union syntax: `str | None`, not `Optional[str]`
- Use `list[X]`, `tuple[X, ...]` (lowercase) — not `List`, `Tuple`
- All dataclasses use `slots=True`; value objects add `frozen=True`
- Private functions/constants prefixed with `_` (e.g., `_find_brace_block`, `_RE_OBJECT_HEADER`)
- Regex pattern constants prefixed `_RE_`
- Line length: 99 characters (configured in ruff)
- Docstrings: Google-style with `Args:` / `Returns:` sections
- Imports sorted by isort (handled by ruff `I` rule)
- No `print()` statements (enforced by ruff `T20` rule)

### Testing Style

- pytest with class-based test organization (e.g., `TestObjectDetection`, `TestChunkObject`)
- Direct `assert` statements — no unittest-style `self.assert*`
- Shared fixtures in `tests/conftest.py`; use `read_fixture("name.al")` to load fixture files
- Adapter tests use `respx` for HTTP mocking
- `asyncio_mode = "auto"` — async test functions are auto-detected
- Always add or update tests when changing functionality

### Adding a New AL Fixture

1. Create a `.al` file in `tests/fixtures/`
2. Use it in tests via `read_fixture("filename.al")`

### Adding a New Adapter

1. Create `src/bc_al_chunker/adapters/new_adapter.py`
2. Implement the `FileSource` Protocol (both `iter_al_files_sync` and `iter_al_files`)
3. Add tests in `tests/test_adapters/test_new_adapter.py`
4. If it requires an external dependency, add it as an optional extra in `pyproject.toml` under `[project.optional-dependencies]`
5. Do **not** import optional deps at module top level — guard with `try`/`except ImportError` or `TYPE_CHECKING`

### Adding a New AL Object Type

1. Add the type to `ALObjectType` enum in `models.py`
2. Update the `_RE_OBJECT_HEADER` regex in `parser.py` (place longer keywords before shorter ones to prevent partial matches)
3. Add a fixture `.al` file and corresponding parser + chunker tests

## Key Implementation Details

- The parser handles multiple objects per `.al` file
- BOM (`\ufeff`) is stripped automatically on parse
- Interfaces have no numeric ID — defaulting to `0`
- `_find_brace_block` and `_find_end_semicolon` both implement string/comment skipping — a bug in either cascades to all extraction logic
- `_extract_header` in `chunker.py` tracks brace depth line-by-line and strips procedure/trigger lines at depth 1
- `ChunkMetadata.attributes` is stored as `tuple[str, ...]` (frozen compat) but serialized as JSON array — deserialization normalizes `list` → `tuple`
- Serializers use `dataclasses.asdict()` and manual reconstruction with `.get()` defaults for forward compatibility

## Public API Entry Points

The two main user-facing functions are in `__init__.py`:

- `chunk(paths, *, config=None) -> list[Chunk]` — local filesystem convenience
- `chunk_source(source, *, config=None) -> list[Chunk]` — any `FileSource` adapter

All public symbols are listed in `__all__` in `__init__.py`. When adding new public APIs, always update `__all__`.
