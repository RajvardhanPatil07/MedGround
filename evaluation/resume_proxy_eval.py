from __future__ import annotations

import json
import time
from pathlib import Path

from run_proxy_eval import (
    BACKEND_CHAT_URL,
    OUTPUT_DIR,
    QUESTIONS,
    aggregate,
    compact_method_row,
    evaluate_answer_with_pipeline,
    generate_baseline,
    load_existing,
    post_form,
    replace_record,
    replace_rows,
    save_outputs,
)


def method_ok(record: dict, method: str) -> bool:
    payload = record.get(method) or {}
    evaluation = payload.get("evaluation") or {}
    return bool(payload.get("answer")) and not evaluation.get("error")


def run_one(qid: str, question: str, existing: dict | None) -> dict:
    started = time.time()
    record = existing or {"question_id": qid, "question": question}

    if method_ok(record, "halluguard"):
        print(f"[{qid}] HalluGuard already ok", flush=True)
        hallu_answer = record["halluguard"]["answer"]
        hallu_eval = record["halluguard"]["evaluation"]
        hallu_raw = record["halluguard"].get("raw", {})
    else:
        print(f"[{qid}] HalluGuard retry...", flush=True)
        try:
            hallu_raw = post_form(BACKEND_CHAT_URL, {"query": question}, timeout=360)
            hallu_answer = str(hallu_raw.get("final_response") or "")
            analysis = hallu_raw.get("analysis") or {}
            hallu_eval = {
                "rag_score": analysis.get("rag_score"),
                "rag_verified": analysis.get("rag_verified"),
                "claims_summary": analysis.get("claims_summary", {}),
                "claim_verification": analysis.get("claim_verification", []),
                "confidence": analysis.get("confidence", {}),
                "verification_mode": analysis.get("verification_mode"),
                "warnings": hallu_raw.get("warnings", []),
                "risk_tier": analysis.get("risk_tier"),
                "risk_score": analysis.get("risk_score"),
            }
        except Exception as exc:
            hallu_answer = ""
            hallu_raw = {"error": str(exc)}
            hallu_eval = {"claims_summary": {}, "confidence": {}, "error": str(exc)}
            print(f"[{qid}] HalluGuard error: {exc}", flush=True)

    if method_ok(record, "baseline_medgemma"):
        print(f"[{qid}] Baseline already ok", flush=True)
        baseline_answer = record["baseline_medgemma"]["answer"]
        baseline_eval = record["baseline_medgemma"]["evaluation"]
    else:
        print(f"[{qid}] Baseline retry...", flush=True)
        try:
            baseline_answer = generate_baseline(question)
            baseline_eval = evaluate_answer_with_pipeline(question, baseline_answer)
        except Exception as exc:
            baseline_answer = ""
            baseline_eval = {"claims_summary": {}, "confidence": {}, "error": str(exc)}
            print(f"[{qid}] Baseline error: {exc}", flush=True)

    record = {
        "question_id": qid,
        "question": question,
        "halluguard": {"answer": hallu_answer, "evaluation": hallu_eval, "raw": hallu_raw},
        "baseline_medgemma": {"answer": baseline_answer, "evaluation": baseline_eval},
        "duration_seconds": round(time.time() - started, 2),
    }
    return record


def main() -> None:
    records, rows = load_existing()
    existing_by_qid = {record.get("question_id"): record for record in records}
    for index, question in enumerate(QUESTIONS, start=1):
        qid = f"Q{index:02d}"
        existing = existing_by_qid.get(qid)
        if existing and method_ok(existing, "halluguard") and method_ok(existing, "baseline_medgemma"):
            print(f"[{qid}] complete; skipping", flush=True)
            continue
        record = run_one(qid, question, existing)
        new_rows = [
            compact_method_row(qid, "halluguard_med", question, record["halluguard"]["answer"], record["halluguard"]["evaluation"]),
            compact_method_row(qid, "baseline_medgemma", question, record["baseline_medgemma"]["answer"], record["baseline_medgemma"]["evaluation"]),
        ]
        records = replace_record(records, record)
        records.sort(key=lambda item: item.get("question_id", ""))
        rows = replace_rows(rows, new_rows, qid)
        rows.sort(key=lambda item: (item.get("question_id", ""), item.get("method", "")))
        save_outputs(records, rows, aggregate(rows))
        print(f"[{qid}] saved; ok_h={method_ok(record, 'halluguard')} ok_b={method_ok(record, 'baseline_medgemma')}", flush=True)

    print(json.dumps(aggregate(rows), indent=2), flush=True)
    print(f"Saved: {OUTPUT_DIR}", flush=True)


if __name__ == "__main__":
    main()
