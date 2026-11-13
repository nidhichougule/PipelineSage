import pytest
import httpx
from fastapi.testclient import TestClient

from app.analyzers.log_parser import LogParser
from app.main import app
from app.routes.github import get_github_service
from app.routes.log_parser import get_log_parser
from app.services.github_service import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubLogExpiredError,
    GitHubService,
)


@pytest.fixture
def parser():
    return LogParser()


# --- Unit Tests: LogParser Core Logic ---


def test_parse_dependency_failure_log(parser: LogParser):
    raw_log = """
2026-11-13T23:05:00.1234567Z ##[group]Run python -m pytest tests/
2026-11-13T23:05:01.0000000Z collecting ...
2026-11-13T23:05:01.1000000Z \x1b[31mtests/scenarios/test_dependency_failure.py:7: in test_dependency_scenario\x1b[0m
2026-11-13T23:05:01.1000100Z     load_external_yaml()
2026-11-13T23:05:01.1000200Z \x1b[31msrc/calculator.py:26: in load_external_yaml\x1b[0m
2026-11-13T23:05:01.1000300Z     import terraform_validator
2026-11-13T23:05:01.1000400Z \x1b[31mE   ModuleNotFoundError: No module named 'terraform_validator'\x1b[0m
2026-11-13T23:05:01.2000000Z \x1b[31mFAILED tests/scenarios/test_dependency_failure.py::test_dependency_scenario\x1b[0m
2026-11-13T23:05:02.0000000Z ##[error]Process completed with exit code 1.
"""
    result = parser.parse(raw_log)
    assert result.has_error is True
    assert result.error_type == "ModuleNotFoundError"
    assert "terraform_validator" in result.error_message
    assert result.normalized_signature == "ModuleNotFoundError: No module named 'terraform_validator'"
    assert result.failed_test == "tests/scenarios/test_dependency_failure.py::test_dependency_scenario"
    assert result.file_reference == "src/calculator.py"
    assert result.line_number == 26
    assert len(result.context_lines) > 0


def test_parse_assertion_failure_log(parser: LogParser):
    raw_log = """
2026-11-13T23:05:00.1234567Z ##[group]Run python -m pytest tests/
2026-11-13T23:05:01.0000000Z tests/scenarios/test_assertion_failure.py:8: in test_assertion_scenario
2026-11-13T23:05:01.0000100Z E   AssertionError: Calculation regression: expected 5, got 4
2026-11-13T23:05:01.0000200Z E   assert 4 == 5
2026-11-13T23:05:01.1000000Z FAILED tests/scenarios/test_assertion_failure.py::test_assertion_scenario - AssertionError: Calculation regression: expected 5, got 4
2026-11-13T23:05:02.0000000Z ##[error]Process completed with exit code 1.
"""
    result = parser.parse(raw_log)
    assert result.has_error is True
    assert result.error_type == "AssertionError"
    assert result.failed_test == "tests/scenarios/test_assertion_failure.py::test_assertion_scenario"
    assert "Calculation regression" in result.error_message
    assert "AssertionError:" in result.normalized_signature


def test_parse_parameterized_pytest_test(parser: LogParser):
    raw_log = """
tests/test_math.py:15: in test_division
E   ZeroDivisionError: division by zero
FAILED tests/test_math.py::test_division[0-10-expected_fail] - ZeroDivisionError: division by zero
##[error]Process completed with exit code 1.
"""
    result = parser.parse(raw_log)
    assert result.has_error is True
    assert result.error_type == "ZeroDivisionError"
    assert result.failed_test == "tests/test_math.py::test_division[0-10-expected_fail]"


def test_parse_syntax_error_log(parser: LogParser):
    raw_log = """
  File "C:/repo/src/calculator.py", line 12
    def broken_syntax(
                     ^
SyntaxError: '(' was never closed
##[error]Process completed with exit code 1.
"""
    result = parser.parse(raw_log)
    assert result.has_error is True
    assert result.error_type == "SyntaxError"
    assert "was never closed" in result.error_message
    assert result.line_number == 12


