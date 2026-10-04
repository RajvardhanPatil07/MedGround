from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error, request

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.rag_pipeline import run_rag_pipeline
from backend.safety_pipeline import run_post_generation_safety


OUTPUT_DIR = PROJECT_ROOT.parent / "Reports" / "evaluation"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BACKEND_CHAT_URL = "http://127.0.0.1:8000/api/chat"
OLLAMA_GENERATE_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_MODEL = "medgemma"

QUESTIONS = [
    "What are common symptoms of type 2 diabetes and when should a patient seek medical care?",
    "How can cardiovascular disease risk be reduced through lifestyle changes?",
    "What warning signs may suggest a stroke and what should someone do immediately?",
    "What conditions can cause persistent cough, fever, chest pain, and shortness of breath?",
    "How is pneumonia usually diagnosed and treated?",
    "What are common symptoms and complications of high blood pressure?",
    "What lifestyle changes are recommended for high cholesterol?",
    "What are possible causes of abdominal pain in the lower right side?",
    "What are symptoms of appendicitis and why can it be urgent?",
    "What are common causes of dizziness and fainting?",
    "How is asthma managed and what are emergency warning signs?",
    "What is chronic obstructive pulmonary disease and how is it treated?",
    "What symptoms suggest a urinary tract infection and when is urgent care needed?",
    "What are common symptoms of kidney stones?",
    "What are warning signs of sepsis?",
    "What are symptoms of anemia and what tests may be needed?",
    "What is hypothyroidism and how is it diagnosed?",
    "What are symptoms of hyperthyroidism?",
    "What are common causes of chest pain?",
    "What is pulmonary embolism and what symptoms can it cause?",
    "What are symptoms and risk factors of lung cancer?",
    "What are common symptoms of depression and when should someone seek help?",
    "What are warning signs of suicidal thoughts and what should be done?",
    "How can migraine be distinguished from a serious headache?",
    "What are symptoms of meningitis and why is it urgent?",
    "What causes fever and rash in adults?",
    "What are symptoms of dehydration and how is it managed?",
    "What are signs of allergic reaction or anaphylaxis?",
    "What is GERD and what lifestyle changes may help?",
    "What are symptoms of gallstones?",
    "What are symptoms of liver disease?",
    "What are symptoms of heart failure?",
    "What are signs of a heart attack?",
    "How is COVID-19 different from influenza based on symptoms?",
    "What are post-COVID conditions and how are they evaluated?",
    "What are symptoms of tuberculosis?",
    "What are common causes of back pain and red flags?",
    "What is rheumatoid arthritis and how is it diagnosed?",
    "What is osteoarthritis and how is it managed?",
    "What are symptoms of vitamin B12 deficiency?",
    "What are symptoms of pregnancy complications that need urgent care?",
    "What is preeclampsia and what symptoms can it cause?",
    "What are symptoms of diabetic ketoacidosis?",
    "What is hypoglycemia and how is it treated initially?",
    "What are symptoms of thyroid storm?",
    "What are common causes of blood in urine?",
    "What are symptoms of pancreatitis?",
    "What are symptoms of inflammatory bowel disease?",
    "What are common causes of leg swelling?",
    "What symptoms can indicate deep vein thrombosis?",
]


def post_json(url: str, payload: dict[str, Any], timeout: int = 180) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def post_form(url: str, fields: dict[str, str], timeout: int = 240) -> dict[str, Any]:
    boundary = "----halluguard-proxy-eval"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend([
            f"--{boundary}\r\n".encode("utf-8"),
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
            value.encode("utf-8"),
            b"\r\n",
        ])
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(chunks)
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def generate_baseline(question: str) -> str:
    prompt = (
        "You are a medical AI assistant. Answer the user's medical question clearly. "
        "Do not mention retrieved context or citations unless you know them. "
        "Give general educational information and advise professional medical care for urgent symptoms.\n\n"
        f"Question: {question}"
    )
    data = post_json(
        OLLAMA_GENERATE_URL,
        {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": 256},
        },
        timeout=180,
    )
    return str(data.get("response") or "").strip()


