"""Tests for database module."""

from pathlib import Path

from mcp_strimzi_documentation.database import DocumentDatabase
from mcp_strimzi_documentation.models import Document


class TestDocumentDatabase:
    """Tests for DocumentDatabase class."""

    def test_initialise_creates_schema(self, temp_db_path: Path) -> None:
        """Test that initialisation creates the database schema."""
        db = DocumentDatabase(temp_db_path)
        assert temp_db_path.exists()
        assert db.get_document_count() == 0

    def test_upsert_document_insert(self, database: DocumentDatabase, sample_document: Document) -> None:
        """Test inserting a new document."""
        database.upsert_document(sample_document)
        assert database.get_document_count() == 1

        retrieved = database.get_document(sample_document.path)
        assert retrieved is not None
        assert retrieved.title == sample_document.title

    def test_upsert_document_update(self, database: DocumentDatabase, sample_document: Document) -> None:
        """Test updating an existing document."""
        database.upsert_document(sample_document)

        updated_doc = Document(
            path=sample_document.path,
            title="Updated Title",
            description=sample_document.description,
            section=sample_document.section,
            content=sample_document.content,
            url=sample_document.url,
        )
        database.upsert_document(updated_doc)

        assert database.get_document_count() == 1
        retrieved = database.get_document(sample_document.path)
        assert retrieved is not None
        assert retrieved.title == "Updated Title"

    def test_search_returns_results(self, database: DocumentDatabase, sample_documents: list[Document]) -> None:
        """Test that search returns matching results."""
        for doc in sample_documents:
            database.upsert_document(doc)

        results = database.search("quickstart")
        assert len(results) >= 1
        assert any(r.path == "quickstarts/minikube.md" for r in results)

    def test_search_with_section_filter(self, database: DocumentDatabase, sample_documents: list[Document]) -> None:
        """Test search with section filter."""
        for doc in sample_documents:
            database.upsert_document(doc)

        results = database.search("cluster", section="operators")
        assert all(r.section == "operators" for r in results)

    def test_search_returns_empty_for_no_match(self, database: DocumentDatabase, sample_document: Document) -> None:
        """Test search returns empty list when no matches."""
        database.upsert_document(sample_document)
        results = database.search("nonexistent_term_xyz")
        assert len(results) == 0

    def test_get_document_not_found(self, database: DocumentDatabase) -> None:
        """Test get_document returns None for non-existent path."""
        result = database.get_document("nonexistent/path.md")
        assert result is None

    def test_clear_removes_all_documents(self, database: DocumentDatabase, sample_documents: list[Document]) -> None:
        """Test clear removes all documents."""
        for doc in sample_documents:
            database.upsert_document(doc)
        assert database.get_document_count() == len(sample_documents)

        database.clear()
        assert database.get_document_count() == 0

    def test_search_respects_limit(self, database: DocumentDatabase, sample_documents: list[Document]) -> None:
        """Test search respects the limit parameter."""
        for doc in sample_documents:
            database.upsert_document(doc)

        results = database.search("kafka", limit=1)
        assert len(results) <= 1

    def test_search_handles_invalid_fts_syntax(
        self, database: DocumentDatabase, sample_documents: list[Document]
    ) -> None:
        """Test that queries with FTS5 operators fall back to quoted terms."""
        for doc in sample_documents:
            database.upsert_document(doc)

        results = database.search("cluster-operator")
        assert any(r.section == "operators" for r in results)

    def test_search_returns_empty_for_query_without_words(self, database: DocumentDatabase) -> None:
        """Test that a query with no searchable terms returns no results."""
        assert database.search('"(') == []

    def test_upsert_stores_date(self, database: DocumentDatabase, sample_documents: list[Document]) -> None:
        """Test that the publication date is stored and retrieved."""
        database.upsert_document(sample_documents[2])
        retrieved = database.get_document(sample_documents[2].path)
        assert retrieved is not None
        assert retrieved.date == "2023-08-23"