def test_parse_custom_generic_exception(parser: LogParser):
    raw_log = """
CustomDatabaseConnectionError: Failed to reach host 10.0.0.1 on port 5432
##[error]Process completed with exit code 1.
"""
    result = parser.parse(raw_log)
    assert result.has_error is True
    assert result.error_type == "CustomDatabaseConnectionError"
    assert "10.0.0.1" in result.error_message


def test_credential_redaction_in_log(parser: LogParser):
    raw_log = """
2026-11-13T23:05:00Z Authenticating with ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890
2026-11-13T23:05:01Z Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz123
2026-11-13T23:05:02Z E   ValueError: Token ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890 rejected
FAILED tests/test_auth.py::test_login
"""
    result = parser.parse(raw_log)
    for line in result.context_lines:
        assert "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890" not in line
        assert "eyJhbGci" not in line


def test_empty_and_clean_logs(parser: LogParser):
    empty_result = parser.parse("")
    assert empty_result.has_error is False

    clean_log = """
============================= test session starts =============================
tests/test_calculator.py ..                                              [100%]
============================== 2 passed in 0.03s ==============================
"""
    clean_result = parser.parse(clean_log)
    assert clean_result.has_error is False


# --- Service Tests: Job Log Retrieval & Redirect Security ---


@pytest.mark.asyncio
async def test_job_log_retrieval_redirect_flow_never_sends_token():
    """Verify 302 redirect is captured and download is strictly unauthenticated."""
    auth_header_seen_at_storage = []

    def mock_handler(request: httpx.Request):
        # Initial GitHub request
        if "api.github.com" in request.url.host:
            assert request.headers.get("Authorization") == "Bearer mock_token_123"
            return httpx.Response(
                302,
                headers={"Location": "https://pipelines.actions.githubusercontent.com/signed-download-path"},
            )
        # Secondary signed storage download
        if "pipelines.actions.githubusercontent.com" in request.url.host:
            if "Authorization" in request.headers:
                auth_header_seen_at_storage.append(request.headers["Authorization"])
            return httpx.Response(200, text="Log line 1\nLog line 2\n")
        return httpx.Response(404)

    from app.core.config import Settings
    settings = Settings(GITHUB_PERSONAL_ACCESS_TOKEN="mock_token_123")
    async with httpx.AsyncClient(transport=httpx.MockTransport(mock_handler)) as client:
        service = GitHubService(settings=settings, client=client)
        logs, is_truncated = await service.get_job_raw_logs(12345)
        assert "Log line 1" in logs
        assert is_truncated is False
        # Guarantee token was NEVER forwarded to the storage host
        assert len(auth_header_seen_at_storage) == 0


