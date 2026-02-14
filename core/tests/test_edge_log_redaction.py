"""don't leak secrets into condition eval logs"""

import logging

from framework.graph.edge import EdgeCondition, EdgeSpec


def _edge(expr: str) -> EdgeSpec:
    return EdgeSpec(
        id="test_edge",
        source="node_a",
        target="node_b",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr=expr,
    )


class TestRedactValue:
    def test_normal_key_not_redacted(self):
        assert EdgeSpec._redact_value("status", "active") == "'active'"

    def test_api_key_redacted(self):
        assert EdgeSpec._redact_value("api_key", "sk-12345") == "***REDACTED***"

    def test_token_redacted(self):
        assert EdgeSpec._redact_value("access_token", "tok_abc") == "***REDACTED***"

    def test_password_redacted(self):
        assert EdgeSpec._redact_value("db_password", "hunter2") == "***REDACTED***"

    def test_secret_redacted(self):
        assert EdgeSpec._redact_value("client_secret", "xyz") == "***REDACTED***"

    def test_auth_redacted(self):
        assert EdgeSpec._redact_value("authorization", "Bearer foo") == "***REDACTED***"

    def test_case_insensitive(self):
        assert EdgeSpec._redact_value("API_KEY", "sk-12345") == "***REDACTED***"
        assert EdgeSpec._redact_value("Secret", "shh") == "***REDACTED***"

    def test_long_value_truncated(self):
        long_val = "x" * 200
        result = EdgeSpec._redact_value("description", long_val)
        assert len(result) == 120
        assert result.endswith("...")

    def test_short_value_not_truncated(self):
        assert EdgeSpec._redact_value("status", "ok") == "'ok'"


class TestEvaluateConditionRedaction:
    def test_sensitive_memory_key_not_in_logs(self, caplog):
        edge = _edge("len(api_key) > 0")
        mem = {"api_key": "sk-SUPER-SECRET-12345"}

        with caplog.at_level(logging.INFO):
            result = edge._evaluate_condition(output={}, memory=mem)

        assert result is True
        for record in caplog.records:
            assert "sk-SUPER-SECRET-12345" not in record.getMessage()
        assert "***REDACTED***" in " ".join(r.getMessage() for r in caplog.records)

    def test_non_sensitive_values_visible(self, caplog):
        edge = _edge("status == 'active'")

        with caplog.at_level(logging.INFO):
            edge._evaluate_condition(output={}, memory={"status": "active"})

        assert "'active'" in " ".join(r.getMessage() for r in caplog.records)

    def test_mixed_sensitive_and_normal(self, caplog):
        edge = _edge("status == 'ok' and token == 'abc'")
        mem = {"status": "ok", "token": "secret-bearer-token"}

        with caplog.at_level(logging.INFO):
            edge._evaluate_condition(output={}, memory=mem)

        logs = " ".join(r.getMessage() for r in caplog.records)
        assert "'ok'" in logs
        assert "secret-bearer-token" not in logs
        assert "***REDACTED***" in logs
