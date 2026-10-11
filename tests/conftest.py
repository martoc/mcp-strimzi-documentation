"""Pytest fixtures for Strimzi documentation MCP server tests."""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from mcp_strimzi_documentation.database import DocumentDatabase
from mcp_strimzi_documentation.models import Document

SAMPLE_BOOK_HTML = """<div id="toc" class="toc">
<div id="toctitle">Table of Contents</div>
<ul class="sectlevel1"><li><a href="#deploy-intro_str">1. Deployment overview</a></li></ul>
</div>
<div class="sect1">
<h2 id="deploy-intro_str">1. Deployment overview</h2>
<div class="sectionbody">
<div class="paragraph"><p>Strimzi simplifies running Apache Kafka on Kubernetes.</p></div>
<div class="sect2">
<h3 id="cluster-operator-str">1.1. Deploying the Cluster Operator</h3>
<div class="paragraph"><p>See <a href="#kafka-cluster-str">Deploying Kafka</a> and
<a href="./configuring.html">the API reference</a>.</p></div>
<div class="imageblock"><div class="content"><img src="images/operators.png" alt="Operators"></div></div>
<div class="admonitionblock note"><table><tr>
<td class="icon"><div class="title">Note</div></td>
<td class="content">Install the Cluster Operator before deploying Kafka.</td>
</tr></table></div>
<div class="listingblock"><div class="content">
<pre class="highlightjs highlight"><code class="language-yaml hljs" data-lang="yaml">kind: Kafka
metadata:
  name: my-cluster</code></pre>
</div></div>
</div>
</div>
</div>
<div class="sect1">
<h2 id="kafka-cluster-str">2. Deploying Kafka</h2>
<div class="sectionbody">
<div class="sect2">
<h3 id="kafka-node-pools-str">2.1. Configuring node pools</h3>
<div class="paragraph"><p>Node pools group Kafka nodes with the same configuration.</p></div>
</div>
</div>
</div>
<script>console.log("ignored");</script>
"""


@pytest.fixture
def temp_db_path() -> Generator[Path, None, None]:
    """Provide a temporary database path."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir) / "test_strimzi_docs.db"


@pytest.fixture
def database(temp_db_path: Path) -> DocumentDatabase:
    """Provide a fresh database instance."""
    return DocumentDatabase(temp_db_path)


@pytest.fixture
def sample_document() -> Document:
    """Provide a sample document for testing."""
    return Document(
        path="quickstarts/minikube.md",
        title="Quickstart: Minikube",
        description=None,
        section="quickstarts",
        content="# Quickstart\n\nStart a Minikube cluster and deploy Strimzi with kubectl.",
        url="https://strimzi.io/quickstarts/",
    )


@pytest.fixture
def sample_documents() -> list[Document]:
    """Provide multiple sample documents for testing."""
    return [
        Document(
            path="quickstarts/minikube.md",
            title="Quickstart: Minikube",
            description=None,
            section="quickstarts",
            content="# Quickstart\n\nStart a Minikube cluster and deploy Strimzi with kubectl.",
            url="https://strimzi.io/quickstarts/",
        ),
        Document(
            path="docs/operators/latest/deploying.md#cluster-operator-str",
            title="Deploying the Cluster Operator",
            description="Deploying and Managing (1.2.0): Deployment overview",
            section="operators",
            content="# Deploying the Cluster Operator\n\nInstall the Cluster Operator to manage Kafka clusters.",
            url="https://strimzi.io/docs/operators/latest/deploying.html#cluster-operator-str",
        ),
        Document(
            path="_posts/2023-08-23-kafka-node-pools.md",
            title="Kafka Node Pools",
            description="Node pools introduce a new way to configure Kafka nodes.",
            section="blog",
            content="Kafka node pools let you deploy brokers with different configurations.",
            url="https://strimzi.io/blog/2023/08/23/kafka-node-pools/",
            date="2023-08-23",
        ),
    ]


@pytest.fixture
def site_repo() -> Generator[Path, None, None]:
    """Provide a minimal strimzi.github.io repository layout."""
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)

        data_dir = root / "_data"
        data_dir.mkdir()
        (data_dir / "releases.yaml").write_text(
            "operator:\n  - version: 1.2.0\n  - version: 1.1.0\nbridge:\n  - version: 1.1.0\n"
        )

        posts_dir = root / "_posts"
        posts_dir.mkdir()
        (posts_dir / "2023-08-23-kafka-node-pools.md").write_text(
            "---\nlayout: post\ntitle: Kafka Node Pools\ndate: 2023-08-23\nauthor: jakub_scholz\n---\n\n"
            "Node pools introduce a new way to configure Kafka nodes.\n\n<!--more-->\n\n"
            "See [Cruise Control]({% post_url 2020-06-05-cruise-control %}).\n"
        )

        operators_dir = root / "docs" / "operators" / "latest"
        operators_dir.mkdir(parents=True)
        (operators_dir / "deploying.md").write_text(
            "---\ntitle: Deploying and Managing (!LATEST_OPERATOR_VERSION!)\nlayout: default\n---\n\n"
            "{% include_relative deploying-book.html %}\n"
        )
        (operators_dir / "deploying-book.html").write_text(SAMPLE_BOOK_HTML)
        (operators_dir / "contributing.md").write_text(
            "---\ntitle: Contributor Guide\n---\n\n{% include_relative contributing-book.html %}\n"
        )
        (operators_dir / "contributing-book.html").write_text(SAMPLE_BOOK_HTML)

        quickstarts_dir = root / "quickstarts"
        quickstarts_dir.mkdir()
        (quickstarts_dir / "index.md").write_text(
            "---\nlayout: quickstarts\ntitle: Quickstarts\npermalink: /quickstarts/\n---\n"
        )
        (quickstarts_dir / "minikube.md").write_text("Minikube provides a local Kubernetes cluster.\n")

        glossary_dir = root / "glossary" / "guide"
        glossary_dir.mkdir(parents=True)
        (glossary_dir / "index.md").write_text(
            "---\ntitle: Glossary\n---\n\n{% include_relative glossary.html %}\n\n<script>var a = 1;</script>"
        )
        (glossary_dir / "glossary.html").write_text(
            '<div class="sect1"><h2 id="kraft">KRaft</h2><div class="sectionbody">'
            "<p>Kafka Raft metadata mode.</p></div></div>"
        )

        yield root
