"""Strimzi Documentation MCP Server.

An MCP server that provides search and retrieval tools for Strimzi documentation.
"""

__version__ = "0.1.0"

from mcp_strimzi_documentation.database import DocumentDatabase
from mcp_strimzi_documentation.indexer import StrimziDocsIndexer

__all__ = [
    "DocumentDatabase",
    "StrimziDocsIndexer",
]
