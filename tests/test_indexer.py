"""Tests for indexer module."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_strimzi_documentation.database import DocumentDatabase
from mcp_strimzi_documentation.indexer import StrimziDocsIndexer


class TestStrimziDocsIndexer:
    """Tests for StrimziDocsIndexer class."""

    def test_index_from_path_indexes_source_paths(self, database: DocumentDatabase, site_repo: Path) -> None:
        """Test indexing the configured source paths of a local repository."""
        count = StrimziDocsIndexer(database).index_from_path(site_repo)

        # 1 post + 4 deploying book documents + 1 quickstart + 2 glossary documents
        assert count == 8
        assert database.get_document_count() == 8

    def test_index_from_path_skips_excluded_paths(self, database: DocumentDatabase, site_repo: Path) -> None:
        """Test that duplicate books are not indexed."""
        StrimziDocsIndexer(database).index_from_path(site_repo)

        assert database.get_document("docs/operators/latest/contributing.md") is None

    def test_index_from_path_replaces_version_placeholders(self, database: DocumentDatabase, site_repo: Path) -> None:
        """Test that placeholders are replaced with the latest release versions."""
        StrimziDocsIndexer(database).index_from_path(site_repo)

        document = database.get_document("docs/operators/latest/deploying.md")
        assert document is not None
        assert document.title == "Deploying and Managing (1.2.0)"

    def test_index_from_path_without_release_data(self, database: DocumentDatabase, site_repo: Path) -> None:
        """Test that indexing still works when release data is missing."""
        (site_repo / "_data" / "releases.yaml").unlink()

        count = StrimziDocsIndexer(database).index_from_path(site_repo)

        assert count == 8
        document = database.get_document("docs/operators/latest/deploying.md")
        assert document is not None
        assert "!LATEST_OPERATOR_VERSION!" in document.title

    def test_index_from_path_with_invalid_release_data(self, database: DocumentDatabase, site_repo: Path) -> None:
        """Test that unparseable or incomplete release data is tolerated."""
        indexer = StrimziDocsIndexer(database)
        releases = site_repo / "_data" / "releases.yaml"

        releases.write_text("operator: [unclosed")
        assert indexer._load_placeholders(site_repo) == {}

        releases.write_text("operator:\n  - version: 1.2.0\n")
        assert indexer._load_placeholders(site_repo) == {"!LATEST_OPERATOR_VERSION!": "1.2.0"}

    def test_index_from_path_continues_after_parse_failure(self, database: DocumentDatabase, site_repo: Path) -> None:
        """Test that a file that fails to parse is skipped."""
        (site_repo / "quickstarts" / "broken.md").write_text("---\ntitle: [unclosed\n---\nBody")
        (site_repo / "glossary" / "guide" / "glossary.html").unlink()

        count = StrimziDocsIndexer(database).index_from_path(site_repo)

        # The broken quickstart and the glossary with a missing include are skipped
        assert count == 6

    def test_index_from_path_skips_missing_source_paths(self, database: DocumentDatabase, tmp_path: Path) -> None:
        """Test that missing source directories are skipped."""
        assert StrimziDocsIndexer(database).index_from_path(tmp_path) == 0

    def test_index_from_path_raises_on_missing_path(self, database: DocumentDatabase) -> None:
        """Test that indexing raises error for missing path."""
        with pytest.raises(ValueError, match="does not exist"):
            StrimziDocsIndexer(database).index_from_path(Path("/nonexistent/path"))

    def test_clone_repository_uses_sparse_checkout(self, database: DocumentDatabase, tmp_path: Path) -> None:
        """Test that cloning only checks out the indexed paths."""
        indexer = StrimziDocsIndexer(database)

        with patch("mcp_strimzi_documentation.indexer.subprocess.run") as mock_run:
            indexer._clone_repository(tmp_path / "repo", "main", shallow=True)

        clone_cmd = mock_run.call_args_list[0].args[0]
        sparse_cmd = mock_run.call_args_list[1].args[0]
        assert clone_cmd[:4] == ["git", "clone", "--filter=blob:none", "--sparse"]
        assert "--depth" in clone_cmd
        assert sparse_cmd[3:5] == ["sparse-checkout", "set"]
        assert set(sparse_cmd[5:]) == {*StrimziDocsIndexer.SOURCE_PATHS, "_data"}

    def test_clone_repository_without_shallow(self, database: DocumentDatabase, tmp_path: Path) -> None:
        """Test that a full clone omits the depth option."""
        with patch("mcp_strimzi_documentation.indexer.subprocess.run") as mock_run:
            StrimziDocsIndexer(database)._clone_repository(tmp_path / "repo", "main", shallow=False)

        assert "--depth" not in mock_run.call_args_list[0].args[0]

    def test_clone_repository_propagates_git_errors(self, database: DocumentDatabase, tmp_path: Path) -> None:
        """Test that git failures are not swallowed."""
        error = subprocess.CalledProcessError(128, ["git", "clone"])
        with (
            patch("mcp_strimzi_documentation.indexer.subprocess.run", side_effect=error),
            pytest.raises(subprocess.CalledProcessError),
        ):
            StrimziDocsIndexer(database)._clone_repository(tmp_path / "repo", "main", shallow=True)

    def test_index_from_git_indexes_cloned_repository(self, database: DocumentDatabase, site_repo: Path) -> None:
        """Test that index_from_git indexes the cloned repository."""
        indexer = StrimziDocsIndexer(database)
        mock_index = MagicMock(return_value=3)

        with (
            patch.object(indexer, "_clone_repository") as mock_clone,
            patch.object(indexer, "_index_repository", mock_index),
        ):
            count = indexer.index_from_git(branch="main")

        assert count == 3
        mock_clone.assert_called_once()
        assert mock_index.call_args.args[0].name == "strimzi.github.io"

    def test_rebuild_index_clears_existing_data(self, database: DocumentDatabase, site_repo: Path) -> None:
        """Test that rebuild clears existing data before indexing."""
        indexer = StrimziDocsIndexer(database)
        indexer.index_from_path(site_repo)
        assert database.get_document_count() > 0

        with patch.object(indexer, "index_from_git", return_value=0) as mock_index:
            indexer.rebuild_index(branch="main")

        mock_index.assert_called_once_with("main")
        assert database.get_document_count() == 0
