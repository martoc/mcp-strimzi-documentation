"""Converter for Asciidoctor-generated HTML books published on strimzi.io."""

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
from markdownify import markdownify

from mcp_strimzi_documentation.models import BookSection


class AsciidocHtmlConverter:
    """Splits Asciidoctor HTML books into sections and converts them to markdown.

    Strimzi books (deploying, configuring, overview, etc.) are single HTML files
    of up to a few megabytes. Indexing them whole would make search snippets and
    ranking meaningless, so each book is split into its level 1 and level 2
    sections, which map to individual, linkable topics on strimzi.io.
    """

    SECTION_NUMBER_PATTERN = re.compile(r"^\d+(\.\d+)*\.\s+")
    EXCESS_NEWLINES_PATTERN = re.compile(r"\n{3,}")
    REMOVED_TAGS = ("script", "style", "img", "svg")

    def split_sections(self, html: str, base_url: str | None = None) -> list[BookSection]:
        """Split an Asciidoctor HTML book into markdown sections.

        Args:
            html: Asciidoctor-generated HTML (either a full page or a body fragment).
            base_url: URL the book is published at. When given, relative links and
                in-page anchors are rewritten as absolute URLs so they remain valid
                once a section is read on its own.

        Returns:
            List of BookSection instances in document order. A book without any
            level 1 sections is returned as a single section with an empty anchor.
        """
        soup = BeautifulSoup(html, "html.parser")
        self._remove_noise(soup)
        if base_url:
            self._absolutise_links(soup, base_url)

        sections: list[BookSection] = []

        preamble = soup.find("div", id="preamble")
        if isinstance(preamble, Tag):
            content = self.to_markdown(preamble)
            if content:
                sections.append(BookSection(anchor="preamble", title="Preamble", parent_title=None, content=content))
            preamble.decompose()

        sect1_elements = [el for el in soup.find_all("div", class_="sect1") if isinstance(el, Tag)]
        if not sect1_elements:
            content = self.to_markdown(soup)
            return [BookSection(anchor="", title="", parent_title=None, content=content)] if content else sections

        for sect1 in sect1_elements:
            sections.extend(self._split_sect1(sect1))

        return sections

    def _split_sect1(self, sect1: Tag) -> list[BookSection]:
        """Split a level 1 section into its introduction and level 2 sections.

        Args:
            sect1: The ``div.sect1`` element.

        Returns:
            List of BookSection instances for the level 1 introduction (when it has
            content of its own) followed by each level 2 section.
        """
        anchor, title = self._pop_heading(sect1, "h2")
        sect2_elements = [el for el in sect1.find_all("div", class_="sect2") if isinstance(el, Tag)]

        children: list[BookSection] = []
        for sect2 in sect2_elements:
            child_anchor, child_title = self._pop_heading(sect2, "h3")
            body = self.to_markdown(sect2)
            children.append(
                BookSection(
                    anchor=child_anchor,
                    title=child_title,
                    parent_title=title,
                    content=self._with_heading(child_title, body),
                )
            )
            sect2.decompose()

        sections: list[BookSection] = []
        intro = self.to_markdown(sect1)
        if intro:
            sections.append(
                BookSection(anchor=anchor, title=title, parent_title=None, content=self._with_heading(title, intro))
            )
        sections.extend(children)
        return sections

    @staticmethod
    def _with_heading(title: str, body: str) -> str:
        """Prefix section markdown with a top-level heading.

        Args:
            title: Section title.
            body: Section markdown without its heading.

        Returns:
            Markdown starting with the section title as a level 1 heading.
        """
        return f"# {title}\n\n{body}".strip() if title else body

    def _pop_heading(self, element: Tag, tag_name: str) -> tuple[str, str]:
        """Extract and remove the heading of a section.

        Args:
            element: The section element, modified in place.
            tag_name: Heading tag name for the section level (e.g. ``h2``).

        Returns:
            Tuple of the heading anchor (empty if absent) and the title with any
            leading section number removed.
        """
        heading = element.find(tag_name)
        if not isinstance(heading, Tag):
            return "", ""
        anchor = heading.get("id")
        title = self.SECTION_NUMBER_PATTERN.sub("", heading.get_text(" ", strip=True))
        heading.decompose()
        return (anchor if isinstance(anchor, str) else ""), title

    def _remove_noise(self, soup: BeautifulSoup) -> None:
        """Remove elements that carry no searchable documentation content.

        Args:
            soup: Parsed HTML document, modified in place.
        """
        for element in soup.find_all(self.REMOVED_TAGS):
            element.decompose()
        toc = soup.find("div", id="toc")
        if isinstance(toc, Tag):
            toc.decompose()
        for element in soup.find_all(["div"], id=["header", "footer"]):
            element.decompose()

    @staticmethod
    def _absolutise_links(soup: BeautifulSoup, base_url: str) -> None:
        """Rewrite relative link targets as absolute URLs.

        Args:
            soup: Parsed HTML document, modified in place.
            base_url: URL the document is published at.
        """
        for link in soup.find_all("a", href=True):
            if not isinstance(link, Tag):
                continue
            href = link.get("href")
            if isinstance(href, str) and href:
                link["href"] = urljoin(base_url, href)

    def _convert_admonitions(self, element: Tag) -> None:
        """Rewrite Asciidoctor admonition tables as blockquotes.

        Args:
            element: Element whose admonition blocks are rewritten in place.
        """
        soup = BeautifulSoup("", "html.parser")
        for block in element.find_all("div", class_="admonitionblock"):
            if not isinstance(block, Tag):
                continue
            label_element = block.find("div", class_="title")
            content_element = block.find("td", class_="content")
            label = label_element.get_text(strip=True) if isinstance(label_element, Tag) else "Note"

            quote = soup.new_tag("blockquote")
            strong = soup.new_tag("strong")
            strong.string = f"{label}:"
            paragraph = soup.new_tag("p")
            paragraph.append(strong)
            quote.append(paragraph)
            if isinstance(content_element, Tag):
                for child in list(content_element.children):
                    quote.append(child.extract())
            block.replace_with(quote)

    @staticmethod
    def _code_language(element: Tag) -> str | None:
        """Determine the language of a code listing.

        Args:
            element: The ``pre`` element of a listing block.

        Returns:
            The language declared by Asciidoctor, or None if not declared.
        """
        code = element.find("code")
        language = code.get("data-lang") if isinstance(code, Tag) else None
        return language if isinstance(language, str) else None

    def to_markdown(self, element: Tag) -> str:
        """Convert an HTML element to markdown.

        Args:
            element: The element to convert.

        Returns:
            Markdown text with excess blank lines collapsed.
        """
        self._convert_admonitions(element)
        markdown: str = markdownify(
            str(element),
            heading_style="ATX",
            bullets="*",
            code_language_callback=self._code_language,
        )
        return self.EXCESS_NEWLINES_PATTERN.sub("\n\n", markdown).strip()
