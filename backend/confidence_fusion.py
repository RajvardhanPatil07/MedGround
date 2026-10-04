"""
Confidence fusion for HalluGuard-Med safety signals.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

try:
    from .clinical_claims import ClaimVerificationResult
    from .evidence_scoring import EvidenceScore
    from .source_conflicts import SourceConflict
except ImportError:
    from clinical_claims import ClaimVerificationResult
    from evidence_scoring import EvidenceScore
    from source_conflicts import SourceConflict


@dataclass(frozen=True)
class ConfidenceResult:
    score: float
    label: str
    should_answer: bool
    should_refuse: bool
    reasons: list[str]
    breakdown: dict[str, float]
    reliability_score: float
    calibration: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ConfidenceFusion:
    def fuse(
        self,
        rag_score: float | None,
        evidence_scores: list[EvidenceScore],
        conflicts: list[SourceConflict],
        claim_results: list[ClaimVerificationResult],
        imaging_result: dict[str, Any] | None = None,
    ) -> ConfidenceResult:
        reasons: list[str] = []
        rag_signal = float(rag_score or 0.0)
        passed_scores = [score.final_score for score in evidence_scores if score.passed]
        all_scores = [score.final_score for score in evidence_scores]
        mean_evidence = sum(passed_scores or all_scores or [0.0]) / len(passed_scores or all_scores or [1.0])

        if claim_results:
            supported = [item for item in claim_results if item.status == "supported"]
            weak_supported = [item for item in claim_results if item.status == "weak_support"]
            contradicted = [
                item for item in claim_results
                if item.status == "contradicted"
                and item.contradiction_score >= 0.90
                and item.contradiction_score > item.support_score + 0.20
            ]
            soft_contradicted = [
                item for item in claim_results
                if item.status == "contradicted" and item not in contradicted
            ]
            unsupported = [item for item in claim_results if item.status in {"unsupported", "insufficient"}]
            claim_support_ratio = self._weighted_claim_support(claim_results)
            citation_coverage = self._weighted_citation_coverage(claim_results)
        else:
            contradicted = []
            soft_contradicted = []
            unsupported = []
            weak_supported = []
            claim_support_ratio = 0.0
            citation_coverage = 0.0
            reasons.append("no_claims_verified")

        high_conflicts = [conflict for conflict in conflicts if conflict.severity == "high"]
        contradiction_penalty = min(
            1.0,
            (0.4 * len(high_conflicts))
            + (0.15 * (len(conflicts) - len(high_conflicts)))
            + (0.35 * len(contradicted))
            + max([item.contradiction_score for item in claim_results] or [0.0]),
        )

        entity_alignment = self._entity_alignment(evidence_scores)
        source_agreement = self._source_agreement(evidence_scores)
        raw_reliability = (
            (0.20 * rag_signal)
            + (0.22 * mean_evidence)
            + (0.28 * claim_support_ratio)
            + (0.12 * citation_coverage)
            + (0.08 * entity_alignment)
            + (0.10 * source_agreement)
            - (0.30 * contradiction_penalty)
        )
        confidence = self._calibrate(raw_reliability)
        if unsupported:
            confidence = min(confidence, 0.69)
        elif weak_supported:
            confidence = min(confidence, 0.71)
        if contradicted:
            confidence = min(confidence, 0.35)
        elif soft_contradicted:
            confidence = min(confidence, 0.55)
        if citation_coverage <= 0.0 and claim_results:
            confidence = min(confidence, 0.45)
        if rag_signal < 0.40:
            confidence = min(confidence, 0.55)
        confidence = round(confidence, 4)
        breakdown = {
            "rag_signal": round(rag_signal, 4),
            "mean_evidence": round(mean_evidence, 4),
            "weighted_claim_support": round(claim_support_ratio, 4),
            "entailed_citation_coverage": round(citation_coverage, 4),
            "entity_alignment": round(entity_alignment, 4),
            "source_agreement": round(source_agreement, 4),
            "contradiction_penalty": round(contradiction_penalty, 4),
        }
        calibration = {
            "raw_reliability": round(max(0.0, min(raw_reliability, 1.0)), 4),
            "calibrated_reliability": confidence,
            "calibration_intercept": -1.1,
            "calibration_slope": 3.2,
        }

        should_refuse = False
        should_answer = True
        if high_conflicts:
            should_refuse = True
            reasons.append("high_severity_source_conflict")
        if contradicted:
            should_refuse = True
            reasons.append("contradicted_clinical_claim")
        elif soft_contradicted:
            reasons.append("possible_contradiction_needs_review")
        if claim_results and claim_support_ratio < 0.5:
            should_answer = False
            reasons.append("low_claim_support_ratio")
        if mean_evidence < 0.35:
            should_answer = False
            reasons.append("weak_evidence_quality")

        if unsupported:
            reasons.append(f"{len(unsupported)}_unsupported_or_insufficient_claims")
        if weak_supported:
            reasons.append(f"{len(weak_supported)}_weak_support_claims")

        if imaging_result and imaging_result.get("critical"):
            reasons.append("critical_imaging_finding_present")

        if should_refuse:
            label = "unsafe"
            should_answer = False
        elif confidence >= 0.72:
            label = "high"
        elif confidence >= 0.45:
            label = "medium"
        else:
            label = "low"
            should_answer = False

        return ConfidenceResult(
            score=confidence,
            label=label,
            should_answer=should_answer,
            should_refuse=should_refuse,
            reasons=reasons,
            breakdown=breakdown,
            reliability_score=confidence,
            calibration=calibration,
        )

    def _entity_alignment(self, evidence_scores: list[EvidenceScore]) -> float:
        if not evidence_scores:
            return 0.0
        overlaps = [score.entity_overlap for score in evidence_scores]
        if max(overlaps or [0.0]) <= 0.0:
            strong_retrieval = [
                score.retrieval_score
                for score in evidence_scores
                if score.retrieval_score >= 0.75 and score.passed
            ]
            if strong_retrieval:
                return round(min(0.75, sum(strong_retrieval) / len(strong_retrieval)), 4)
        return round(sum(overlaps) / len(evidence_scores), 4)

    def _claim_weight(self, item: ClaimVerificationResult) -> float:
        try:
            return max(0.1, float(getattr(item, "severity_weight", 1.0) or 1.0))
        except (TypeError, ValueError):
            return 1.0

    def _weighted_claim_support(self, claim_results: list[ClaimVerificationResult]) -> float:
        weighted_total = sum(self._claim_weight(item) for item in claim_results)
        if weighted_total <= 0:
            return 0.0
        support = 0.0
        for item in claim_results:
            weight = self._claim_weight(item)
            if item.status == "supported":
                support += weight
            elif item.status == "weak_support":
                support += 0.5 * weight
            else:
                support += max(0.0, min(float(item.support_score or 0.0), 0.35)) * weight
        return round(support / weighted_total, 4)

    def _weighted_citation_coverage(self, claim_results: list[ClaimVerificationResult]) -> float:
        weighted_total = sum(self._claim_weight(item) for item in claim_results)
        if weighted_total <= 0:
            return 0.0
        covered = sum(
            self._claim_weight(item)
            for item in claim_results
            if item.best_citation_id and item.status in {"supported", "weak_support"}
        )
        return round(covered / weighted_total, 4)

    def _source_agreement(self, evidence_scores: list[EvidenceScore]) -> float:
        if not evidence_scores:
            return 0.0
        values = [
            getattr(score, "source_consistency", 1.0) * score.final_score
            for score in evidence_scores
        ]
        return round(sum(values) / len(values), 4)

    def _calibrate(self, raw_score: float) -> float:
        import math

        clipped = max(0.0, min(float(raw_score), 1.0))
        probability = 1.0 / (1.0 + math.exp(-(-1.1 + (3.2 * clipped))))
        return round(max(0.0, min(probability, 1.0)), 4)
