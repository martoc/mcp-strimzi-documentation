"""Data models for Strimzi documentation."""

from dataclasses import dataclass


@dataclass
class DocumentMetadata:
    """Metadata extracted from markdown frontmatter."""

    title: str | None = None
    description: str | None = None
    date: str | None = None
    author: str | None = None


@dataclass
class Document:
    """Represents a documentation page or a section of a documentation book."""

    path: str
    title: str
    description: str | None
    section: str
    content: str
    url: str
    date: str | None = None


@dataclass
class SearchResult:
    """Represents a search result."""

    path: str
    title: str
    url: str
    snippet: str
    score: float
    section: str


@dataclass
class BookSection:
    """A section extracted from an Asciidoctor-generated HTML book."""

    anchor: str
    title: str
    parent_title: str | None
    content: str
