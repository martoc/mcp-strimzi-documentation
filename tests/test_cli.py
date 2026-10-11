"""Tests for cli module."""

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_strimzi_documentation.cli import cmd_index, cmd_stats, main
from mcp_strimzi_documentation.database import DocumentDatabase
from mcp_strimzi_documentation.models import Document


class TestCli:
    """Tests for command-line interface."""

    def test_cmd_index_indexes_from_git(self, temp_db_path: Path) -> None:
        """Test that the index command indexes without clearing."""
        args = argparse.Namespace(database=str(temp_db_path), branch="main", rebuild=False)

        with patch("mcp_strimzi_documentation.cli.StrimziDocsIndexer") as mock_indexer:
            mock_indexer.return_value.index_from_git.return_value = 5
            assert cmd_index(args) == 0

        mock_indexer.return_value.index_from_git.assert_called_once_with(branch="main")
        mock_indexer.return_value.rebuild_index.assert_not_called()

    def test_cmd_index_rebuilds(self, temp_db_path: Path) -> None:
        """Test that the rebuild flag clears and rebuilds the index."""
        args = argparse.Namespace(database=str(temp_db_path), branch="main", rebuild=True)

        with patch("mcp_strimzi_documentation.cli.StrimziDocsIndexer") as mock_indexer:
            mock_indexer.return_value.rebuild_index.return_value = 5
            assert cmd_index(args) == 0

        mock_indexer.return_value.rebuild_index.assert_called_once_with(branch="main")

    def test_cmd_stats_reports_count(self, temp_db_path: Path, sample_document: Document) -> None:
        """Test that stats succeeds for an existing database."""
        DocumentDatabase(temp_db_path).upsert_document(sample_document)

        assert cmd_stats(argparse.Namespace(database=str(temp_db_path))) == 0

    def test_cmd_stats_fails_without_database(self, tmp_path: Path) -> None:
        """Test that stats fails when the database does not exist."""
        assert cmd_stats(argparse.Namespace(database=str(tmp_path / "missing.db"))) == 1

    def test_main_dispatches_command(self, temp_db_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that main parses arguments and runs the selected command."""
        monkeypatch.setattr("sys.argv", ["strimzi-docs-index", "--database", str(temp_db_path), "stats"])

        assert main() == 1
