from fastapi.testclient import TestClient


def test_root_endpoint_returns_200_and_metadata(client: TestClient):
    """Verify that the root endpoint returns status 200 and valid JSON metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app_name"] == "PipelineSage"
    assert "version" in data
    assert data["docs_url"] == "/docs"
    assert data["health_url"] == "/health"
    assert "description" in data


def test_health_endpoint_returns_healthy_status(client: TestClient):
    """Verify that the health check returns status 200 and healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "PipelineSage"
    assert "environment" in data
    assert "timestamp" in data


def test_not_found_returns_standardized_error(client: TestClient):
    """Verify that a non-existent path triggers the standardized 404 error handler."""
    response = client.get("/api/v1/nonexistent-route")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert "detail" in data
    assert data["error_code"] == "HTTP_404"


def test_docs_and_openapi_endpoints_accessible(client: TestClient):
    """Verify that Swagger UI and OpenAPI schema generation work."""
    docs_resp = client.get("/docs")
    assert docs_resp.status_code == 200

    openapi_resp = client.get("/openapi.json")
    assert openapi_resp.status_code == 200
    schema = openapi_resp.json()
    assert schema["info"]["title"] == "PipelineSage API"
    assert "/health" in schema["paths"]
    assert "/" in schema["paths"]
