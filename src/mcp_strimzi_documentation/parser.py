"""Parser for the Jekyll sources of the strimzi.io website."""

import logging
import re
from datetime import date, datetime
from pathlib import Path
from typing import ClassVar

import frontmatter

from mcp_strimzi_documentation.html_converter import AsciidocHtmlConverter
from mcp_strimzi_documentation.models import Document, DocumentMetadata

logger = logging.getLogger(__name__)


class DocumentParser:
    """Parses Jekyll markdown pages, blog posts and the HTML books they include."""

    STRIMZI_BASE_URL = "https://strimzi.io"
    POSTS_DIRECTORY = "_posts"
    DOCS_DIRECTORY = "docs"
    QUICKSTARTS_DIRECTORY = "quickstarts"
    DESCRIPTION_MAX_LENGTH = 300
    EXCERPT_SEPARATOR = "<!--more-->"
    QUICKSTART_TITLES: ClassVar[dict[str, str]] = {
        "dockerdesktop": "Docker Desktop",
        "kind": "Kind",
        "minikube": "Minikube",
    }

    INCLUDE_RELATIVE_PATTERN = re.compile(r"{%-?\s*include_relative\s+(\S+?)\s*-?%}")
    POST_URL_PATTERN = re.compile(r"{%-?\s*post_url\s+(\S+?)\s*-?%}")
    RAW_BLOCK_PATTERN = re.compile(r"{%-?\s*raw\s*-?%}(.*?){%-?\s*endraw\s*-?%}", flags=re.DOTALL)
    LIQUID_TAG_PATTERN = re.compile(r"{%.*?%}", flags=re.DOTALL)
    SCRIPT_PATTERN = re.compile(r"<script\b.*?</script>", flags=re.DOTALL | re.IGNORECASE)
    HEADING_PATTERN = re.compile(r"^#\s+(.+?)\s*#*\s*$", flags=re.MULTILINE)
    POST_FILENAME_PATTERN = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-(.+)$")
    WHITESPACE_PATTERN = re.compile(r"\s+")
    EXCESS_NEWLINES_PATTERN = re.compile(r"\n{3,}")

    def __init__(self, placeholders: dict[str, str] | None = None) -> None:
        """Initialise the parser.

        Args:
            placeholders: Mapping of site placeholders (e.g. ``!LATEST_OPERATOR_VERSION!``)
                to the values that replace them in titles and content.
        """
        self.placeholders = placeholders or {}
        self.converter = AsciidocHtmlConverter()

    def parse_file(self, file_path: Path, base_path: Path) -> list[Document]:
        """Parse a markdown file into one or more documents.

        Pages that include an Asciidoctor HTML book via ``include_relative`` are
        split into one document per book section, plus a contents document for
        the book itself.

        Args:
            file_path: Path to the markdown file.
            base_path: Root of the strimzi.github.io repository.

        Returns:
            List of documents; empty when the page has no indexable content.

        Raises:
            OSError: If the file or an included HTML book cannot be read.
            ValueError: If the frontmatter cannot be parsed.
        """
        post = frontmatter.load(file_path)
        relative_path = file_path.relative_to(base_path)
        metadata = self._extract_metadata(post.metadata)

        includes = [name for name in self.INCLUDE_RELATIVE_PATTERN.findall(post.content) if name.endswith(".html")]
        if includes:
            return self._parse_book(file_path, relative_path, metadata, includes)

        return self._parse_page(relative_path, metadata, post.content)

    def _parse_page(self, relative_path: Path, metadata: DocumentMetadata, raw_content: str) -> list[Document]:
        """Parse a plain markdown page or blog post.

        Args:
            relative_path: Path relative to the repository root.
            metadata: Frontmatter metadata.
            raw_content: Markdown content without frontmatter.

        Returns:
            A single-element list, or an empty list if the page has no content.
        """
        content = self._clean_content(raw_content)
        if not content:
            return []

        section = self._extract_section(relative_path)
        date_value = metadata.date
        if section == "blog" and date_value is None:
            date_value = self._post_date(relative_path)

        description = metadata.description
        if description is None and section == "blog":
            description = self._excerpt(raw_content)

        return [
            Document(
                path=relative_path.as_posix(),
                title=self._resolve_title(relative_path, metadata, content),
                description=description,
                section=section,
                content=content,
                url=self._compute_url(relative_path),
                date=date_value,
            )
        ]

    def _parse_book(
        self,
        file_path: Path,
        relative_path: Path,
        metadata: DocumentMetadata,
        includes: list[str],
    ) -> list[Document]:
        """Parse a page that wraps one or more Asciidoctor HTML books.

        Args:
            file_path: Absolute path to the markdown page.
            relative_path: Path relative to the repository root.
            metadata: Frontmatter metadata of the page.
            includes: HTML files included by the page, relative to it.

        Returns:
            A contents document for the book followed by one document per section.
        """
        section = self._extract_section(relative_path)
        base_url = self._compute_url(relative_path)
        book_title = self._resolve_title(relative_path, metadata, "")
        page_path = relative_path.as_posix()

        documents: list[Document] = []
        for include in includes:
            html = (file_path.parent / include).read_text(encoding="utf-8")
            for book_section in self.converter.split_sections(html, base_url):
                anchor = book_section.anchor
                title = book_section.title or book_title
                description = book_title
                if book_section.parent_title:
                    description = f"{book_title}: {book_section.parent_title}"
                documents.append(
                    Document(
                        path=f"{page_path}#{anchor}" if anchor else page_path,
                        title=self._substitute_placeholders(title),
                        description=self._substitute_placeholders(description),
                        section=section,
                        content=self._substitute_placeholders(book_section.content),
                        url=f"{base_url}#{anchor}" if anchor else base_url,
                    )
                )

        if documents and all(doc.path != page_path for doc in documents):
            documents.insert(0, self._book_contents(page_path, book_title, section, base_url, documents))
        return documents

    @staticmethod
    def _book_contents(
        page_path: str,
        book_title: str,
        section: str,
        url: str,
        documents: list[Document],
    ) -> Document:
        """Build a contents document listing every section of a book.

        Args:
            page_path: Path of the book page relative to the repository root.
            book_title: Title of the book.
            section: Section the book belongs to.
            url: URL of the book on strimzi.io.
            documents: Section documents of the book.

        Returns:
            Document whose content lists the title and path of each section.
        """
        lines = [f"# {book_title}", "", "## Contents", ""]
        lines.extend(f"* {doc.title} (`{doc.path}`)" for doc in documents)
        return Document(
            path=page_path,
            title=book_title,
            description=f"Table of contents for {book_title}",
            section=section,
            content="\n".join(lines),
            url=url,
        )

    def _extract_metadata(self, metadata: dict[str, object]) -> DocumentMetadata:
        """Extract structured metadata from frontmatter.

        Args:
            metadata: Dictionary of frontmatter fields.

        Returns:
            DocumentMetadata instance.
        """
        title = metadata.get("title")
        description = metadata.get("description")
        author = metadata.get("author")
        date_value = metadata.get("date")

        date_text: str | None = None
        if isinstance(date_value, datetime):
            date_text = date_value.date().isoformat()
        elif isinstance(date_value, date):
            date_text = date_value.isoformat()
        elif isinstance(date_value, str):
            date_text = date_value.strip()[:10]

        return DocumentMetadata(
            title=self._substitute_placeholders(title.strip()) if isinstance(title, str) else None,
            description=description.strip() if isinstance(description, str) else None,
            date=date_text,
            author=author if isinstance(author, str) else None,
        )

    def _extract_section(self, relative_path: Path) -> str:
        """Determine the section a file belongs to.

        Blog posts map to ``blog`` and documentation books map to their product
        (``operators`` or ``bridge``); everything else uses its top-level directory.

        Args:
            relative_path: Path relative to the repository root.

        Returns:
            Section name.
        """
        parts = relative_path.parts
        if len(parts) == 1:
            return "root"
        if parts[0] == self.POSTS_DIRECTORY:
            return "blog"
        if parts[0] == self.DOCS_DIRECTORY and len(parts) > 2:
            return parts[1]
        return parts[0]

    def _compute_url(self, relative_path: Path) -> str:
        """Compute the strimzi.io URL of a page.

        Args:
            relative_path: Path relative to the repository root.

        Returns:
            Full URL to the page.
        """
        parts = relative_path.parts
        if parts[0] == self.POSTS_DIRECTORY:
            match = self.POST_FILENAME_PATTERN.match(relative_path.stem)
            if match:
                year, month, day, slug = match.groups()
                return f"{self.STRIMZI_BASE_URL}/blog/{year}/{month}/{day}/{slug}/"
        if parts[0] == self.QUICKSTARTS_DIRECTORY:
            # Individual quickstarts are rendered as tabs on a single page
            return f"{self.STRIMZI_BASE_URL}/quickstarts/"
        if relative_path.name == "index.md":
            parent = relative_path.parent.as_posix()
            return f"{self.STRIMZI_BASE_URL}/" if parent == "." else f"{self.STRIMZI_BASE_URL}/{parent}/"
        return f"{self.STRIMZI_BASE_URL}/{relative_path.with_suffix('.html').as_posix()}"

    def _post_url(self, post_name: str) -> str:
        """Compute the URL of a blog post referenced via ``post_url``.

        Args:
            post_name: Post filename without extension.

        Returns:
            Full URL to the blog post.
        """
        return self._compute_url(Path(self.POSTS_DIRECTORY) / f"{post_name}.md")

    def _post_date(self, relative_path: Path) -> str | None:
        """Extract the publication date from a blog post filename.

        Args:
            relative_path: Path relative to the repository root.

        Returns:
            ISO date string, or None if the filename has no date prefix.
        """
        match = self.POST_FILENAME_PATTERN.match(relative_path.stem)
        if not match:
            return None
        year, month, day, _ = match.groups()
        return f"{year}-{month}-{day}"

    def _resolve_title(self, relative_path: Path, metadata: DocumentMetadata, content: str) -> str:
        """Determine the title of a page.

        Args:
            relative_path: Path relative to the repository root.
            metadata: Frontmatter metadata.
            content: Cleaned markdown content.

        Returns:
            The frontmatter title, a quickstart title, the first level 1 heading or
            a title derived from the filename, in that order of preference.
        """
        if metadata.title:
            return metadata.title
        if relative_path.parts[0] == self.QUICKSTARTS_DIRECTORY:
            name = self.QUICKSTART_TITLES.get(relative_path.stem, relative_path.stem.replace("-", " ").title())
            return f"Quickstart: {name}"
        heading = self.HEADING_PATTERN.search(content)
        if heading:
            return heading.group(1)
        stem = relative_path.parent.name if relative_path.stem == "index" else relative_path.stem
        return stem.replace("-", " ").replace("_", " ").strip().title() or "Untitled"

    def _excerpt(self, raw_content: str) -> str | None:
        """Build a description from the excerpt of a blog post.

        Args:
            raw_content: Markdown content without frontmatter.

        Returns:
            The text before the excerpt separator (or the first paragraph),
            whitespace-collapsed and truncated, or None if empty.
        """
        if self.EXCERPT_SEPARATOR in raw_content:
            excerpt = raw_content.split(self.EXCERPT_SEPARATOR, 1)[0]
        else:
            excerpt = raw_content.strip().split("\n\n", 1)[0]
        excerpt = self.WHITESPACE_PATTERN.sub(" ", self._clean_content(excerpt)).strip()
        if not excerpt:
            return None
        if len(excerpt) > self.DESCRIPTION_MAX_LENGTH:
            excerpt = excerpt[: self.DESCRIPTION_MAX_LENGTH].rsplit(" ", 1)[0] + "..."
        return excerpt

    def _substitute_placeholders(self, text: str) -> str:
        """Replace site placeholders such as ``!LATEST_OPERATOR_VERSION!``.

        Args:
            text: Text that may contain placeholders.

        Returns:
            Text with known placeholders replaced.
        """
        for placeholder, value in self.placeholders.items():
            text = text.replace(placeholder, value)
        return text

    def _clean_content(self, content: str) -> str:
        """Clean markdown content for indexing.

        Resolves ``post_url`` links, strips Liquid tags (keeping the bodies of
        ``raw`` blocks verbatim), inline scripts and the excerpt separator, and
        substitutes site placeholders.

        Args:
            content: Raw markdown content.

        Returns:
            Cleaned content suitable for indexing.
        """
        content = self.POST_URL_PATTERN.sub(lambda match: self._post_url(match.group(1)), content)
        # Odd-numbered fragments are the bodies of raw blocks, which are kept verbatim
        fragments = self.RAW_BLOCK_PATTERN.split(content)
        content = "".join(
            fragment if index % 2 else self.LIQUID_TAG_PATTERN.sub("", fragment)
            for index, fragment in enumerate(fragments)
        )
        content = self.SCRIPT_PATTERN.sub("", content)
        content = content.replace(self.EXCERPT_SEPARATOR, "")
        content = self._substitute_placeholders(content)
        return self.EXCESS_NEWLINES_PATTERN.sub("\n\n", content).strip()
