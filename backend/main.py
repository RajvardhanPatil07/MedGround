import os
import re
from io import BytesIO
from time import perf_counter
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

try:
    from .audit_log import write_audit_event
    from .case_store import store_case
    from .medgemma import MedGemmaError, generate_response, get_model_status
    from .radiology_analyzer import analyze_image, format_finding_assessment, get_radiology_status
    from .verification import verify_response, get_verification_status
    from .rag import get_rag_status
    from .rag_pipeline import RagPipelineError, run_rag_pipeline
    from .report_routes import router as report_router
    from .runtime_checks import get_runtime_status
    from .safety_pipeline import get_safety_pipeline_status, run_post_generation_safety
    from .structured_log import log_event
except ImportError:
    from audit_log import write_audit_event
    from case_store import store_case
    from medgemma import MedGemmaError, generate_response, get_model_status
    from radiology_analyzer import analyze_image, format_finding_assessment, get_radiology_status
    from verification import verify_response, get_verification_status
    from rag import get_rag_status
    from rag_pipeline import RagPipelineError, run_rag_pipeline
    from report_routes import router as report_router
    from runtime_checks import get_runtime_status
    from safety_pipeline import get_safety_pipeline_status, run_post_generation_safety
    from structured_log import log_event


app = FastAPI(title="HalluGuard-Med API")


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_csv(name: str, default: str = "") -> list[str]:
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


CORS_ALLOW_ORIGINS = _env_csv(
    "CORS_ALLOW_ORIGINS",
    "http://127.0.0.1:8000,http://localhost:8000,http://127.0.0.1:5500,http://localhost:5500,http://127.0.0.1:3000,http://localhost:3000",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=_env_bool("CORS_ALLOW_CREDENTIALS", False),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Report export integration: registers PDF generation routes without changing
# chat, MedGemma, RAG, Qdrant, verification, confidence, or radiology logic.
app.include_router(report_router)


IMAGE_MEDGEMMA_MAX_NEW_TOKENS = int(os.getenv("IMAGE_MEDGEMMA_MAX_NEW_TOKENS", "256"))
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
MAX_IMAGE_PIXELS = int(os.getenv("MAX_IMAGE_PIXELS", "12000000"))
ALLOWED_IMAGE_MIME_TYPES = set(_env_csv("ALLOWED_IMAGE_MIME_TYPES", "image/jpeg,image/png,image/webp"))
ALLOWED_IMAGE_EXTENSIONS = set(_env_csv("ALLOWED_IMAGE_EXTENSIONS", ".jpg,.jpeg,.png,.webp"))
EMERGENCY_WARNING = (
    "Urgent safety warning: your message includes symptoms or concerns that can be medical emergencies. "
    "Seek emergency medical care now or call your local emergency number. "
    "Do not rely on this AI response to decide whether urgent care is needed."
)
RADIOLOGY_SCREENING_WARNING = (
    "Image safety note: uploaded image analysis is screening-only and cannot confirm or rule out a diagnosis. "
    "A qualified clinician or radiologist should review the original image."
)
RADIOLOGY_MODALITY_WARNING = (
    "Image modality warning: this system cannot verify that the uploaded image is a valid chest X-ray or the correct view."
)
EMERGENCY_PATTERNS = [
    r"\bchest pain\b",
    r"\b(stroke|face droop|facial droop|arm weakness|speech difficulty|slurred speech)\b",
    r"\b(difficulty breathing|shortness of breath|trouble breathing|can't breathe|cannot breathe)\b",
    r"\b(severe bleeding|uncontrolled bleeding|bleeding heavily)\b",
    r"\b(severe allergic reaction|anaphylaxis|throat swelling|tongue swelling)\b",
    r"\b(suicidal thoughts|suicide|self harm|self-harm|want to die)\b",
]
INTERNAL_CITATION_RE = re.compile(
    r"\s*\[[A-Z0-9][A-Z0-9_-]{2,}(?:-[A-Z0-9_-]+)*\]",
    re.IGNORECASE,
)


def _validate_upload_metadata(image: UploadFile) -> None:
    content_type = (image.content_type or "").lower().strip()
    if content_type not in ALLOWED_IMAGE_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported image MIME type: {content_type or 'unknown'}",
        )

    filename = image.filename or ""
    extension = os.path.splitext(filename)[1].lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported image file extension: {extension or 'none'}",
        )


