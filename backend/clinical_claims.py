"""
Clinical claim extraction and evidence verification.
"""

from __future__ import annotations

import re
import os
from dataclasses import asdict, dataclass, field
from typing import Any

try:
    from .medical_entities import MedicalEntity, MedicalEntityExtractor, entities_to_dicts
    from .nli_verifier import (
        NLI_CONTRADICTION_THRESHOLD,
        NLI_SUPPORT_THRESHOLD,
        NliUnavailableError,
        disabled_metadata,
        get_nli_status,
        verify_claim_against_evidence,
    )
    from .structured_log import log_event
except ImportError:
    from medical_entities import MedicalEntity, MedicalEntityExtractor, entities_to_dicts
    from nli_verifier import (
        NLI_CONTRADICTION_THRESHOLD,
        NLI_SUPPORT_THRESHOLD,
        NliUnavailableError,
        disabled_metadata,
        get_nli_status,
        verify_claim_against_evidence,
    )
    from structured_log import log_event


MAX_CLAIMS = int(os.getenv("MAX_CLAIMS", "10"))
MAX_EVIDENCE_PER_CLAIM = 4
MAX_EVIDENCE_WINDOWS_PER_CLAIM = 3
MAX_EVIDENCE_WINDOW_CHARS = 520
ENTAILMENT_THRESHOLD = NLI_SUPPORT_THRESHOLD
CONTRADICTION_THRESHOLD = NLI_CONTRADICTION_THRESHOLD
CONTRADICTION_MARGIN = 0.10
SUPPORTED_THRESHOLD = 0.60
WEAK_SUPPORT_THRESHOLD = 0.40
UNSUPPORTED_THRESHOLD = WEAK_SUPPORT_THRESHOLD
LEXICAL_SUPPORT_THRESHOLD = 0.46

CLAIM_SEVERITY_WEIGHTS = {
    "emergency_triage": 2.0,
    "diagnosis": 1.8,
    "medication_or_dosage": 1.8,
    "treatment": 1.6,
    "contraindication_or_adverse_effect": 1.5,
    "risk_or_complication": 1.4,
    "prognosis": 1.2,
    "symptom": 1.0,
    "general": 0.7,
}

UNSAFE_PHRASES = [
    "guaranteed to cure",
    "always works",
    "never fails",
    "stop taking your medication",
    "no need to consult",
    "safe for everyone",
    "100% effective",
]

LOW_VALUE_IMAGE_CLAIM_PATTERNS = [
    r"\bclear visualization of the lungs\b",
    r"\bclear visualization of .*mediastinum\b",
    r"\bdoes not show any other specific findings\b",
    r"\bwould suggest other diagnoses\b",
]

VERIFICATION_ENGINE = "deberta_v3_mnli_with_overlap_fallback"


def classify_support_status(support_score: float) -> str:
    if support_score >= SUPPORTED_THRESHOLD:
        return "supported"
    if support_score >= WEAK_SUPPORT_THRESHOLD:
        return "weak_support"
    return "unsupported"

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have",
    "how", "if", "in", "is", "it", "its", "may", "of", "on", "or", "that", "the",
    "their", "this", "to", "used", "uses", "with", "your", "you",
    "given", "during", "typically", "usually", "considered", "requiring", "standard",
    "overview", "point", "points", "evidence", "supports", "important", "include",
    "including", "based", "retrieved", "listed", "noted", "clear", "unclear",
    "warning", "sign", "signs", "seek", "care", "someone", "overview", "key",
}

GENERIC_CLAIM_PATTERNS = [
    r"\b(common symptom|numerous potential causes|can vary significantly)\b",
    r"\b(differential diagnosis .* broad|prompt evaluation is necessary)\b",
    r"\b(crucial to differentiate|appropriate care)\b",
    r"\b(use this output|decision support|not a final diagnosis)\b",
]

SAFETY_OR_POLICY_CLAIM_PATTERNS = [
    r"\burgent safety warning\b",
    r"\bdo not rely on\b.*\b(ai|assistant|model|response|answer|output)\b",
    r"\b(ai|assistant|model|response|answer|output)\b.*\bdoes not replace\b",
    r"\bnot a final diagnosis\b",
    r"\bdecision support only\b",
    r"\bnot a substitute for\b.*\bmedical advice\b",
    r"\bprofessional medical advice\b",
    r"\bconsult (?:a |your )?(?:licensed )?(?:clinician|doctor|physician|health ?care provider|medical professional)\b",
    r"\btalk to (?:a |your )?(?:clinician|doctor|physician|health ?care provider)\b",
    r"\bplease (?:consult|seek|talk to)\b",
    r"\bseek (?:urgent|emergency|immediate) medical care\b",
    r"\bcall (?:911|your local emergency number|emergency services)\b",
]