@pytest.mark.asyncio
async def test_job_log_retrieval_rejects_untrusted_redirect_host():
    """Verify non-whitelisted redirect hosts are rejected with GitHubAPIError."""
    def mock_handler(request: httpx.Request):
        return httpx.Response(
            302,
            headers={"Location": "https://untrusted-malicious-site.com/exploit"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(mock_handler)) as client:
        service = GitHubService(client=client)
        with pytest.raises(GitHubAPIError) as exc_info:
            await service.get_job_raw_logs(12345)
        assert "Untrusted redirect host" in str(exc_info.value)


@pytest.mark.parametrize(
    "malicious_url, expected_error_fragment",
    [
        ("https://attacker-amazonaws.com/logs", "Untrusted redirect host"),
        ("https://amazonaws.com.attacker.example/logs", "Untrusted redirect host"),
        ("https://actions.githubusercontent.com.attacker.example/logs", "Untrusted redirect host"),
        ("https://user:secret@pipelines.actions.githubusercontent.com/logs", "embedded credentials"),
        ("https://pipelines.actions.githubusercontent.com:8443/logs", "Unexpected port"),
        ("http://pipelines.actions.githubusercontent.com/logs", "Insecure non-HTTPS"),
    ],
)
@pytest.mark.asyncio
async def test_job_log_redirect_security_audit_rejections(malicious_url: str, expected_error_fragment: str):
    """Verify strict rejection of boundary bypasses, non-HTTPS, unexpected ports, and credentials."""
    def mock_handler(request: httpx.Request):
        return httpx.Response(302, headers={"Location": malicious_url})

    async with httpx.AsyncClient(transport=httpx.MockTransport(mock_handler)) as client:
        service = GitHubService(client=client)
        with pytest.raises(GitHubAPIError) as exc_info:
            await service.get_job_raw_logs(12345)
        assert expected_error_fragment in str(exc_info.value)


@pytest.mark.parametrize(
    "valid_url",
    [
        "https://pipelines.actions.githubusercontent.com/logs/valid",
        "https://productionresultssa1.s3.us-east-1.amazonaws.com/logs/valid",
        "https://github-production-user-asset.s3.amazonaws.com/logs/valid",
    ],
)
@pytest.mark.asyncio
async def test_job_log_redirect_accepts_valid_expected_hosts(valid_url: str):
    """Verify legitimate GitHub Actions and AWS S3 signed log hostnames are accepted."""
    def mock_handler(request: httpx.Request):
        if "api.github.com" in request.url.host:
            return httpx.Response(302, headers={"Location": valid_url})
        return httpx.Response(200, text="valid log content\n")

    async with httpx.AsyncClient(transport=httpx.MockTransport(mock_handler)) as client:
        service = GitHubService(client=client)
        logs, is_truncated = await service.get_job_raw_logs(12345)
        assert "valid log content" in logs
        assert is_truncated is False


@pytest.mark.asyncio
async def test_job_log_streaming_enforces_5mb_ceiling():
    """Verify streaming aborts and sets is_truncated=True when log exceeds 5 MB."""
    large_chunk = b"A" * (1024 * 1024)  # 1 MB

    def mock_handler(request: httpx.Request):
        if "api.github.com" in request.url.host:
            return httpx.Response(
                302,
                headers={"Location": "https://pipelines.actions.githubusercontent.com/large-log"},
            )
        # Storage returns async stream of 6 chunks of 1 MB = 6 MB total
        async def async_gen():
            for _ in range(6):
                yield large_chunk
        return httpx.Response(200, content=async_gen())

    async with httpx.AsyncClient(transport=httpx.MockTransport(mock_handler)) as client:
        service = GitHubService(client=client)
        logs, is_truncated = await service.get_job_raw_logs(12345)
        assert is_truncated is True
        assert len(logs) == 5 * 1024 * 1024  # Exactly 5 MB


@pytest.mark.asyncio
async def test_job_log_expired_410():
    """Verify HTTP 410 returns GitHubLogExpiredError."""
    def mock_handler(request: httpx.Request):
        return httpx.Response(410, json={"message": "Gone"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(mock_handler)) as client:
        service = GitHubService(client=client)
        with pytest.raises(GitHubLogExpiredError):
            await service.get_job_raw_logs(12345)


# --- API Endpoint Tests ---


def test_post_parse_endpoint_stateless(client: TestClient):
    """Verify POST /api/v1/parser/parse accepts raw log text and returns parsed error."""
    payload = {
        "raw_logs": "E   ModuleNotFoundError: No module named 'requests'\nFAILED tests/test_app.py::test_init\n",
        "failed_step_hint": "Execute Tests",
    }
    response = client.post("/api/v1/parser/parse", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["has_error"] is True
    assert data["error_type"] == "ModuleNotFoundError"
    assert data["failed_step"] == "Execute Tests"


def test_get_job_logs_endpoint_orchestrated(client: TestClient):
    """Verify GET /api/v1/parser/jobs/{job_id} orchestrates retrieval and parsing."""
    class MockService:
        async def get_job_raw_logs(self, job_id, owner=None, repo=None):
            return ("E   AssertionError: assert 1 == 2\nFAILED tests/test_main.py::test_entry\n", False)

    app.dependency_overrides[get_github_service] = lambda: MockService()
    try:
        response = client.get("/api/v1/parser/jobs/998877")
        assert response.status_code == 200
        data = response.json()
        assert data["has_error"] is True
        assert data["error_type"] == "AssertionError"
        assert data["normalized_signature"] == "AssertionError: assert 1 == 2"
    finally:
        app.dependency_overrides.clear()