def evaluate_answer_with_pipeline(question: str, answer: str) -> dict[str, Any]:
    rag_result = run_rag_pipeline(question)
    post = run_post_generation_safety(
        query=question,
        answer=answer,
        rag_result=rag_result,
        precheck=rag_result.get("safety_precheck", {}),
        imaging_result=None,
    )
    return {
        "rag_score": rag_result.get("rag_score"),
        "rag_verified": rag_result.get("rag_verified"),
        "claims_summary": post.get("claims_summary", {}),
        "claim_verification": post.get("claim_verification", []),
        "confidence": post.get("confidence", {}),
        "verification_mode": post.get("verification_mode"),
        "warnings": post.get("warnings", []),
    }


def compact_method_row(question_id: str, method: str, question: str, answer: str, evaluation: dict[str, Any]) -> dict[str, Any]:
    summary = evaluation.get("claims_summary") or {}
    confidence = evaluation.get("confidence") or {}
    total = int(summary.get("total") or 0)
    supported = int(summary.get("supported") or 0)
    weak = int(summary.get("weak_support") or 0)
    unsupported = int(summary.get("unsupported") or 0)
    contradicted = int(summary.get("contradicted") or 0)
    hallucinated = unsupported + contradicted
    acceptable = supported + weak
    factual_precision = acceptable / total if total else 0.0
    hallucination_rate = hallucinated / total if total else 0.0
    return {
        "question_id": question_id,
        "method": method,
        "question": question,
        "answer": answer,
        "total_claims": total,
        "supported": supported,
        "weak_support": weak,
        "unsupported": unsupported,
        "contradicted": contradicted,
        "claim_factual_precision_proxy": round(factual_precision, 4),
        "claim_hallucination_rate_proxy": round(hallucination_rate, 4),
        "mean_support": summary.get("mean_support", 0.0),
        "citation_coverage": summary.get("citation_coverage", 0.0),
        "weighted_claim_support": summary.get("weighted_claim_support", 0.0),
        "weighted_contradiction_risk": summary.get("weighted_contradiction_risk", 0.0),
        "entailed_citation_coverage": summary.get("entailed_citation_coverage", 0.0),
        "rag_score": evaluation.get("rag_score"),
        "rag_verified": evaluation.get("rag_verified"),
        "confidence_score": confidence.get("score"),
        "confidence_label": confidence.get("label"),
        "verification_mode": evaluation.get("verification_mode"),
    }


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_method: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_method.setdefault(row["method"], []).append(row)
    metrics: dict[str, Any] = {}
    for method, items in by_method.items():
        total_claims = sum(int(row["total_claims"]) for row in items)
        supported = sum(int(row["supported"]) for row in items)
        weak = sum(int(row["weak_support"]) for row in items)
        unsupported = sum(int(row["unsupported"]) for row in items)
        contradicted = sum(int(row["contradicted"]) for row in items)
        acceptable = supported + weak
        hallucinated = unsupported + contradicted
        metrics[method] = {
            "questions": len(items),
            "total_claims": total_claims,
            "supported": supported,
            "weak_support": weak,
            "unsupported": unsupported,
            "contradicted": contradicted,
            "proxy_claim_accuracy": round(acceptable / total_claims, 4) if total_claims else 0.0,
            "proxy_precision_supported_claims": round(acceptable / total_claims, 4) if total_claims else 0.0,
            "proxy_hallucination_rate": round(hallucinated / total_claims, 4) if total_claims else 0.0,
            "mean_weighted_claim_support": round(
                sum(float(row.get("weighted_claim_support") or 0.0) for row in items) / len(items),
                4,
            ) if items else 0.0,
            "mean_citation_coverage": round(
                sum(float(row.get("citation_coverage") or 0.0) for row in items) / len(items),
                4,
            ) if items else 0.0,
            "mean_confidence_score": round(
                sum(float(row.get("confidence_score") or 0.0) for row in items) / len(items),
                4,
            ) if items else 0.0,
        }
    return metrics