DOMAIN_PHRASES = (
    "a1c",
    "appendicitis",
    "appendix",
    "blockage",
    "medical emergency",
    "removing the appendix",
    "removal of the appendix",
    "appendectomy",
    "treatment",
    "anti-d",
    "anti d",
    "rh immune globulin",
    "rh incompatibility",
    "rh-negative",
    "rh negative",
    "rh-positive",
    "rh positive",
    "blood glucose",
    "blood sugar",
    "prediabetes",
    "diabetes",
    "pregnancy",
    "injection",
)

CLAIM_TYPE_PATTERNS = [
    ("emergency_triage", r"\b(emergency|urgent|call\s+911|go to (?:the )?er|seek emergency|immediate medical)\b"),
    ("medication_or_dosage", r"\b(dose|dosage|mg|milligram|tablet|capsule|insulin|antibiotic|medication|medicine|drug|prescription)\b"),
    ("contraindication_or_adverse_effect", r"\b(side effect|adverse|contraindicat|avoid|allergic|interaction|harmful|toxicity|overdose)\b"),
    ("diagnosis", r"\b(diagnos|diagnosis|diagnosed|indicates|suggests|consistent with|rules out|rule out)\b"),
    ("treatment", r"\b(treat|treatment|therapy|surgery|procedure|manage|management|lifestyle|exercise|diet)\b"),
    ("risk_or_complication", r"\b(risk|complication|can lead to|can cause|may cause|worsen|progression|rupture|stroke|attack)\b"),
    ("prognosis", r"\b(prognosis|outlook|recover|recovery|long[- ]term|survival|prevent or delay)\b"),
    ("symptom", r"\b(symptom|sign|pain|fever|cough|nausea|vomit|weakness|shortness of breath|bleeding)\b"),
]


def claim_severity_weight(claim_type: str) -> float:
    return CLAIM_SEVERITY_WEIGHTS.get(claim_type, CLAIM_SEVERITY_WEIGHTS["general"])

CONCEPT_SYNONYMS = {
    "rupture": "burst",
    "ruptured": "burst",
    "bursts": "burst",
    "bursting": "burst",
    "inflammation": "inflame",
    "inflamed": "inflame",
    "nauseous": "nausea",
    "sick": "nausea",
    "queasy": "nausea",
    "vomiting": "vomit",
    "vomited": "vomit",
    "throwing": "vomit",
    "throw": "vomit",
    "emesis": "vomit",
    "weakness": "weak",
    "weakened": "weak",
    "diagnosing": "diagnosis",
    "diagnosed": "diagnosis",
    "diagnose": "diagnosis",
    "testing": "test",
    "biomarkers": "biomarker",
    "markers": "marker",
    "ischemia": "ischemic",
    "haemorrhagic": "hemorrhagic",
    "medication": "medicine",
    "medications": "medicine",
    "medicines": "medicine",
    "managed": "manage",
    "managing": "manage",
    "gradually": "time",
    "physical": "activity",
    "exercise": "activity",
}

PHRASE_SYNONYMS = {
    "nausea and vomiting": [
        "nausea and vomiting",
        "nausea or vomiting",
        "feeling sick and throwing up",
        "feeling sick",
        "throwing up",
    ],
    "loss of appetite": [
        "loss of appetite",
        "lost appetite",
        "decreased appetite",
        "poor appetite",
    ],
    "burst appendix": [
        "burst appendix",
        "appendix can burst",
        "ruptured appendix",
        "appendiceal rupture",
    ],
    "inflamed appendix": [
        "inflamed appendix",
        "appendix becomes inflamed",
        "inflammation of the appendix",
    ],
    "blood clot": [
        "blood clot",
        "clot",
        "blocked artery",
        "blockage",
        "thrombus",
        "thrombotic",
    ],
    "bleeding in brain": [
        "bleeding in the brain",
        "brain bleed",
        "bleeding into the brain",
        "hemorrhage in the brain",
        "ruptured blood vessel",
    ],
    "high blood sugar": [
        "high blood sugar",
        "high blood glucose",
        "hyperglycemia",
        "elevated glucose",
    ],
    "low blood sugar": [
        "low blood sugar",
        "low blood glucose",
        "hypoglycemia",
    ],
    "insulin resistance": [
        "insulin resistance",
        "resistant to insulin",
        "body does not use insulin well",
    ],
    "muscle weakness": [
        "muscle weakness",
        "weak muscles",
        "weakness of muscles",
        "fatigable weakness",
    ],
    "double vision": [
        "double vision",
        "diplopia",
    ],
    "drooping eyelid": [
        "drooping eyelid",
        "drooping eyelids",
        "ptosis",
    ],
    "lifestyle changes": [
        "lifestyle changes",
        "diet and exercise",
        "healthy eating and physical activity",
        "eating fewer calories",
        "physically active",
        "physical activity",
    ],
    "diabetes medication": [
        "medication",
        "medications",
        "medicine",
        "medicines",
        "oral medicines",
        "insulin",
        "injectable medicines",
    ],
    "develops over time": [
        "develops gradually",
        "gradually over time",
        "over time",
        "prevent or delay",
    ],
}

