"""Tests for html_converter module."""

from bs4 import BeautifulSoup

from mcp_strimzi_documentation.html_converter import AsciidocHtmlConverter
from tests.conftest import SAMPLE_BOOK_HTML

BASE_URL = "https://strimzi.io/docs/operators/latest/deploying.html"


class TestAsciidocHtmlConverter:
    """Tests for AsciidocHtmlConverter class."""

    def test_split_sections_returns_level_one_and_two_sections(self) -> None:
        """Test that a book is split into level 1 introductions and level 2 sections."""
        sections = AsciidocHtmlConverter().split_sections(SAMPLE_BOOK_HTML)

        assert [s.anchor for s in sections] == ["deploy-intro_str", "cluster-operator-str", "kafka-node-pools-str"]

    def test_split_sections_strips_section_numbers(self) -> None:
        """Test that section numbers are removed from titles."""
        sections = AsciidocHtmlConverter().split_sections(SAMPLE_BOOK_HTML)

        assert sections[1].title == "Deploying the Cluster Operator"
        assert sections[1].parent_title == "Deployment overview"
        assert sections[1].content.startswith("# Deploying the Cluster Operator")

    def test_split_sections_skips_empty_introductions(self) -> None:
        """Test that a level 1 section with only a heading is not emitted."""
        sections = AsciidocHtmlConverter().split_sections(SAMPLE_BOOK_HTML)

        assert "kafka-cluster-str" not in [s.anchor for s in sections]

    def test_split_sections_removes_noise(self) -> None:
        """Test that the table of contents, scripts and images are removed."""
        content = "\n".join(s.content for s in AsciidocHtmlConverter().split_sections(SAMPLE_BOOK_HTML))

        assert "Table of Contents" not in content
        assert "console.log" not in content
        assert "operators.png" not in content

    def test_split_sections_converts_code_and_admonitions(self) -> None:
        """Test that listings keep their language and admonitions become blockquotes."""
        sections = AsciidocHtmlConverter().split_sections(SAMPLE_BOOK_HTML)
        content = sections[1].content

        assert "```yaml" in content
        assert "name: my-cluster" in content
        assert "> **Note:**" in content
        assert "Install the Cluster Operator before deploying Kafka." in content

    def test_split_sections_absolutises_links(self) -> None:
        """Test that relative links and anchors are rewritten as absolute URLs."""
        sections = AsciidocHtmlConverter().split_sections(SAMPLE_BOOK_HTML, BASE_URL)
        content = sections[1].content

        assert f"({BASE_URL}#kafka-cluster-str)" in content
        assert "(https://strimzi.io/docs/operators/latest/configuring.html)" in content

    def test_split_sections_keeps_relative_links_without_base_url(self) -> None:
        """Test that links are left untouched when no base URL is given."""
        sections = AsciidocHtmlConverter().split_sections(SAMPLE_BOOK_HTML)

        assert "(#kafka-cluster-str)" in sections[1].content

    def test_split_sections_includes_preamble(self) -> None:
        """Test that a book preamble becomes its own section."""
        html = '<div id="preamble"><p>About this book.</p></div>' + SAMPLE_BOOK_HTML
        sections = AsciidocHtmlConverter().split_sections(html)

        assert sections[0].anchor == "preamble"
        assert "About this book." in sections[0].content

    def test_split_sections_without_sections_returns_whole_document(self) -> None:
        """Test that HTML without sections is returned as a single section."""
        sections = AsciidocHtmlConverter().split_sections("<p>Just a paragraph.</p>")

        assert len(sections) == 1
        assert sections[0].anchor == ""
        assert sections[0].content == "Just a paragraph."

    def test_split_sections_of_empty_html_returns_nothing(self) -> None:
        """Test that empty HTML yields no sections."""
        assert AsciidocHtmlConverter().split_sections("<div></div>") == []

    def test_to_markdown_collapses_blank_lines(self) -> None:
        """Test that excess blank lines are collapsed."""
        soup = BeautifulSoup("<div><p>One</p><br><br><br><p>Two</p></div>", "html.parser")

        markdown = AsciidocHtmlConverter().to_markdown(soup)

        assert "\n\n\n" not in markdown