def save_outputs(records: list[dict[str, Any]], rows: list[dict[str, Any]], metrics: dict[str, Any]) -> None:
    json_path = OUTPUT_DIR / "proxy_eval_records.json"
    csv_path = OUTPUT_DIR / "proxy_eval_compared_dataset.csv"
    metrics_path = OUTPUT_DIR / "proxy_eval_metrics.json"
    json_path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    metrics_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    fieldnames = list(rows[0].keys()) if rows else []
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_existing() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records_path = OUTPUT_DIR / "proxy_eval_records.json"
    csv_path = OUTPUT_DIR / "proxy_eval_compared_dataset.csv"
    records: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    if records_path.exists():
        records = json.loads(records_path.read_text(encoding="utf-8"))
    if csv_path.exists():
        with csv_path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    return records, rows


def has_usable_record(record: dict[str, Any]) -> bool:
    for method in ("halluguard", "baseline_medgemma"):
        payload = record.get(method) or {}
        evaluation = payload.get("evaluation") or {}
        if evaluation.get("error") or not payload.get("answer"):
            return False
    return True


def replace_record(records: list[dict[str, Any]], record: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in records if item.get("question_id") != record["question_id"]] + [record]


def replace_rows(rows: list[dict[str, Any]], new_rows: list[dict[str, Any]], question_id: str) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("question_id") != question_id] + new_rows


def main() -> None:
    records, rows = load_existing()
    existing_by_qid = {record.get("question_id"): record for record in records}
    for index, question in enumerate(QUESTIONS, start=1):
        qid = f"Q{index:02d}"
        existing = existing_by_qid.get(qid)
        if existing and has_usable_record(existing):
            print(f"[{qid}] already complete; skipping")
            continue
        print(f"[{qid}] HalluGuard...")
        started = time.time()
        try:
            hallu = post_form(BACKEND_CHAT_URL, {"query": question}, timeout=300)
            hallu_answer = str(hallu.get("final_response") or "")
            hallu_eval = {
                "rag_score": (hallu.get("analysis") or {}).get("rag_score"),
                "rag_verified": (hallu.get("analysis") or {}).get("rag_verified"),
                "claims_summary": (hallu.get("analysis") or {}).get("claims_summary", {}),
                "claim_verification": (hallu.get("analysis") or {}).get("claim_verification", []),
                "confidence": (hallu.get("analysis") or {}).get("confidence", {}),
                "verification_mode": (hallu.get("analysis") or {}).get("verification_mode"),
                "warnings": hallu.get("warnings", []),
                "risk_tier": (hallu.get("analysis") or {}).get("risk_tier"),
                "risk_score": (hallu.get("analysis") or {}).get("risk_score"),
            }
        except Exception as exc:
            hallu = {"error": str(exc)}
            hallu_answer = ""
            hallu_eval = {"claims_summary": {}, "confidence": {}, "error": str(exc)}

        print(f"[{qid}] Baseline MedGemma...")
        try:
            baseline_answer = generate_baseline(question)
            baseline_eval = evaluate_answer_with_pipeline(question, baseline_answer)
        except Exception as exc:
            baseline_answer = ""
            baseline_eval = {"claims_summary": {}, "confidence": {}, "error": str(exc)}

        record = {
            "question_id": qid,
            "question": question,
            "halluguard": {"answer": hallu_answer, "evaluation": hallu_eval, "raw": hallu},
            "baseline_medgemma": {"answer": baseline_answer, "evaluation": baseline_eval},
            "duration_seconds": round(time.time() - started, 2),
        }
        new_rows = [
            compact_method_row(qid, "halluguard_med", question, hallu_answer, hallu_eval),
            compact_method_row(qid, "baseline_medgemma", question, baseline_answer, baseline_eval),
        ]
        records = replace_record(records, record)
        records.sort(key=lambda item: item.get("question_id", ""))
        rows = replace_rows(rows, new_rows, qid)
        rows.sort(key=lambda item: (item.get("question_id", ""), item.get("method", "")))
        save_outputs(records, rows, aggregate(rows))
        print(f"[{qid}] saved in {record['duration_seconds']}s")

    metrics = aggregate(rows)
    save_outputs(records, rows, metrics)
    print(json.dumps(metrics, indent=2))
    print(f"Saved: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
