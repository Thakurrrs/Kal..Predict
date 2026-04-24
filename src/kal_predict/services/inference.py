"""Ollama-backed inference service with deterministic fallback."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from threading import Lock
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import ollama

from kal_predict.config import AppConfig
from kal_predict.logging_setup import get_logger

logger = get_logger(__name__)


@dataclass
class InferenceResult:
    probability: float
    source: str
    model: str
    raw: str
    parse_ok: bool
    fallback_reason: Optional[str]
    latency_ms: int
    role: str


class InferenceService:
    """Generate posterior probabilities via Ollama local models."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._validate_base_url(config.ollama.base_url)
        self._client = ollama.Client(host=config.ollama.base_url)
        self._lock = Lock()
        self._total_calls = 0
        self._fallback_calls = 0
        self._last_source = "unknown"
        self._last_fallback_reason: Optional[str] = None

    def _fallback_probability(
        self, market_prior: float, evidence_items: List[Dict[str, Any]]
    ) -> float:
        """Deterministic fallback if inference is unavailable."""
        if not evidence_items:
            return market_prior
        weighted = 0.0
        total = 0.0
        for item in evidence_items:
            confidence = float(item.get("confidence_hint", 0.5))
            reliability = float(item.get("reliability_score", 0.7))
            weighted += (confidence - 0.5) * reliability
            total += reliability
        shift = (weighted / total) if total > 0 else 0.0
        return max(0.0, min(1.0, market_prior + (shift * 0.25)))

    def _validate_base_url(self, base_url: str) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("OLLAMA_BASE_URL must use http or https")
        if not parsed.netloc:
            raise ValueError("OLLAMA_BASE_URL must include host")

    def _prompt(
        self, market_id: str, market_prior: float, evidence_items: List[Dict[str, Any]]
    ) -> str:
        claims = [str(item.get("claim", "")) for item in evidence_items[:8]]
        evidence_block = "\n".join(f"- {claim}" for claim in claims if claim.strip())
        return (
            "You are a calibrated forecast model. Return only JSON.\n"
            "Task: estimate probability for YES outcome in [0,1].\n"
            f"market_id: {market_id}\n"
            f"market_prior: {market_prior:.4f}\n"
            "recent_evidence:\n"
            f"{evidence_block if evidence_block else '- no evidence'}\n\n"
            'Output JSON exactly: {"probability": <float 0..1>}'
        )

    def posterior_probability(
        self,
        market_id: str,
        market_prior: float,
        evidence_items: List[Dict[str, Any]],
        role: str = "hands",
        model: Optional[str] = None,
    ) -> InferenceResult:
        """Get posterior probability from Ollama with safe fallback."""
        model_name = model or (
            self._config.ollama.brain_model if role == "brain" else self._config.ollama.hands_model
        )
        prompt = self._prompt(market_id, market_prior, evidence_items)
        fallback = self._fallback_probability(market_prior, evidence_items)
        started = time.perf_counter()
        fallback_reason: Optional[str] = None
        source = "ollama"
        parse_ok = True
        raw = ""
        try:
            response = self._client.chat(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                format="json",
                options={"temperature": 0},
            )
            content = str(response.get("message", {}).get("content", "")).strip()
            raw = content
            parsed = json.loads(content)
            if "probability" not in parsed:
                raise ValueError("malformed_output_missing_probability")
            probability = max(0.0, min(1.0, float(parsed.get("probability"))))
        except json.JSONDecodeError:
            probability = fallback
            source = "fallback"
            parse_ok = False
            fallback_reason = "malformed_output_json"
        except (TypeError, ValueError) as exc:
            probability = fallback
            source = "fallback"
            parse_ok = False
            fallback_reason = str(exc)
        except Exception as exc:  # pragma: no cover
            exc_name = exc.__class__.__name__.lower()
            fallback_reason = "ollama_connectivity_error"
            if "timeout" in exc_name:
                fallback_reason = "ollama_timeout"
            elif "responseerror" in exc_name and "not found" in str(exc).lower():
                fallback_reason = "model_not_found"
            logger.warning(
                "Ollama inference fallback",
                extra={
                    "event_type": "inference_fallback",
                    "actor": "inference_service",
                    "model": model_name,
                    "error_class": exc.__class__.__name__,
                },
            )
            probability = fallback
            source = "fallback"
            parse_ok = False

        latency_ms = int((time.perf_counter() - started) * 1000)
        with self._lock:
            self._total_calls += 1
            if source == "fallback":
                self._fallback_calls += 1
            self._last_source = source
            self._last_fallback_reason = fallback_reason

        return InferenceResult(
            probability=probability,
            source=source,
            model=model_name,
            raw=raw,
            parse_ok=parse_ok,
            fallback_reason=fallback_reason,
            latency_ms=latency_ms,
            role=role,
        )

    def health(self) -> Dict[str, Any]:
        """Expose inference runtime health for observability endpoints."""
        with self._lock:
            total = self._total_calls
            fallback = self._fallback_calls
            last_source = self._last_source
            last_reason = self._last_fallback_reason
        fallback_rate = (float(fallback) / float(total)) if total > 0 else 0.0
        return {
            "base_url": self._config.ollama.base_url,
            "brain_model": self._config.ollama.brain_model,
            "hands_model": self._config.ollama.hands_model,
            "total_calls": total,
            "fallback_calls": fallback,
            "fallback_rate": round(fallback_rate, 4),
            "last_source": last_source,
            "last_fallback_reason": last_reason,
        }
