from __future__ import annotations

from argus.core.logging import redact_url_secrets


def test_redact_url_secrets_redacts_query_tokens() -> None:
    assert (
        redact_url_secrets("rtsp://camera.internal/live?jwt=abc123&foo=bar")
        == "rtsp://camera.internal/live?jwt=redacted&foo=bar"
    )


def test_redact_url_secrets_redacts_rtsp_credentials() -> None:
    assert (
        redact_url_secrets("rtsp://user:pass@192.168.1.10:8554/ch2")
        == "rtsp://redacted@192.168.1.10:8554/ch2"
    )
