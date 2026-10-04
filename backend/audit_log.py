import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOG_PATH = Path(__file__).resolve().parent / "audit.log"
TEXT_KEYS = {"query", "answer", "final_response", "claim", "best_evidence", "text", "detail"}
SUMMARY_KEYS = {
    "case_id",
    "image_uploaded",
    "model_available",
    "rag_available",
    "generated_response",
    "risk_tier",
    "risk_score",
    "rag_score",
    "rag_verified",
    "rag_error",
    "nli_label",
    "matched_conditions",
    "imaging_status",
    "critical_findings",
}


def _text_summary(value: Any) -> dict[str, Any]:
    text = str(value or "")
    return {
        "redacted": True,
        "chars": len(text),
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest() if text else None,
    }


def _summarize_claims(items: Any) -> dict[str, Any]:
    rows = items if isinstance(items, list) else []
    statuses: dict[str, int] = {}
    for item in rows:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "unknown")
        statuses[status] = statuses.get(status, 0) + 1
    return {
        "count": len(rows),
        "statuses": statuses,
    }


def _summarize_citations(items: Any) -> dict[str, Any]:
    rows = items if isinstance(items, list) else []
    return {
        "count": len(rows),
        "sources": sorted({
            str(item.get("source"))
            for item in rows
            if isinstance(item, dict) and item.get("source")
        })[:10],
        "conditions": sorted({
            str(item.get("condition"))
            for item in rows
            if isinstance(item, dict) and item.get("condition")
        })[:10],
    }


def _sanitize_value(key: str, value: Any) -> Any:
    if key in TEXT_KEYS:
        return _text_summary(value)
    if key == "claim_verification":
        return _summarize_claims(value)
    if key == "citations":
        return _summarize_citations(value)
    if key == "safety_confidence" and isinstance(value, dict):
        return {
            "score": value.get("score"),
            "label": value.get("label"),
            "should_answer": value.get("should_answer"),
            "should_refuse": value.get("should_refuse"),
            "reasons_count": len(value.get("reasons") or []),
        }
    if key == "source_conflicts" and isinstance(value, list):
        return {"count": len(value)}
    if isinstance(value, str) and len(value) > 200:
        return _text_summary(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        if all(isinstance(item, (str, int, float, bool)) or item is None for item in value):
            return value[:20]
        return {"count": len(value)}
    if isinstance(value, dict):
        return {
            nested_key: _sanitize_value(nested_key, nested_value)
            for nested_key, nested_value in value.items()
            if nested_key in SUMMARY_KEYS
        }
    return str(type(value).__name__)


def _sanitize_event(event: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in event.items():
        if key in SUMMARY_KEYS or key in TEXT_KEYS or key in {
            "claim_verification",
            "citations",
            "safety_confidence",
            "source_conflicts",
            "model_status",
            "model_error",
        }:
            sanitized[key] = _sanitize_value(key, value)
    return sanitized


def write_audit_event(event: dict[str, Any]) -> None:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **_sanitize_event(event),
    }
    with LOG_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=True) + "\n")