def _validate_image_pixels(image_bytes: bytes) -> None:
    try:
        from PIL import Image

        Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
        with Image.open(BytesIO(image_bytes)) as image:
            image.verify()
            width, height = image.size
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image.") from exc

    if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
        raise HTTPException(
            status_code=413,
            detail=f"Image dimensions exceed the configured pixel limit of {MAX_IMAGE_PIXELS}.",
        )


async def _read_validated_image(image: UploadFile | None) -> bytes | None:
    if image is None:
        return None

    _validate_upload_metadata(image)
    image_bytes = await image.read(MAX_UPLOAD_BYTES + 1)
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Image upload exceeds the configured size limit of {MAX_UPLOAD_BYTES} bytes.",
        )
    if not image_bytes:
        return None

    _validate_image_pixels(image_bytes)
    return image_bytes


def _new_case_id() -> str:
    return f"HGM-{uuid4().hex[:12].upper()}"


def _detect_emergency(query: str) -> dict[str, Any]:
    matched = [
        pattern
        for pattern in EMERGENCY_PATTERNS
        if re.search(pattern, query or "", re.IGNORECASE)
    ]
    return {
        "detected": bool(matched),
        "matched_patterns": matched,
        "warning": EMERGENCY_WARNING if matched else None,
    }


def _prepend_warning(answer: str, warning: str) -> str:
    if not warning or warning in answer:
        return answer
    return f"{warning}\n\n{answer}".strip()
INTERNAL_CITATION_ID_RE = re.compile(
    r"^[A-Z0-9][A-Z0-9_-]{2,}(?:-[A-Z0-9_-]+)*$",
    re.IGNORECASE,
)


def _title_label(value: Any) -> str:
    text = str(value or "").replace("_", " ").strip()
    return re.sub(r"\s+", " ", text).title() if text else ""


def _display_citation_label(item: dict[str, Any] | None) -> str:
    item = item or {}
    source = str(item.get("source") or "Retrieved evidence").strip()
    condition = _title_label(item.get("condition") or item.get("section") or "Medical Evidence")
    return f"{source} - {condition}" if condition else source


def _strip_internal_citation_ids(text: Any) -> Any:
    if not isinstance(text, str):
        return text
    return re.sub(INTERNAL_CITATION_RE, "", text).strip()


def _build_image_augmented_query(query: str, imaging_result: dict[str, Any] | None) -> str:
    if not imaging_result:
        return query

    status = imaging_result.get("status")
    if status == "Neutral":
        normal_score = imaging_result.get("normal_score")
        parts = [query]
        if normal_score is not None:
            parts.append(
                f"Radiology screening: no high-confidence finding detected; normal-likelihood {normal_score}%."
            )
        else:
            parts.append("Radiology screening: no high-confidence finding detected.")
        parts.append(
            "Not a confirmed normal diagnosis; clinician/radiologist review is required."
        )
        return " ".join(parts)

    if status != "Analyzed":
        return query

    findings = imaging_result.get("findings") or []
    critical = imaging_result.get("critical") or []
    scores = imaging_result.get("percentage_scores") or {}
    parts = [query]
    top_scores = sorted(scores.items(), key=lambda item: float(item[1]), reverse=True)[:4]
    if top_scores:
        score_text = ", ".join(f"{name} {float(value):.1f}%" for name, value in top_scores)
        parts.append(f"Radiology screening findings: {score_text}.")
    elif findings:
        parts.append(f"Detected radiology findings: {', '.join(findings)}.")
    if critical:
        parts.append(f"High-confidence finding: {', '.join(critical)}.")
    parts.append(
        "Use these as screening signals, not confirmed diagnoses; mention radiologist review."
    )
    return " ".join(parts)


