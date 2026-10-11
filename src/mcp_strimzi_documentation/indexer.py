"""Indexer for Strimzi documentation from the strimzi.github.io repository."""

import logging
import subprocess
import tempfile
from pathlib import Path

import yaml

from mcp_strimzi_documentation.database import DocumentDatabase
from mcp_strimzi_documentation.parser import DocumentParser

logger = logging.getLogger(__name__)


class StrimziDocsIndexer:
    """Indexes Strimzi documentation from the strimzi.github.io GitHub repository."""

    STRIMZI_SITE_REPO = "https://github.com/strimzi/strimzi.github.io.git"

    # Only the latest documentation books are indexed: the docs directory also
    # holds every historical release, which would multiply the index size with
    # near-identical content
    SOURCE_PATHS = (
        "contributing",
        "_posts",
        "docs/operators/latest",
        "docs/bridge/latest",
        "glossary",
        "quickstarts",
    )

    # Duplicates of books that are already indexed from another source path
    EXCLUDED_PATHS = frozenset({"docs/operators/latest/contributing.md"})

    RELEASES_PATH = "_data/releases.yaml"

    def __init__(self, database: DocumentDatabase) -> None:
        """Initialise indexer with database instance.

        Args:
            database: DocumentDatabase instance for storing documents.
        """
        self.database = database

    def index_from_git(self, branch: str = "main", shallow: bool = True) -> int:
        """Clone the strimzi.github.io repository and index documentation.

        Args:
            branch: Git branch to clone.
            shallow: Whether to do a shallow clone.

        Returns:
            Number of documents indexed.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "strimzi.github.io"
            self._clone_repository(repo_path, branch, shallow)
            return self._index_repository(repo_path)

    def index_from_path(self, repo_path: Path) -> int:
        """Index documentation from a local checkout of strimzi.github.io.

        Args:
            repo_path: Path to the repository root.

        Returns:
            Number of documents indexed.
        """
        return self._index_repository(repo_path)

    def _clone_repository(self, target_path: Path, branch: str, shallow: bool) -> None:
        """Clone the strimzi.github.io repository with a sparse checkout.

        Only the indexed source paths and the release data are checked out, which
        avoids downloading thousands of images from historical releases.

        Args:
            target_path: Directory to clone into.
            branch: Git branch to clone.
            shallow: Whether to do a shallow clone.

        Raises:
            subprocess.CalledProcessError: If a git command fails.
        """
        cmd = ["git", "clone", "--filter=blob:none", "--sparse"]
        if shallow:
            cmd.extend(["--depth", "1"])
        cmd.extend(["--branch", branch, self.STRIMZI_SITE_REPO, str(target_path)])

        logger.info("Cloning strimzi.github.io repository...")
        subprocess.run(cmd, check=True, capture_output=True)  # noqa: S603

        sparse_paths = [*self.SOURCE_PATHS, Path(self.RELEASES_PATH).parent.as_posix()]
        subprocess.run(  # noqa: S603
            ["git", "-C", str(target_path), "sparse-checkout", "set", *sparse_paths],  # noqa: S607
            check=True,
            capture_output=True,
        )
        logger.info("Repository cloned successfully")

    def _load_placeholders(self, repo_path: Path) -> dict[str, str]:
        """Load the latest release versions used by site placeholders.

        Args:
            repo_path: Path to the repository root.

        Returns:
            Mapping of placeholder to version; empty if release data is unavailable.
        """
        releases_file = repo_path / self.RELEASES_PATH
        if not releases_file.exists():
            logger.warning("Release data not found, version placeholders will not be replaced: %s", releases_file)
            return {}

        try:
            releases = yaml.safe_load(releases_file.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            logger.warning("Failed to parse release data %s: %s", releases_file, e)
            return {}

        placeholders: dict[str, str] = {}
        for key, placeholder in (("operator", "!LATEST_OPERATOR_VERSION!"), ("bridge", "!LATEST_BRIDGE_VERSION!")):
            entries = releases.get(key) if isinstance(releases, dict) else None
            if isinstance(entries, list) and entries and isinstance(entries[0], dict) and "version" in entries[0]:
                placeholders[placeholder] = str(entries[0]["version"])
            else:
                logger.warning("No %s release found in %s", key, releases_file)
        return placeholders

    def _index_repository(self, repo_path: Path) -> int:
        """Index all markdown files under the configured source paths.

        Args:
            repo_path: Path to the repository root.

        Returns:
            Number of documents indexed.

        Raises:
            ValueError: If the repository path does not exist.
        """
        if not repo_path.exists():
            msg = f"Repository path does not exist: {repo_path}"
            raise ValueError(msg)

        parser = DocumentParser(self._load_placeholders(repo_path))
        indexed_count = 0
        failed_count = 0

        for source_path in self.SOURCE_PATHS:
            source_dir = repo_path / source_path
            if not source_dir.exists():
                logger.warning("Source path not found, skipping: %s", source_path)
                continue

            md_files = sorted(source_dir.rglob("*.md"))
            logger.info("Found %d markdown files in %s", len(md_files), source_path)

            for file_path in md_files:
                relative_path = file_path.relative_to(repo_path).as_posix()
                if relative_path in self.EXCLUDED_PATHS:
                    logger.debug("Skipping excluded file: %s", relative_path)
                    continue

                try:
                    documents = parser.parse_file(file_path, repo_path)
                except (OSError, ValueError, yaml.YAMLError) as e:
                    logger.warning("Failed to parse %s: %s", relative_path, e)
                    failed_count += 1
                    continue

                if not documents:
                    logger.debug("No indexable content: %s", relative_path)
                for document in documents:
                    self.database.upsert_document(document)
                    indexed_count += 1
                    logger.debug("Indexed: %s", document.path)

        logger.info("Successfully indexed %d documents (%d files failed)", indexed_count, failed_count)
        return indexed_count

    def rebuild_index(self, branch: str = "main") -> int:
        """Clear existing index and rebuild from scratch.

        Args:
            branch: Git branch to index from.

        Returns:
            Number of documents indexed.
        """
        logger.info("Clearing existing index...")
        self.database.clear()
        return self.index_from_git(branch)
