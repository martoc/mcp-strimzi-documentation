"""Tests for models module."""

from mcp_strimzi_documentation.models import BookSection, Document, DocumentMetadata, SearchResult


class TestDocumentMetadata:
    """Tests for DocumentMetadata dataclass."""

    def test_create_with_all_fields(self) -> None:
        """Test creating metadata with all fields."""
        metadata = DocumentMetadata(
            title="Test Title",
            description="Test description",
            date="2024-01-02",
            author="jakub_scholz",
        )
        assert metadata.title == "Test Title"
        assert metadata.description == "Test description"
        assert metadata.date == "2024-01-02"
        assert metadata.author == "jakub_scholz"

    def test_create_with_defaults(self) -> None:
        """Test creating metadata with default values."""
        metadata = DocumentMetadata()
        assert metadata.title is None
        assert metadata.description is None
        assert metadata.date is None
        assert metadata.author is None


class TestDocument:
    """Tests for Document dataclass."""

    def test_create_document(self) -> None:
        """Test creating a document."""
        doc = Document(
            path="quickstarts/kind.md",
            title="Quickstart: Kind",
            description=None,
            section="quickstarts",
            content="Kind runs Kubernetes in Docker.",
            url="https://strimzi.io/quickstarts/",
        )
        assert doc.path == "quickstarts/kind.md"
        assert doc.section == "quickstarts"
        assert doc.date is None


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_create_search_result(self) -> None:
        """Test creating a search result."""
        result = SearchResult(
            path="quickstarts/kind.md",
            title="Quickstart: Kind",
            url="https://strimzi.io/quickstarts/",
            snippet="...deploy <mark>Strimzi</mark>...",
            score=15.5,
            section="quickstarts",
        )
        assert result.score == 15.5
        assert "<mark>" in result.snippet


class TestBookSection:
    """Tests for BookSection dataclass."""

    def test_create_book_section(self) -> None:
        """Test creating a book section."""
        section = BookSection(anchor="kraft", title="KRaft", parent_title=None, content="# KRaft")
        assert section.anchor == "kraft"
        assert section.parent_title is None