def _image_bytes_for_generation(
    image_bytes: bytes | None,
    imaging_result: dict[str, Any] | None,
) -> bytes | None:
    if not image_bytes:
        return None

    mode = os.getenv("MEDGEMMA_RAW_IMAGE_MODE", "radiology_error").lower()
    if mode == "always":
        return image_bytes
    if mode == "never":
        return None

    status = (imaging_result or {}).get("status")
    if status in {"Analyzed", "Neutral"}:
        return None
    return image_bytes


def _ensure_citation_section(answer: str, citations: list[dict[str, Any]]) -> tuple[str, bool]:
    if not citations:
        return answer, False
    citation_ids = [str(item.get("id") or "").strip() for item in citations if item.get("id")]
    if not citation_ids:
        return answer, False
    has_citation_section = bool(re.search(r"(?im)^\s*(?:\*\*)?citations?(?:\*\*)?\s*:?\s*$", answer))
    if has_citation_section:
        return answer, False
    lines = ["", "", "Citations:"]
    for item in citations[:3]:
        lines.append(f"- {_display_citation_label(item)}.")
    return answer.rstrip() + "\n".join(lines), True


def _sanitize_user_facing_payload(payload: dict[str, Any]) -> dict[str, Any]:
    citation_labels: dict[str, str] = {}
    analysis = payload.get("analysis") or {}
    citations = analysis.get("citations") or payload.get("citations") or []
    for citation in citations:
        if isinstance(citation, dict) and citation.get("id"):
            citation_labels[str(citation["id"])] = _display_citation_label(citation)

    def label_for(raw_id: Any) -> str | None:
        if raw_id is None:
            return None
        raw_text = str(raw_id)
        if raw_text == "IMG1":
            return "Uploaded Image Analysis"
        if INTERNAL_CITATION_ID_RE.match(raw_text):
            return citation_labels.get(raw_text) or "Retrieved Evidence"
        return citation_labels.get(raw_text) or _title_label(raw_text)

    def scrub(value: Any) -> Any:
        if isinstance(value, str):
            return _strip_internal_citation_ids(value)
        if isinstance(value, list):
            return [scrub(item) for item in value]
        if isinstance(value, dict):
            cleaned: dict[str, Any] = {}
            for key, item in value.items():
                if key in {"id", "citation_id", "best_citation_id", "citation_a", "citation_b"}:
                    cleaned[key] = label_for(item)
                else:
                    cleaned[key] = scrub(item)
            return cleaned
        return value

    return scrub(payload)


@app.get("/", response_class=HTMLResponse)
def root() -> str:
    return """
    <html>
      <head><title>HalluGuard-Med API</title></head>
      <body style="font-family: Arial, sans-serif; margin: 40px;">
        <h1>🛡️ HalluGuard-Med API</h1>
        <p>Backend is running.</p>
        <ul>
          <li><a href="/docs">Open API docs</a></li>
          <li><a href="/health">Check health</a></li>
          <li><a href="/api/model-status">Check model status</a></li>
        </ul>
      </body>
    </html>
    """


@app.get("/health")
def health() -> dict[str, Any]:
    runtime = get_runtime_status()
    return {
        "status": runtime["status"],
        "model": runtime["medgemma"],
        "failures": runtime["failures"],
    }


@app.get("/api/health")
def api_health() -> dict[str, Any]:
    return get_runtime_status()


@app.get("/api/model-status")
def model_status() -> dict[str, Any]:
    """
    Returns full status of all system modules.
    Useful for debugging in Cell 7 of Kaggle notebook.
    """
    return {
        "medgemma": get_model_status(),
        "radiology": get_radiology_status(),
        "verification": get_verification_status(),
        "safety_pipeline": get_safety_pipeline_status(),
        "rag": get_rag_status(),
    }


@app.get("/api/retrieval-status")
def retrieval_status() -> dict[str, Any]:
    runtime = get_runtime_status()
    return {
        "status": "ok" if runtime["qdrant"]["available"] and runtime["retrieval"].get("google_api_key_configured") else "unavailable",
        "retrieval": runtime["retrieval"],
        "qdrant": runtime["qdrant"],
        "google_api_key_configured": runtime["checks"]["google_api_key"]["ok"],
    }


