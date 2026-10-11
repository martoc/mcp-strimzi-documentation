"""Tests for parser module."""

from datetime import date, datetime
from pathlib import Path

from mcp_strimzi_documentation.parser import DocumentParser

PLACEHOLDERS = {"!LATEST_OPERATOR_VERSION!": "1.2.0", "!LATEST_BRIDGE_VERSION!": "1.1.0"}


class TestDocumentParser:
    """Tests for DocumentParser class."""

    def test_parse_blog_post(self, site_repo: Path) -> None:
        """Test parsing a blog post with frontmatter and an excerpt."""
        parser = DocumentParser(PLACEHOLDERS)
        documents = parser.parse_file(site_repo / "_posts" / "2023-08-23-kafka-node-pools.md", site_repo)

        assert len(documents) == 1
        document = documents[0]
        assert document.path == "_posts/2023-08-23-kafka-node-pools.md"
        assert document.title == "Kafka Node Pools"
        assert document.section == "blog"
        assert document.date == "2023-08-23"
        assert document.url == "https://strimzi.io/blog/2023/08/23/kafka-node-pools/"
        assert document.description == "Node pools introduce a new way to configure Kafka nodes."
        assert "https://strimzi.io/blog/2020/06/05/cruise-control/" in document.content
        assert "<!--more-->" not in document.content
        assert "{%" not in document.content

    def test_parse_book_splits_sections(self, site_repo: Path) -> None:
        """Test that a page including an HTML book is split into sections."""
        parser = DocumentParser(PLACEHOLDERS)
        documents = parser.parse_file(site_repo / "docs" / "operators" / "latest" / "deploying.md", site_repo)

        paths = [d.path for d in documents]
        assert paths == [
            "docs/operators/latest/deploying.md",
            "docs/operators/latest/deploying.md#deploy-intro_str",
            "docs/operators/latest/deploying.md#cluster-operator-str",
            "docs/operators/latest/deploying.md#kafka-node-pools-str",
        ]
        assert all(d.section == "operators" for d in documents)

    def test_parse_book_section_metadata(self, site_repo: Path) -> None:
        """Test titles, descriptions and URLs of book sections."""
        parser = DocumentParser(PLACEHOLDERS)
        documents = parser.parse_file(site_repo / "docs" / "operators" / "latest" / "deploying.md", site_repo)
        section = documents[2]

        assert section.title == "Deploying the Cluster Operator"
        assert section.description == "Deploying and Managing (1.2.0): Deployment overview"
        assert section.url == "https://strimzi.io/docs/operators/latest/deploying.html#cluster-operator-str"

    def test_parse_book_contents_document(self, site_repo: Path) -> None:
        """Test that the book page itself lists its sections."""
        parser = DocumentParser(PLACEHOLDERS)
        documents = parser.parse_file(site_repo / "docs" / "operators" / "latest" / "deploying.md", site_repo)
        contents = documents[0]

        assert contents.title == "Deploying and Managing (1.2.0)"
        assert contents.url == "https://strimzi.io/docs/operators/latest/deploying.html"
        assert "`docs/operators/latest/deploying.md#cluster-operator-str`" in contents.content

    def test_parse_book_without_placeholders(self, site_repo: Path) -> None:
        """Test that unknown placeholders are left as they are."""
        documents = DocumentParser().parse_file(site_repo / "docs" / "operators" / "latest" / "deploying.md", site_repo)

        assert documents[0].title == "Deploying and Managing (!LATEST_OPERATOR_VERSION!)"

    def test_parse_glossary_index(self, site_repo: Path) -> None:
        """Test that an index page including a book uses its directory URL."""
        documents = DocumentParser().parse_file(site_repo / "glossary" / "guide" / "index.md", site_repo)

        section = documents[1]
        assert section.section == "glossary"
        assert section.url == "https://strimzi.io/glossary/guide/#kraft"
        assert section.title == "KRaft"

    def test_parse_quickstart_without_frontmatter(self, site_repo: Path) -> None:
        """Test that quickstarts get a derived title and the quickstarts URL."""
        documents = DocumentParser().parse_file(site_repo / "quickstarts" / "minikube.md", site_repo)

        assert len(documents) == 1
        assert documents[0].title == "Quickstart: Minikube"
        assert documents[0].url == "https://strimzi.io/quickstarts/"

    def test_parse_page_without_content_returns_nothing(self, site_repo: Path) -> None:
        """Test that a layout-only page produces no documents."""
        documents = DocumentParser().parse_file(site_repo / "quickstarts" / "index.md", site_repo)

        assert documents == []

    def test_parse_page_title_from_heading(self, tmp_path: Path) -> None:
        """Test that the first level 1 heading is used when there is no title."""
        file_path = tmp_path / "contributing" / "index.md"
        file_path.parent.mkdir()
        file_path.write_text("---\nlayout: default\n---\n\n# Contributing\n\nYou can contribute by...")

        documents = DocumentParser().parse_file(file_path, tmp_path)

        assert documents[0].title == "Contributing"
        assert documents[0].section == "contributing"
        assert documents[0].url == "https://strimzi.io/contributing/"

    def test_parse_page_title_from_filename(self, tmp_path: Path) -> None:
        """Test that the filename is used when there is no title or heading."""
        file_path = tmp_path / "contributing" / "how-to_help.md"
        file_path.parent.mkdir()
        file_path.write_text("Some text without a heading.")

        documents = DocumentParser().parse_file(file_path, tmp_path)

        assert documents[0].title == "How To Help"
        assert documents[0].url == "https://strimzi.io/contributing/how-to_help.html"

    def test_clean_content_keeps_raw_blocks(self) -> None:
        """Test that raw blocks keep literal Liquid syntax."""
        content = "{% raw %}{{ .Values.image }} {% if x %}{% endraw %}\n{% include note.html %}Text"

        cleaned = DocumentParser()._clean_content(content)

        assert cleaned == "{{ .Values.image }} {% if x %}\nText"

    def test_clean_content_removes_scripts(self) -> None:
        """Test that inline scripts are removed."""
        cleaned = DocumentParser()._clean_content("Text<script>\nvar a = 1;\n</script>")

        assert cleaned == "Text"

    def test_extract_metadata_dates(self) -> None:
        """Test that dates are normalised to ISO format."""
        parser = DocumentParser()

        assert parser._extract_metadata({"date": date(2024, 1, 2)}).date == "2024-01-02"
        assert parser._extract_metadata({"date": datetime(2024, 1, 2, 10, 0)}).date == "2024-01-02"
        assert parser._extract_metadata({"date": "2024-01-02 10:00:00 +0000"}).date == "2024-01-02"
        assert parser._extract_metadata({"date": 20240102}).date is None

    def test_extract_metadata_ignores_invalid_types(self) -> None:
        """Test that non-string metadata values are ignored."""
        metadata = DocumentParser()._extract_metadata({"title": 1, "description": [], "author": {}})

        assert metadata.title is None
        assert metadata.description is None
        assert metadata.author is None

    def test_extract_section(self) -> None:
        """Test section names for each source path."""
        parser = DocumentParser()

        assert parser._extract_section(Path("index.md")) == "root"
        assert parser._extract_section(Path("_posts/2020-01-01-post.md")) == "blog"
        assert parser._extract_section(Path("docs/bridge/latest/index.md")) == "bridge"
        assert parser._extract_section(Path("glossary/guide/index.md")) == "glossary"

    def test_compute_url_for_root_index(self) -> None:
        """Test the URL of the site root index page."""
        assert DocumentParser()._compute_url(Path("index.md")) == "https://strimzi.io/"

    def test_compute_url_for_post_without_date(self) -> None:
        """Test that a post without a date prefix falls back to the file URL."""
        assert DocumentParser()._compute_url(Path("_posts/draft.md")) == "https://strimzi.io/_posts/draft.html"

    def test_post_date_without_date_prefix(self) -> None:
        """Test that a post filename without a date yields no date."""
        assert DocumentParser()._post_date(Path("_posts/draft.md")) is None

    def test_excerpt_uses_first_paragraph_and_truncates(self) -> None:
        """Test excerpt fallback to the first paragraph and truncation."""
        parser = DocumentParser()
        long_text = " ".join(["word"] * 100)

        excerpt = parser._excerpt(f"{long_text}\n\nSecond paragraph.")

        assert excerpt is not None
        assert excerpt.endswith("...")
        assert len(excerpt) <= DocumentParser.DESCRIPTION_MAX_LENGTH + 3
        assert parser._excerpt("{% include x.html %}") is None
