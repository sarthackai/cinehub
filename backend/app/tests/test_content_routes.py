"""
Tests for content browsing, search, and details endpoints.
"""

import pytest


@pytest.mark.integration
class TestBrowseEndpoint:
    def test_browse_movies_returns_200(self, client):
        response = client.get("/api/content/browse", params={"content_type": "movie"})
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_browse_invalid_content_type_returns_422(self, client):
        response = client.get("/api/content/browse", params={"content_type": "invalid"})
        assert response.status_code == 422

    def test_browse_respects_limit(self, client):
        response = client.get(
            "/api/content/browse", params={"content_type": "movie", "limit": 3}
        )
        assert response.status_code == 200
        assert len(response.json()["results"]) <= 3


@pytest.mark.integration
class TestContentDetails:
    def test_details_for_nonexistent_id_returns_404(self, client):
        response = client.get("/api/content/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    def test_details_for_real_content_includes_expected_fields(self, client):
        # Get a real content_id from browse first
        browse_response = client.get("/api/content/browse", params={"content_type": "movie", "limit": 1})
        results = browse_response.json()["results"]
        if not results:
            pytest.skip("No content in database to test against")

        content_id = results[0]["content_id"]
        response = client.get(f"/api/content/{content_id}")
        assert response.status_code == 200
        data = response.json()
        assert "genres" in data
        assert "cast" in data
        assert "crew" in data


@pytest.mark.integration
class TestKeywordSearch:
    def test_search_without_auth_returns_401(self, client):
        response = client.get("/api/content/search/keyword", params={"q": "test"})
        assert response.status_code == 401

    def test_search_with_empty_query_returns_empty_results(self, client, admin_token):
        response = client.get(
            "/api/content/search/keyword",
            params={"q": ""},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["count"] == 0