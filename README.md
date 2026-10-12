[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-green.svg)](https://modelcontextprotocol.io/)

# MCP Strimzi Documentation Server

An MCP (Model Context Protocol) server that provides search and retrieval tools for [Strimzi](https://strimzi.io)
documentation. This server enables AI assistants like Claude to search and read Strimzi documentation directly.

## Features

- **Full-text search** using SQLite FTS5 with BM25 ranking and Porter stemming
- **Section filtering** to narrow search results to the operator books, HTTP Bridge book, blog, quickstarts,
  glossary or contributor guide
- **Section-level documents**: the large Asciidoctor books published on strimzi.io are split into individual,
  linkable sections, each converted to markdown
- **Pre-built index** containing ~700 documents from the official
  [strimzi.github.io](https://github.com/strimzi/strimzi.github.io) repository
- **Docker support** for portable deployment across projects
- **STDIO and HTTP transports** for seamless MCP client integration

## Indexed Content

The indexer performs a sparse clone of [strimzi.github.io](https://github.com/strimzi/strimzi.github.io) and indexes
the following paths:

| Path | Section | Content |
|------|---------|---------|
| `docs/operators/latest` | `operators` | Overview, Deploying and Managing, and Configuring (API reference) books for the latest release |
| `docs/bridge/latest` | `bridge` | HTTP Bridge book for the latest release |
| `_posts` | `blog` | Strimzi blog posts |
| `quickstarts` | `quickstarts` | Minikube, Kind and Docker Desktop quickstarts |
| `glossary` | `glossary` | Glossary of Strimzi and Kafka terms |
| `contributing` | `contributing` | Contributing guidelines and the documentation contributor guide |

Only the `latest` documentation is indexed. The `docs` directory also holds every historical release, which would
multiply the size of the index with near-identical content.

## Quick Start

### Using Docker (Recommended)

```bash
# Build the Docker image (includes pre-indexed documentation)
make docker-build

# Test the server
make docker-run
```

### Using uv (Local Development)

```bash
# Initialise the environment
make init

# Build the documentation index
make index

# Run the server
make run
```

## Configuration

### Claude Code / Claude Desktop

Add to your `.mcp.json` or global settings:

```json
{
  "mcpServers": {
    "strimzi-docs": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "martoc/mcp-strimzi-documentation:latest"]
    }
  }
}
```

For a locally built Docker image:

```json
{
  "mcpServers": {
    "strimzi-docs": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "mcp-strimzi-documentation"]
    }
  }
}
```

For local development without Docker:

```json
{
  "mcpServers": {
    "strimzi-docs": {
      "command": "uv",
      "args": ["run", "mcp-strimzi-docs"],
      "cwd": "/path/to/mcp-strimzi-documentation"
    }
  }
}
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `search_documentation` | Search Strimzi documentation by keyword query with optional section filtering |
| `read_documentation` | Retrieve the full content of a specific documentation page or book section |

### search_documentation

Search Strimzi documentation using full-text search with stemming support.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search terms (supports stemming) |
| `section` | string | No | None | Filter by section (see below) |
| `limit` | integer | No | 10 | Maximum results (1-50) |

**Available Sections:** `operators`, `bridge`, `blog`, `quickstarts`, `glossary`, `contributing`

### read_documentation

Retrieve the full content of a documentation page or book section.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | string | Yes | Path to document (from search results) |

Book sections use the book page path plus the section anchor, for example
`docs/operators/latest/deploying.md#cluster-operator-str`. Reading the book path without an anchor returns its table
of contents.

## CLI Commands

```bash
# Build/rebuild the documentation index
uv run strimzi-docs-index index
uv run strimzi-docs-index index --rebuild
uv run strimzi-docs-index index --branch main

# Show index statistics
uv run strimzi-docs-index stats
```

## Development

```bash
make init       # Initialise development environment
make build      # Run full build (lint, typecheck, test)
make test       # Run tests with coverage
make format     # Format code
make lint       # Run linter
make typecheck  # Run type checker
```

## Documentation

- [USAGE.md](USAGE.md) - Detailed usage instructions
- [CODESTYLE.md](CODESTYLE.md) - Code style guidelines
- [CLAUDE.md](CLAUDE.md) - Claude Code instructions

## Licence

This project is licensed under the MIT Licence - see the [LICENSE](LICENSE) file for details.