@app.post("/api/chat", response_model=None)
async def chat(
    query: str = Form(...),
    image: UploadFile | None = File(default=None),
) -> dict[str, Any] | JSONResponse:
    """
    Main chat endpoint.

    Request:
        query — medical question (text)
        image — optional chest X-ray image

    Response format:
        final_response  — MedGemma's answer (never modified)
        analysis:
            risk_tier       — Tier 1 / Tier 2 / Tier 3
            kg              — Match / Neutral
            nli:
                label       — Entailed / Contradicted / Neutral
                confidence  — float 0-1 or null
            rag_score       — float 0-1 or null
            rag_verified    — bool or null
            imaging:
                status          — Analyzed / Neutral / N/A / Error
                findings        — list of detected pathologies
                critical        — list of critical findings
                normal_score    — float % or null
                percentage_scores — dict {pathology: %} or null
        warnings        — list of warning strings
        suggestions     — list of suggestion strings
        matched_conditions — list of matched condition names
        image_uploaded  — bool
    """

    # ── Read image ──
    chat_start = perf_counter()
    case_id = _new_case_id()
    emergency = _detect_emergency(query)
    chat_timing_ms: dict[str, float] = {}
    image_read_start = perf_counter()
    image_bytes = await _read_validated_image(image)
    chat_timing_ms["image_upload_read"] = round((perf_counter() - image_read_start) * 1000.0, 2)
    image_uploaded = image_bytes is not None and len(image_bytes) > 0
    image_warnings = [RADIOLOGY_SCREENING_WARNING, RADIOLOGY_MODALITY_WARNING] if image_uploaded else []
    image_analysis_start = perf_counter()
    imaging_result = analyze_image(image_bytes) if image_uploaded else None
    if imaging_result is not None:
        existing_warnings = imaging_result.get("warnings", [])
        imaging_result["warnings"] = list(dict.fromkeys([*image_warnings, *existing_warnings]))
    chat_timing_ms["image_analysis"] = round((perf_counter() - image_analysis_start) * 1000.0, 2)
    query_build_start = perf_counter()
    retrieval_query = _build_image_augmented_query(query, imaging_result)
    chat_timing_ms["retrieval_query_build"] = round((perf_counter() - query_build_start) * 1000.0, 2)
    log_event(
        "runtime",
        "stage_timing",
        stage_name="image_upload_and_analysis",
        duration_ms=round(
            chat_timing_ms["image_upload_read"]
            + chat_timing_ms["image_analysis"]
            + chat_timing_ms["retrieval_query_build"],
            2,
        ),
        image_uploaded=image_uploaded,
        image_bytes=len(image_bytes or b""),
        image_upload_read_ms=chat_timing_ms["image_upload_read"],
        image_analysis_ms=chat_timing_ms["image_analysis"],
        retrieval_query_build_ms=chat_timing_ms["retrieval_query_build"],
        imaging_timing_ms=(imaging_result or {}).get("timing_ms"),
    )

    # Retrieve evidence before generation. Never generate without grounded context.
    retrieval_start = perf_counter()
    try:
        rag_result = run_rag_pipeline(retrieval_query)
    except RagPipelineError as exc:
        log_event(
            "runtime",
            "chat_failed_rag",
            "error",
            query_chars=len(query),
            image_uploaded=image_uploaded,
            error=str(exc),
        )
        write_audit_event({
            "case_id": case_id,
            "query": query,
            "image_uploaded": image_uploaded,
            "model_available": None,
            "rag_available": False,
            "rag_error": str(exc),
            "generated_response": False,
        })
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "RAG_RETRIEVAL_FAILED",
                    "message": (
                        "Hybrid RAG retrieval failed. "
                        "No AI medical response was generated."
                    ),
                    "detail": str(exc),
                    "rag_status": get_rag_status(),
                }
            },
        )

    retrieval_duration_ms = round((perf_counter() - retrieval_start) * 1000.0, 2)
    chat_timing_ms["retrieval_and_pre_generation_safety"] = retrieval_duration_ms
    log_event(
        "runtime",
        "stage_timing",
        stage_name="rag_retrieval_and_pre_generation_safety",
        duration_ms=retrieval_duration_ms,
        query_chars=len(retrieval_query),
    )

    # Generate MedGemma response. Never continue with synthetic text.
    generation_start = perf_counter()
    try:
        generation_image_bytes = _image_bytes_for_generation(image_bytes, imaging_result)
        log_event(
            "runtime",
            "medgemma_image_forwarding",
            image_uploaded=image_uploaded,
            image_forwarded=generation_image_bytes is not None,
            imaging_status=(imaging_result or {}).get("status"),
            mode=os.getenv("MEDGEMMA_RAW_IMAGE_MODE", "radiology_error"),
        )
        generation_token_limit = IMAGE_MEDGEMMA_MAX_NEW_TOKENS if image_uploaded else None
        ai_response = generate_response(
            rag_result["grounded_query"],
            generation_image_bytes,
            max_new_tokens=generation_token_limit,
        )
        if emergency["detected"]:
            ai_response = _prepend_warning(ai_response, EMERGENCY_WARNING)
        ai_response, citations_appended = _ensure_citation_section(
            ai_response,
            rag_result.get("citations", []),
        )
        if citations_appended:
            log_event(
                "runtime",
                "citation_section_appended",
                citations_count=len(rag_result.get("citations", [])),
            )
    except MedGemmaError as exc:
        model_status_data = get_model_status()
        log_event(
            "runtime",
            "chat_failed_generation",
            "error",
            query_chars=len(query),
            image_uploaded=image_uploaded,
            error=str(exc),
            model_status=model_status_data.get("status"),
        )
        write_audit_event({
            "case_id": case_id,
            "query": query,
            "image_uploaded": image_uploaded,
            "model_available": False,
            "model_status": model_status_data.get("status"),
            "model_error": str(exc),
            "generated_response": False,
        })
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "MEDGEMMA_UNAVAILABLE",
                    "message": (
                        "MedGemma is not available. "
                        "No AI medical response was generated."
                    ),
                    "model_status": model_status_data,
                }
            },
        )

    # ── Radiology analysis ──
    # ── Clinical claim safety layer ──
    generation_duration_ms = round((perf_counter() - generation_start) * 1000.0, 2)
    chat_timing_ms["response_generation"] = generation_duration_ms
    log_event(
        "runtime",
        "stage_timing",
        stage_name="response_generation",
        duration_ms=generation_duration_ms,
        prompt_chars=len(rag_result["grounded_query"]),
        response_chars=len(ai_response),
    )

    post_start = perf_counter()
    post_generation_safety = run_post_generation_safety(
        query=query,
        answer=ai_response,
        rag_result=rag_result,
        precheck=rag_result.get("safety_precheck", {}),
        imaging_result=imaging_result,
    )
    post_generation_safety["emergency"] = emergency
    if image_uploaded:
        post_generation_safety["radiology_caution"] = {
            "screening_only": True,
            "modality_verified": False,
            "warnings": image_warnings,
        }
    post_duration_ms = round((perf_counter() - post_start) * 1000.0, 2)
    chat_timing_ms["claim_extraction_and_verification"] = post_duration_ms
    log_event(
        "runtime",
        "stage_timing",
        stage_name="claim_extraction_and_nli_verification",
        duration_ms=post_duration_ms,
        claims_count=len(post_generation_safety.get("claims", [])),
    )

    # ── Verification pipeline ──
    verification_start = perf_counter()
    verification = verify_response(
        query,
        ai_response,
        imaging_result,
        rag_result,
        safety_result=post_generation_safety,
    )
    verification_duration_ms = round((perf_counter() - verification_start) * 1000.0, 2)
    chat_timing_ms["risk_scoring"] = verification_duration_ms
    log_event(
        "runtime",
        "stage_timing",
        stage_name="risk_scoring",
        duration_ms=verification_duration_ms,
        risk_score=verification["risk_score"],
        risk_tier=verification["risk_tier"],
    )
    # ── Build imaging section for response ──
    if imaging_result is None:
        imaging_data = {
            "status": "N/A",
            "findings": None,
            "critical": None,
            "normal_score": None,
            "percentage_scores": None,
            "warnings": [],
        }
    else:
        imaging_data = {
            "status": imaging_result.get("status"),
            "findings": imaging_result.get("findings"),
            "critical": imaging_result.get("critical"),
            "normal_score": imaging_result.get("normal_score"),
            "percentage_scores": imaging_result.get("percentage_scores"),
            "timing_ms": imaging_result.get("timing_ms"),
            "warnings": imaging_result.get("warnings", []),
        }

    # ── Build full response ──
    result = {
        "case_id": case_id,
        "query": query,
        "final_response": ai_response,
        "analysis": {
            "risk_tier": verification["risk_tier"],
            "risk_score": verification["risk_score"],
            "risk_reasons": verification["risk_reasons"],
            "final_assessment": verification.get("final_assessment"),
            "kg": verification["kg"],
            "nli": verification["nli"],
            "verification_mode": verification.get("verification_mode"),
            "verified_claim_count": verification.get("verified_claim_count"),
            "total_claim_count": verification.get("total_claim_count"),
            "rag_score": verification["rag_score"],
            "rag_verified": verification["rag_verified"],
            "rag_error": verification["rag_error"],
            "retrieval_summary": rag_result.get("retrieval_summary", {}),
            "citations": verification["citations"],
            "imaging": imaging_data,
            "safety": {
                "pre_generation": {
                    "query_entities": rag_result.get("safety_precheck", {}).get("query_entities", []),
                    "evidence_scores": rag_result.get("safety_precheck", {}).get("evidence_scores", []),
                    "source_conflicts": rag_result.get("safety_precheck", {}).get("source_conflicts", []),
                },
                "post_generation": post_generation_safety,
            },
            "confidence": post_generation_safety.get("confidence"),
            "claims_summary": post_generation_safety.get("claims_summary", {}),
            "claim_verification": post_generation_safety.get("claim_verification", []),
        },
        "warnings": verification["warnings"],
        "suggestions": verification["suggestions"],
        "matched_conditions": verification["matched_conditions"],
        "citations": verification["citations"],
        "image_uploaded": image_uploaded,
        "meta": {
            "response_chars": len(ai_response),
            "timing_ms": {
                **chat_timing_ms,
                "total": round((perf_counter() - chat_start) * 1000.0, 2),
            },
        },
    }

    # ── Audit log ──
    if emergency["detected"]:
        if EMERGENCY_WARNING not in result["warnings"]:
            result["warnings"].insert(0, EMERGENCY_WARNING)
        if EMERGENCY_WARNING not in result["suggestions"]:
            result["suggestions"].insert(0, EMERGENCY_WARNING)
    if image_uploaded:
        for warning in image_warnings:
            if warning not in result["warnings"]:
                result["warnings"].append(warning)

    write_audit_event({
        "case_id": case_id,
        "query": query,
        "image_uploaded": image_uploaded,
        "model_available": True,
        "risk_tier": verification["risk_tier"],
        "risk_score": verification["risk_score"],
        "risk_reasons": verification["risk_reasons"],
        "safety_confidence": post_generation_safety.get("confidence"),
        "claim_verification": post_generation_safety.get("claim_verification", []),
        "source_conflicts": rag_result.get("safety_precheck", {}).get("source_conflicts", []),
        "rag_score": verification["rag_score"],
        "rag_verified": verification["rag_verified"],
        "rag_error": verification["rag_error"],
        "citations": verification["citations"],
        "nli_label": verification["nli"]["label"],
        "matched_conditions": verification["matched_conditions"],
        "imaging_status": imaging_data["status"],
        "critical_findings": imaging_data["critical"],
    })
    log_event(
        "runtime",
        "chat_completed",
        duration_ms=round((perf_counter() - chat_start) * 1000.0, 2),
        query_chars=len(query),
        image_uploaded=image_uploaded,
        response_chars=len(ai_response),
        risk_tier=verification["risk_tier"],
        rag_score=verification["rag_score"],
        nli_label=verification["nli"]["label"],
        imaging_status=imaging_data["status"],
    )

    store_case(case_id, result)
    return _sanitize_user_facing_payload(result)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