GENERIC_CONDITION_TERMS = {
    "cancer",
    "disease",
    "disorder",
    "condition",
    "syndrome",
    "problem",
    "failure",
}

SECTION_LABEL_RE = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:overview|key points?|what the evidence supports|"
    r"safety notes(?: or when to seek medical care)?|warning signs?|symptoms?|"
    r"diagnosis|treatment|emergency care|when to seek care)\s*:?\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ClinicalClaim:
    claim_id: str
    text: str
    claim_type: str
    entities: list[MedicalEntity]
    severity_weight: float = CLAIM_SEVERITY_WEIGHTS["general"]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["entities"] = entities_to_dicts(self.entities)
        return data


@dataclass(frozen=True)
class ClaimVerificationResult:
    claim_id: str
    claim: str
    status: str
    support_score: float
    contradiction_score: float
    best_citation_id: str | None
    best_evidence: str | None
    reason: str
    support_breakdown: dict[str, float] = field(default_factory=dict)
    matched_concepts: list[str] = field(default_factory=list)
    missing_concepts: list[str] = field(default_factory=list)
    nli: dict[str, Any] = field(default_factory=disabled_metadata)
    claim_type: str = "general"
    severity_weight: float = CLAIM_SEVERITY_WEIGHTS["general"]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _split_sentences(text: str) -> list[str]:
    text = re.sub(
        r"(?im)^\s*\*\*(overview|key points|what the evidence supports|safety notes(?: or when to seek medical care)?)\*\*\s*$",
        "",
        text,
    )
    text = re.sub(r"\*\*([^*\n:]{2,45}):\*\*", r"\1:", text)
    text = re.sub(r"\*\*([^*\n]{2,80})\*\*", r"\1", text)
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if re.match(r"^\s*#{1,6}\s+", line):
            continue
        if SECTION_LABEL_RE.match(line):
            continue
        line = re.sub(r"^[\s*\-\u2022\d.)]+", "", line).strip()
        line = re.sub(
            r"^(overview|key points?|warning signs?|symptoms?|diagnosis|treatment|emergency care|when to seek care)\s*:\s*",
            "",
            line,
            flags=re.IGNORECASE,
        ).strip()
        if line:
            lines.append(line)
    joined = " ".join(line for line in lines if line)
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", joined) if part.strip()]


def _content_terms(text: str) -> set[str]:
    terms = set()
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        if len(token) < 2 or token in STOPWORDS:
            continue
        token = CONCEPT_SYNONYMS.get(token, token)
        if token == "appendicitis":
            token = "appendiciti"
        elif token in {"caused", "causes", "causing"}:
            token = "cause"
        elif token in {"preventing", "prevents", "prevented"}:
            token = "prevent"
        elif token in {"draining", "drains", "drained"}:
            token = "drain"
        elif token in {"removing", "removed", "removal"}:
            token = "remove"
        elif token in {"infected", "infection", "infections"}:
            token = "infect"
        elif token in {"inflamed", "inflammation"}:
            token = "inflame"
        elif len(token) > 4 and token.endswith("ies"):
            token = token[:-3] + "y"
        elif len(token) > 4 and token.endswith("s"):
            token = token[:-1]
        terms.add(token)
    return terms


def _concept_terms(text: str) -> set[str]:
    terms = _content_terms(text)
    return {
        term
        for term in terms
        if len(term) >= 4 or term in {"ecg", "ct", "mri", "pe"}
    }


def _lexical_support_score(claim: str, evidence: str) -> float:
    claim_terms = _content_terms(claim)
    if not claim_terms:
        return 0.0
    evidence_terms = _content_terms(evidence)
    overlap = len(claim_terms & evidence_terms) / len(claim_terms)
    phrase_bonus = 0.0
    for phrase in DOMAIN_PHRASES:
        if phrase in claim.lower() and phrase in evidence.lower():
            phrase_bonus += 0.08
    explicit = _explicit_phrase_support(claim, evidence)
    return round(min(1.0, max(overlap + min(0.24, phrase_bonus), explicit)), 4)


def _phrase_present(text: str, phrase: str) -> bool:
    normalized = re.sub(r"\s+", " ", text.lower())
    variants = PHRASE_SYNONYMS.get(phrase, [phrase])
    return any(variant in normalized for variant in variants)


