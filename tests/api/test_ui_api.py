"""Contract and guardrail tests for read-only UI API."""

from fastapi.testclient import TestClient

from kal_predict.api.app import create_app


def test_health_endpoint_contract() -> None:
    client = TestClient(create_app())
    response = client.get("/api/ui/health")
    assert response.status_code == 200
    body = response.json()
    assert "timestamp" in body
    assert "freshness_seconds" in body
    assert "source" in body
    assert "mode" in body
    assert "heartbeat_status" in body


def test_markets_endpoint_contract() -> None:
    client = TestClient(create_app())
    response = client.get("/api/ui/markets?limit=5")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body.get("markets"), list)


def test_decisions_endpoint_contract() -> None:
    client = TestClient(create_app())
    response = client.get("/api/ui/decisions?limit=5")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body.get("decisions"), list)


def test_replay_metrics_endpoint_contract() -> None:
    client = TestClient(create_app())
    response = client.get("/api/ui/metrics/replay")
    assert response.status_code == 200
    body = response.json()
    assert "brier_threshold" in body
    assert "brier_pass" in body


def test_inference_health_endpoint_contract() -> None:
    client = TestClient(create_app())
    response = client.get("/api/ui/inference-health")
    assert response.status_code == 200
    body = response.json()
    assert "inference" in body
    assert "hands_model" in body["inference"]
    assert "fallback_rate" in body["inference"]


def test_trial_decision_trace_endpoint_contract() -> None:
    client = TestClient(create_app())
    response = client.get("/api/ui/trial-decision-trace?limit=5")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body.get("traces"), list)
    if body["traces"]:
        first = body["traces"][0]
        assert "gate_context" in first
        assert "expected_value" in first


def test_paper_metrics_endpoint_contract() -> None:
    client = TestClient(create_app())
    response = client.get("/api/ui/metrics/paper")
    assert response.status_code == 200
    body = response.json()
    assert "paper_pnl" in body
    assert "total_trades" in body


def test_audit_endpoint_contract() -> None:
    client = TestClient(create_app())
    response = client.get("/api/ui/audit?limit=10")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body.get("events"), list)


def test_ui_routes_are_read_only() -> None:
    client = TestClient(create_app())
    response = client.post("/api/ui/health")
    assert response.status_code == 405
    body = response.json()
    assert body["error_code"] == "method_not_allowed"


def test_trial_markets_endpoint_contract() -> None:
    client = TestClient(create_app())
    response = client.get("/api/trial/markets?limit=5")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body.get("markets"), list)
    if body["markets"]:
        item = body["markets"][0]
        assert "inference_source" in item
        assert "inference_fallback_reason" in item
        assert "inference_latency_ms" in item
        assert "model" in item


def test_trial_book_and_betting_flow() -> None:
    client = TestClient(create_app())

    first_market = client.get("/api/trial/markets?limit=1").json()["markets"][0]["market_id"]
    before = client.get("/api/trial/book").json()
    before_balance = float(before["balance_usd"])

    place = client.post(
        "/api/trial/bets/manual",
        json={"market_id": first_market, "side": "YES", "contracts": 1},
    )
    assert place.status_code == 200
    assert place.json().get("ok") is True

    after = client.get("/api/trial/book").json()
    assert float(after["balance_usd"]) < before_balance
    assert isinstance(after.get("bets"), list)


def test_trial_manual_bet_invalid_side_validation() -> None:
    client = TestClient(create_app())
    first_market = client.get("/api/trial/markets?limit=1").json()["markets"][0]["market_id"]
    response = client.post(
        "/api/trial/bets/manual",
        json={"market_id": first_market, "side": "MAYBE", "contracts": 1},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "validation_error"


def test_trial_manual_bet_invalid_market_id_validation() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/api/trial/bets/manual",
        json={"market_id": "bad-market-id", "side": "YES", "contracts": 1},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "validation_error"


def test_trial_manual_bet_insufficient_balance_error_envelope() -> None:
    client = TestClient(create_app())
    first_market = client.get("/api/trial/markets?limit=1").json()["markets"][0]["market_id"]
    response = client.post(
        "/api/trial/bets/manual",
        json={"market_id": first_market, "side": "YES", "contracts": 1000},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "insufficient_balance"
    assert "trace_id" in body


def test_trial_scenario_dry_run_contract() -> None:
    client = TestClient(create_app())
    first_market = client.get("/api/trial/markets?limit=1").json()["markets"][0]["market_id"]
    response = client.post(
        "/api/trial/scenarios/run",
        json={
            "dry_run": True,
            "scenarios": [
                {"market_id": first_market, "mode": "auto", "contracts": 1},
                {"market_id": first_market, "mode": "manual", "side": "YES", "contracts": 1},
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["dry_run"] is True
    assert "summary" in body
    assert body["summary"]["total"] == 2
