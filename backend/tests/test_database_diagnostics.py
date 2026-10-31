from contextlib import nullcontext

import psycopg
import pytest
from fastapi import HTTPException

from app.api import recommendations


@pytest.mark.parametrize(
    "message,reason",
    [
        ("password authentication failed: private-password", "invalid_password"),
        ("Network is unreachable: private-host", "network_unreachable"),
        ("connection timeout expired: private-host", "connection_timeout"),
        ("Tenant or user not found: private-user", "pooler_user_not_found"),
    ],
)
def test_connection_failure_is_logged_without_credentials(monkeypatch, caplog, message, reason):
    monkeypatch.setattr(recommendations, "database_url", lambda: "private-dsn")

    def fail(*args, **kwargs):
        raise psycopg.OperationalError(message)

    monkeypatch.setattr(recommendations.psycopg, "connect", fail)
    with pytest.raises(HTTPException) as caught:
        next(recommendations.get_connection())
    assert caught.value.status_code == 503
    assert "stage=connect" in caplog.text
    assert f"reason={reason}" in caplog.text
    assert "private-" not in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


def test_member_write_failure_is_distinguished_from_connection_failure(monkeypatch, caplog):
    monkeypatch.setattr(recommendations, "database_url", lambda: "private-dsn")
    monkeypatch.setattr(recommendations.psycopg, "connect", lambda *a, **kw: nullcontext(object()))
    dependency = recommendations.get_connection()
    next(dependency)
    with pytest.raises(HTTPException) as caught:
        dependency.throw(psycopg.errors.ForeignKeyViolation("private-user-id private-email"))
    assert caught.value.status_code == 503
    assert "stage=operation" in caplog.text
    assert "sqlstate=23503" in caplog.text
    assert "reason=foreign_key_violation" in caplog.text
    assert "private-" not in caplog.text


def test_missing_database_setting_has_its_own_log_reason(monkeypatch, caplog):
    def missing():
        raise ValueError("private-dsn")

    monkeypatch.setattr(recommendations, "database_url", missing)
    with pytest.raises(HTTPException):
        next(recommendations.get_connection())
    assert "stage=configuration" in caplog.text
    assert "reason=invalid_configuration" in caplog.text
    assert "private-dsn" not in caplog.text