def _explicit_phrase_support(claim: str, evidence: str) -> float:
    claim_lower = claim.lower()
    evidence_lower = evidence.lower()
    best = 0.0
    for phrase, variants in PHRASE_SYNONYMS.items():
        if any(variant in claim_lower for variant in variants) and any(variant in evidence_lower for variant in variants):
            best = max(best, 0.92)
    if re.search(r"\b(symptom|sign|warning sign)s?\b", claim_lower):
        for phrase, variants in PHRASE_SYNONYMS.items():
            if any(variant in claim_lower for variant in variants) and any(variant in evidence_lower for variant in variants):
                best = max(best, 0.95)
    return best


def _concept_coverage(claim: str, evidence: str) -> tuple[float, list[str], list[str]]:
    claim_terms = _concept_terms(claim)
    if not claim_terms:
        return 0.0, [], []
    evidence_terms = _concept_terms(evidence)
    matched = sorted(claim_terms & evidence_terms)
    missing = sorted(claim_terms - evidence_terms)
    phrase_matches = []
    for phrase, variants in PHRASE_SYNONYMS.items():
        if any(variant in claim.lower() for variant in variants) and any(variant in evidence.lower() for variant in variants):
            phrase_matches.append(phrase)
    if phrase_matches:
        matched = sorted(set(matched) | set(phrase_matches))
        missing = [
            term for term in missing
            if term not in {
                "nausea", "vomit", "appetite", "loss", "burst", "inflame",
                "blood", "clot", "blockage", "bleeding", "brain", "sugar",
                "glucose", "insulin", "weak", "muscle", "vision", "eyelid",
                "lifestyle", "activity", "medicine", "manage", "time",
            }
        ]
    coverage = len(matched) / max(1, len(claim_terms))
    if phrase_matches:
        coverage = max(coverage, 0.82)
    return round(min(1.0, coverage), 4), matched, missing


def _semantic_support_score(
    claim: str,
    evidence: str,
    entity_overlap: float,
    concept_coverage: float,
    lexical: float,
) -> float:
    claim_concepts = _concept_terms(claim)
    evidence_concepts = _concept_terms(evidence)
    if not claim_concepts:
        return 0.0
    jaccard = len(claim_concepts & evidence_concepts) / max(1, len(claim_concepts | evidence_concepts))
    phrase_support = _explicit_phrase_support(claim, evidence)
    semantic = max(concept_coverage, lexical * 0.85, phrase_support, min(1.0, entity_overlap + 0.15))
    if jaccard >= 0.22 and concept_coverage >= 0.45:
        semantic = max(semantic, 0.62)
    if entity_overlap >= 0.67 and concept_coverage >= 0.35:
        semantic = max(semantic, 0.70)
    return round(min(1.0, semantic), 4)


