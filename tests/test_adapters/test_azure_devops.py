"""Tests for the Azure DevOps adapter (mocked HTTP)."""

from __future__ import annotations

import base64

import pytest

try:
    import respx  # noqa: TC002

    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

pytestmark = pytest.mark.skipif(not HAS_HTTPX, reason="httpx/respx not installed")


@pytest.fixture
def _mock_ado(respx_mock: respx.MockRouter) -> None:  # type: ignore[name-defined]
    items_url = "https://dev.azure.com/myorg/myproject/_apis/git/repositories/myrepo/items"

    list_response = {
        "value": [
            {"path": "/src/Table.al", "gitObjectType": "blob"},
            {"path": "/src/Page.al", "gitObjectType": "blob"},
            {"path": "/README.md", "gitObjectType": "blob"},
            {"path": "/src", "gitObjectType": "tree"},
        ]
    }
    respx_mock.get(items_url).respond(200, json=list_response)


@pytest.mark.usefixtures("_mock_ado")
class TestAzureDevOpsAdapter:
    def test_auth_header(self) -> None:
        from bc_al_chunker.adapters.azure_devops import AzureDevOpsAdapter

        adapter = AzureDevOpsAdapter("myorg", "myproject", "myrepo", token="pat123")
        headers = adapter._headers()
        expected = base64.b64encode(b":pat123").decode()
        assert headers["Authorization"] == f"Basic {expected}"

    def test_items_url(self) -> None:
        from bc_al_chunker.adapters.azure_devops import AzureDevOpsAdapter

        adapter = AzureDevOpsAdapter("myorg", "myproject", "myrepo")
        url = adapter._items_url()
        assert "myorg" in url
        assert "myproject" in url
        assert "myrepo" in url
