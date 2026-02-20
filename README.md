# bc-al-chunker

RAG-optimized chunking for Business Central AL files.

`bc-al-chunker` statically parses `.al` files and produces semantically-aware chunks optimized for embedding and retrieval-augmented generation (RAG). It understands the structure of every AL object type — tables, pages, codeunits, reports, queries, enums, interfaces, and all extension types — and splits large objects at natural semantic boundaries (sections, procedures, triggers) while keeping small objects whole.

## Features

- **Hierarchical chunking** — small objects stay whole; large objects split at procedure/trigger/section boundaries
- **Context headers** — every sub-chunk gets a synthetic context comment so each chunk is self-contained for embedding
- **All AL object types** — table, page, codeunit, report, query, xmlport, enum, interface, permissionset, profile, controladdin, entitlement, and all extension variants
- **Multiple data sources** — local filesystem, GitHub API, Azure DevOps API
- **Structured output** — Python dataclasses with JSON and JSONL export
- **Zero dependencies** for core usage — `httpx` only needed for remote adapters
- **Fully typed** — strict mypy, PEP 561 `py.typed` marker

## Installation

```bash
# Core (local filesystem only)
pip install bc-al-chunker

# With GitHub adapter
pip install bc-al-chunker[github]

# With Azure DevOps adapter
pip install bc-al-chunker[azure]

# Everything
pip install bc-al-chunker[all]
```

## Quick Start

```python
from bc_al_chunker import chunk

# Chunk all .al files in a directory
chunks = chunk("/path/to/al-repo")

# Multiple repositories
chunks = chunk(["/repo1", "/repo2"])

# Each chunk has content + rich metadata
for c in chunks:
    print(c.metadata.object_type, c.metadata.object_name, c.metadata.chunk_type)
    print(c.content[:100])
    print(c.token_estimate)
```

## Configuration

```python
from bc_al_chunker import chunk, ChunkingConfig

chunks = chunk(
    "/path/to/repo",
    config=ChunkingConfig(
        max_chunk_chars=2000,      # Max characters per chunk (default: 1500)
        min_chunk_chars=100,       # Min characters per chunk (default: 100)
        include_context_header=True,  # Prepend object context to sub-chunks
        estimate_tokens=True,      # Include token estimate on each chunk
    ),
)
```

## Remote Sources

```python
from bc_al_chunker import chunk_source
from bc_al_chunker.adapters.github import GitHubAdapter
from bc_al_chunker.adapters.azure_devops import AzureDevOpsAdapter

# GitHub
chunks = chunk_source(
    GitHubAdapter("microsoft/BCApps", token="ghp_...", paths=["src/"])
)

# Azure DevOps
chunks = chunk_source(
    AzureDevOpsAdapter("myorg", "myproject", "myrepo", token="pat...")
)
```

## Export

```python
from bc_al_chunker import chunk, chunks_to_json, chunks_to_jsonl, chunks_to_dicts

chunks = chunk("/path/to/repo")

# JSON array
chunks_to_json(chunks, "output.json")

# JSONL (streaming-friendly)
chunks_to_jsonl(chunks, "output.jsonl")

# Python dicts (for programmatic use)
dicts = chunks_to_dicts(chunks)
```

## Chunking Strategy

The chunker uses a **hierarchical, AST-aware** strategy:

1. **Parse** — Each `.al` file is parsed into an `ALObject` AST with sections, procedures, triggers, and properties identified
2. **Size check** — If the object's source is ≤ `max_chunk_chars`, it becomes one `WholeObject` chunk
3. **Split** — Large objects are split:
   - **Header chunk** — object declaration + top-level properties
   - **Section chunks** — `fields`, `keys`, `layout`, `actions`, `views`, `dataset`, etc.
   - **Procedure/Trigger chunks** — each procedure or trigger as its own chunk
4. **Context injection** — Sub-chunks get a context header prepended:
   ```al
   // Object: codeunit 50100 "Address Management"
   // File: src/Codeunits/AddressManagement.al
   procedure ValidateAddress(var CustAddr: Record "Customer Address")
   begin
       ...
   end;
   ```

This ensures every chunk is self-contained and produces high-quality embeddings for code search.

## Chunk Schema

Each `Chunk` contains:

- `content` — the text to embed
- `token_estimate` — approximate token count (chars / 4)
- `metadata`:
  - `file_path`, `object_type`, `object_id`, `object_name`
  - `chunk_type` — `whole_object`, `header`, `section`, `procedure`, `trigger`
  - `section_name`, `procedure_name`
  - `extends` — for extension objects
  - `source_table` — extracted from page/codeunit properties
  - `attributes` — e.g., `[EventSubscriber(...)]`
  - `line_start`, `line_end`

## Development

```bash
# Clone and install
git clone https://github.com/andrijantasevski/bc-al-chunker.git
cd bc-al-chunker
uv sync --all-extras --group dev

# Run tests
uv run pytest tests/ -v

# Lint + format
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Type check
uv run mypy src/
```

## License

MIT