def _normalize_condition(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _condition_terms(condition: str) -> set[str]:
    return _content_terms(condition)


def _condition_alignment_score(claim: str, hit: dict[str, Any], primary_conditions: set[str]) -> float:
    condition = _normalize_condition(hit.get("condition"))
    if not condition:
        return 0.5
    claim_terms = _content_terms(claim)
    condition_terms = _condition_terms(condition)
    raw_overlap = claim_terms & condition_terms
    meaningful_overlap = raw_overlap - GENERIC_CONDITION_TERMS
    if condition in primary_conditions:
        if meaningful_overlap:
            return 1.0
        if raw_overlap:
            return 0.0
        return 0.5
    if condition_terms and meaningful_overlap:
        return 0.9
    return 0.0


def _primary_conditions(hits: list[dict[str, Any]]) -> set[str]:
    if not hits:
        return set()
    ranked = sorted(
        hits,
        key=lambda hit: (
            int(hit.get("rank") or 9999),
            -float(hit.get("normalized_score") or hit.get("score") or 0.0),
        ),
    )
    top_condition = _normalize_condition(ranked[0].get("condition"))
    return {top_condition} if top_condition else set()


def _split_evidence_windows(text: str, max_chars: int = MAX_EVIDENCE_WINDOW_CHARS) -> list[str]:
    sentences = _split_sentences(text)
    if not sentences:
        return []
    windows: list[str] = []

    def add_window(value: str) -> None:
        value = re.sub(r"\s+", " ", value).strip()
        if not value:
            return
        if len(value) > max_chars:
            trimmed = value[:max_chars].rsplit(" ", 1)[0].strip()
            value = trimmed or value[:max_chars].strip()
        windows.append(value)

    for sentence in sentences:
        add_window(sentence)
    for index in range(len(sentences) - 1):
        add_window(f"{sentences[index]} {sentences[index + 1]}")

    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            add_window(current)
        current = sentence
    if current:
        add_window(current)

    deduped: list[str] = []
    seen: set[str] = set()
    for window in windows:
        key = re.sub(r"\W+", " ", window.lower()).strip()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(window)
    return deduped[:24]


def _claim_type(text: str) -> str:
    for label, pattern in CLAIM_TYPE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return label
    return "general"


class ClinicalClaimVerifier:
    def __init__(self, extractor: MedicalEntityExtractor | None = None) -> None:
        self.extractor = extractor or MedicalEntityExtractor()
        self.last_verification_mode = "unknown"

    def extract_claims(self, answer: str) -> list[ClinicalClaim]:
        answer = self._strip_citation_appendix(answer)
        claims: list[ClinicalClaim] = []
        for sentence in _split_sentences(answer):
            if len(sentence) < 25:
                continue
            if sentence.lower().startswith(("consult ", "seek ", "talk to ", "please ")):
                continue
            if self._is_low_value_image_claim(sentence):
                continue
            if self._is_safety_or_policy_claim(sentence):
                continue
            if self._is_generic_claim(sentence):
                continue
            if len(_concept_terms(sentence)) < 2:
                continue
            claim_id = f"C{len(claims) + 1}"
            claim_type = _claim_type(sentence)
            claims.append(ClinicalClaim(
                claim_id=claim_id,
                text=sentence,
                claim_type=claim_type,
                severity_weight=claim_severity_weight(claim_type),
                entities=self.extractor.extract(sentence, source=claim_id),
            ))
            if len(claims) >= MAX_CLAIMS:
                break
        return claims

    def _strip_citation_appendix(self, answer: str) -> str:
        return re.split(
            r"\n\s*(?:\*\*)?citations?(?:\*\*)?\s*(?:\n|$)",
            answer,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]

    def _is_low_value_image_claim(self, sentence: str) -> bool:
        return any(re.search(pattern, sentence, re.IGNORECASE) for pattern in LOW_VALUE_IMAGE_CLAIM_PATTERNS)

    def _is_generic_claim(self, sentence: str) -> bool:
        return any(re.search(pattern, sentence, re.IGNORECASE) for pattern in GENERIC_CLAIM_PATTERNS)

    def _is_safety_or_policy_claim(self, sentence: str) -> bool:
        lowered = sentence.lower()
        dangerous_negation = re.search(
            r"\b(?:do not|don't|avoid|no need to)\s+(?:seek|consult|call|go to|contact)\b",
            lowered,
        )
        if dangerous_negation:
            return False
        return any(
            re.search(pattern, sentence, re.IGNORECASE)
            for pattern in SAFETY_OR_POLICY_CLAIM_PATTERNS
        )

    def verify_claims(
        self,
        claims: list[ClinicalClaim],
        evidence_hits: list[dict[str, Any]],
    ) -> list[ClaimVerificationResult]:
        self.last_verification_mode = "nli"
        if not claims:
            self.last_verification_mode = "none"
            return []
        if any(phrase in " ".join(claim.text.lower() for claim in claims) for phrase in UNSAFE_PHRASES):
            self.last_verification_mode = "rule"
            return [
                ClaimVerificationResult(
                    claim_id=claims[0].claim_id,
                    claim=claims[0].text,
                    status="contradicted",
                    support_score=0.0,
                    contradiction_score=1.0,
                    best_citation_id=None,
                    best_evidence=None,
                    reason="unsafe_absolute_medical_claim",
                    support_breakdown={"unsafe_phrase": 1.0},
                    claim_type=claims[0].claim_type,
                    severity_weight=claims[0].severity_weight,
                )
            ]
        if not evidence_hits:
            self.last_verification_mode = "insufficient_evidence"
            return [
                ClaimVerificationResult(
                    claim_id=claim.claim_id,
                    claim=claim.text,
                    status="insufficient",
                    support_score=0.0,
                    contradiction_score=0.0,
                    best_citation_id=None,
                    best_evidence=None,
                    reason="no_evidence_available",
                    support_breakdown={},
                    claim_type=claim.claim_type,
                    severity_weight=claim.severity_weight,
                )
                for claim in claims
            ]

        try:
            # DeBERTa-v3 MNLI replaces the previous rule-based core verifier.
            # If the model cannot load or run, the legacy overlap verifier below
            # is retained as a fail-open server-safe fallback.
            return self._verify_with_nli(claims, evidence_hits)
        except NliUnavailableError as exc:
            self.last_verification_mode = "fallback"
            log_event(
                "nli",
                "claim_verification_fallback",
                "warning",
                error=str(exc),
                fallback="local_lexical_entity_overlap",
            )
            return self._verify_with_overlap(claims, evidence_hits)

    def _best_lexical_support(
        self,
        claim: ClinicalClaim,
        evidence_window: list[dict[str, Any]],
    ) -> tuple[float, dict[str, Any] | None]:
        best_score = 0.0
        best_hit = None
        for hit in evidence_window:
            score = _lexical_support_score(claim.text, hit.get("_premise_text") or hit.get("text", ""))
            if score > best_score:
                best_score = score
                best_hit = hit
        return best_score, best_hit

    def _best_radiology_overlap(
        self,
        claim: ClinicalClaim,
        evidence_window: list[dict[str, Any]],
    ) -> tuple[float, dict[str, Any] | None]:
        best_score = 0.0
        best_hit = None
        for hit in evidence_window:
            if hit.get("source_type") != "radiology_model":
                continue
            hit_entities = self.extractor.extract(
                hit.get("text", ""),
                source=str(hit.get("citation_id", "")),
            )
            overlap = self.extractor.entity_overlap(claim.entities, hit_entities)
            if overlap > best_score:
                best_score = overlap
                best_hit = hit
        return round(best_score, 4), best_hit

    def _score_candidate_support(
        self,
        claim: ClinicalClaim,
        hit: dict[str, Any],
        primary_conditions: set[str],
    ) -> dict[str, Any]:
        citation_id = str(hit.get("citation_id", ""))
        premise_text = str(hit.get("_premise_text") or hit.get("text") or "")
        if not premise_text:
            return {
                "support": 0.0,
                "hit": hit,
                "premise_text": "",
                "breakdown": {},
                "matched": [],
                "missing": [],
            }

        hit_entities = self.extractor.extract(premise_text, source=citation_id)
        overlap = self.extractor.entity_overlap(claim.entities, hit_entities)
        lexical = _lexical_support_score(claim.text, premise_text)
        concept, matched, missing = _concept_coverage(claim.text, premise_text)
        semantic = _semantic_support_score(claim.text, premise_text, overlap, concept, lexical)
        condition_alignment = _condition_alignment_score(claim.text, hit, primary_conditions)
        retrieval = float(hit.get("normalized_score") or hit.get("score") or 0.0)
        retrieval = min(1.0, max(0.0, retrieval))

        support = (
            (0.22 * lexical)
            + (0.30 * concept)
            + (0.18 * semantic)
            + (0.15 * overlap)
            + (0.10 * condition_alignment)
            + (0.05 * retrieval)
        )
        if condition_alignment <= 0.0:
            support = 0.0
        elif semantic >= 0.70 and condition_alignment >= 0.5:
            support = max(support, 0.62)
        elif semantic >= 0.55 and condition_alignment >= 0.5:
            support = max(support, 0.45)
        if concept >= 0.70 and lexical >= 0.45 and condition_alignment >= 0.5:
            support = max(support, 0.68)
        elif concept >= 0.55 and semantic >= 0.62 and condition_alignment >= 0.5:
            support = max(support, 0.60)
        if concept < 0.30 and lexical < 0.35 and semantic < 0.45:
            support *= 0.55

        return {
            "support": round(min(1.0, max(0.0, support)), 4),
            "hit": hit,
            "premise_text": premise_text,
            "breakdown": {
                "lexical": round(lexical, 4),
                "concept_coverage": round(concept, 4),
                "semantic": round(semantic, 4),
                "entity_overlap": round(overlap, 4),
                "condition_alignment": round(condition_alignment, 4),
                "retrieval": round(retrieval, 4),
            },
            "matched": matched,
            "missing": missing[:8],
        }

    def _support_reason(self, breakdown: dict[str, float]) -> str:
        semantic = breakdown.get("semantic", 0.0)
        concept = breakdown.get("concept_coverage", 0.0)
        lexical = breakdown.get("lexical", 0.0)
        overlap = breakdown.get("entity_overlap", 0.0)
        if semantic >= 0.55:
            return "semantic_concept_support"
        if concept >= 0.5:
            return "concept_and_lexical_support"
        if lexical >= overlap:
            return "lexical_evidence_support"
        return "entity_overlap_fallback"

    def _best_local_support(
        self,
        claim: ClinicalClaim,
        candidate_hits: list[dict[str, Any]],
        primary_conditions: set[str],
    ) -> dict[str, Any]:
        best: dict[str, Any] | None = None
        for hit in candidate_hits:
            scored = self._score_candidate_support(claim, hit, primary_conditions)
            if best is None or scored["support"] > best["support"]:
                best = scored
        if best is not None:
            return best
        return {
            "support": 0.0,
            "hit": None,
            "premise_text": None,
            "breakdown": {},
            "matched": [],
            "missing": [],
        }

    def _window_rank_score(
        self,
        claim: ClinicalClaim,
        hit: dict[str, Any],
        window: str,
        primary_conditions: set[str],
    ) -> float:
        clone = dict(hit)
        clone["_premise_text"] = window
        scored = self._score_candidate_support(claim, clone, primary_conditions)
        return float(scored.get("support") or 0.0)

    def _select_evidence_for_claim(
        self,
        claim: ClinicalClaim,
        evidence_hits: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not evidence_hits:
            return []
        primary_conditions = _primary_conditions(evidence_hits)
        scored = []
        for index, hit in enumerate(evidence_hits):
            condition_alignment = _condition_alignment_score(claim.text, hit, primary_conditions)
            if condition_alignment <= 0.0:
                continue
            local = self._score_candidate_support(claim, hit, primary_conditions)
            source_bonus = 0.25 if hit.get("source_type") == "radiology_model" else 0.0
            rank_bonus = max(0.0, 0.10 - (index * 0.01))
            scored.append((float(local["support"]) + source_bonus + rank_bonus, hit))

        ranked = [hit for score, hit in sorted(scored, key=lambda item: item[0], reverse=True) if score > 0]
        candidates = ranked[:MAX_EVIDENCE_PER_CLAIM]
        if not candidates:
            candidates = [
                hit for hit in evidence_hits
                if _condition_alignment_score(claim.text, hit, primary_conditions) > 0
            ][: min(2, MAX_EVIDENCE_PER_CLAIM)]
        if not candidates:
            return []
        windowed: list[dict[str, Any]] = []
        for hit in candidates:
            windows = _split_evidence_windows(hit.get("text", ""))
            if not windows:
                windowed.append(hit)
                continue
            ranked_windows = sorted(
                windows,
                key=lambda window: self._window_rank_score(claim, hit, window, primary_conditions),
                reverse=True,
            )
            for window in ranked_windows[:2]:
                clone = dict(hit)
                clone["_premise_text"] = window
                windowed.append(clone)
                if len(windowed) >= MAX_EVIDENCE_WINDOWS_PER_CLAIM:
                    return windowed
        return windowed[:MAX_EVIDENCE_WINDOWS_PER_CLAIM]

    def _verify_with_overlap(
        self,
        claims: list[ClinicalClaim],
        evidence_hits: list[dict[str, Any]],
    ) -> list[ClaimVerificationResult]:
        results = []
        primary_conditions = _primary_conditions(evidence_hits)
        for claim in claims:
            best_hit = None
            best_support = 0.0
            best_reason = "entity_overlap_fallback"
            best_breakdown: dict[str, float] = {}
            best_matched: list[str] = []
            best_missing: list[str] = []
            candidate_hits = self._select_evidence_for_claim(claim, evidence_hits)
            if not candidate_hits:
                results.append(self._insufficient_result(claim, "no_condition_aligned_evidence"))
                continue
            for hit in candidate_hits:
                scored = self._score_candidate_support(claim, hit, primary_conditions)
                support = float(scored["support"])
                if support > best_support:
                    best_support = support
                    best_hit = hit
                    best_reason = self._support_reason(scored["breakdown"])
                    best_breakdown = scored["breakdown"]
                    best_matched = scored["matched"]
                    best_missing = scored["missing"]
            status = classify_support_status(best_support)
            results.append(ClaimVerificationResult(
                claim_id=claim.claim_id,
                claim=claim.text,
                status=status,
                support_score=round(best_support, 4),
                contradiction_score=0.0,
                best_citation_id=best_hit.get("citation_id") if best_hit else None,
                best_evidence=(best_hit.get("_premise_text") or best_hit.get("text")) if best_hit else None,
                reason=best_reason,
                support_breakdown=best_breakdown,
                matched_concepts=best_matched[:10],
                missing_concepts=best_missing,
                nli={
                    **disabled_metadata(),
                    "verification_mode": "fallback",
                    "fallback_reason": "nli_unavailable",
                },
                claim_type=claim.claim_type,
                severity_weight=claim.severity_weight,
            ))
        return results

    def _verify_with_nli(
        self,
        claims: list[ClinicalClaim],
        evidence_hits: list[dict[str, Any]],
    ) -> list[ClaimVerificationResult]:
        results: list[ClaimVerificationResult] = []
        primary_conditions = _primary_conditions(evidence_hits)
        for claim in claims:
            candidate_hits = self._select_evidence_for_claim(claim, evidence_hits)[:3]
            if not candidate_hits:
                results.append(self._insufficient_result(claim, "no_condition_aligned_evidence"))
                continue
            local_best = self._best_local_support(claim, candidate_hits, primary_conditions)
            local_support = float(local_best.get("support") or 0.0)
            local_breakdown = local_best.get("breakdown") or {}
            local_hit = local_best.get("hit") or {}

            nli_result = verify_claim_against_evidence(
                claim.text,
                candidate_hits,
                max_evidence=3,
            )
            support_score = nli_result.entailment
            contradiction_score = nli_result.contradiction
            best_citation_id = nli_result.citation_id
            best_evidence = nli_result.premise

            if nli_result.label == "supported":
                status = "supported"
                reason = "nli_entailment"
                support_score = max(support_score, min(local_support, 0.95))
                if local_support >= SUPPORTED_THRESHOLD:
                    contradiction_score = min(contradiction_score, 0.35)
            elif nli_result.label == "contradicted":
                condition_alignment = float(local_breakdown.get("condition_alignment") or 0.0)
                concept = float(local_breakdown.get("concept_coverage") or 0.0)
                semantic = float(local_breakdown.get("semantic") or 0.0)
                strong_local_support = (
                    local_support >= 0.68
                    and condition_alignment >= 0.5
                    and (concept >= 0.55 or semantic >= 0.70)
                )
                if strong_local_support and nli_result.contradiction < 0.97:
                    status = "supported" if local_support >= 0.75 and nli_result.contradiction < 0.90 else "weak_support"
                    reason = "local_evidence_softened_nli_contradiction"
                    support_score = max(nli_result.entailment, min(local_support, 0.72))
                    contradiction_score = min(nli_result.contradiction, 0.49)
                    best_citation_id = local_hit.get("citation_id")
                    best_evidence = local_best.get("premise_text")
                else:
                    status = "contradicted"
                    reason = "nli_contradiction"
            else:
                if local_support >= 0.68:
                    status = "supported"
                    reason = "local_evidence_support_overrode_nli_neutral"
                    support_score = max(nli_result.entailment, local_support)
                    contradiction_score = min(nli_result.contradiction, 0.35)
                    best_citation_id = local_hit.get("citation_id")
                    best_evidence = local_best.get("premise_text")
                elif local_support >= WEAK_SUPPORT_THRESHOLD:
                    status = "weak_support"
                    reason = "local_evidence_weak_support_after_nli_neutral"
                    support_score = max(nli_result.entailment, local_support)
                    contradiction_score = min(nli_result.contradiction, 0.45)
                    best_citation_id = local_hit.get("citation_id")
                    best_evidence = local_best.get("premise_text")
                else:
                    status = "unsupported"
                    reason = "nli_neutral_or_unsupported"

            support_breakdown = {
                "nli_entailment": nli_result.entailment,
                "nli_contradiction": nli_result.contradiction,
                "nli_neutral": nli_result.neutral,
                "local_support": round(local_support, 4),
            }
            support_breakdown.update({
                f"local_{key}": float(value)
                for key, value in local_breakdown.items()
            })

            results.append(ClaimVerificationResult(
                claim_id=claim.claim_id,
                claim=claim.text,
                status=status,
                support_score=round(support_score, 4),
                contradiction_score=round(contradiction_score, 4),
                best_citation_id=best_citation_id,
                best_evidence=best_evidence,
                reason=reason,
                support_breakdown=support_breakdown,
                matched_concepts=list(local_best.get("matched") or [])[:10],
                missing_concepts=list(local_best.get("missing") or []),
                nli=nli_result.to_metadata(),
                claim_type=claim.claim_type,
                severity_weight=claim.severity_weight,
            ))
        return results

    def _insufficient_result(self, claim: ClinicalClaim, reason: str) -> ClaimVerificationResult:
        return ClaimVerificationResult(
            claim_id=claim.claim_id,
            claim=claim.text,
            status="insufficient",
            support_score=0.0,
            contradiction_score=0.0,
            best_citation_id=None,
            best_evidence=None,
            reason=reason,
            support_breakdown={},
            claim_type=claim.claim_type,
            severity_weight=claim.severity_weight,
        )


def claims_to_dicts(claims: list[ClinicalClaim]) -> list[dict[str, Any]]:
    return [claim.to_dict() for claim in claims]


def claim_results_to_dicts(results: list[ClaimVerificationResult]) -> list[dict[str, Any]]:
    return [result.to_dict() for result in results]


def get_claim_verification_status() -> dict[str, Any]:
    nli_status = get_nli_status()
    return {
        "nli_available": nli_status.get("available", False),
        "nli_model_loaded": nli_status.get("model_loaded", False),
        "nli_load_error": nli_status.get("load_error"),
        "nli_model": nli_status.get("model"),
        "verification_engine": VERIFICATION_ENGINE,
        "entailment_threshold": nli_status.get("entailment_threshold", ENTAILMENT_THRESHOLD),
        "contradiction_threshold": nli_status.get("contradiction_threshold", CONTRADICTION_THRESHOLD),
    }
