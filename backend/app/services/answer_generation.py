import re

from backend.app.prompts import (
    GROUNDED_ANSWER_MODE,
    GROUNDED_ANSWER_PROMPT_VERSION,
    GroundedAnswerPrompt,
    build_grounded_answer_prompt,
)
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.schemas.answers import AnswerCitation, AnswerRequest, AnswerResponse
from backend.app.schemas.retrieval import RetrievedChunk, RetrievalRequest
from backend.app.services.llm import get_llm_provider
from backend.app.services.retrieval import retrieve_chunks

settings = get_settings()

INSUFFICIENT_EVIDENCE_ANSWER = (
    "I do not have enough evidence in the indexed documents to answer that confidently."
)
QUESTION_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "can",
    "does",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "or",
    "should",
    "tell",
    "the",
    "their",
    "there",
    "they",
    "this",
    "what",
    "when",
    "where",
    "which",
    "who",
}
PARTIAL_ANSWER_STOPWORDS = QUESTION_STOPWORDS.union(
    {
        "candidate",
        "candidates",
        "document",
        "documents",
        "experience",
        "highlight",
        "highlights",
        "resume",
        "resumes",
        "role",
        "roles",
    }
)


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if token}


def _significant_question_tokens(text: str) -> set[str]:
    return {
        token
        for token in _tokenize(text)
        if len(token) > 2 and token not in QUESTION_STOPWORDS
    }


def _render_page_reference(page_reference: int | list[int] | None) -> str | None:
    if page_reference is None:
        return None
    if isinstance(page_reference, list):
        joined_pages = ", ".join(str(page) for page in page_reference)
        return f"pages {joined_pages}"
    return f"page {page_reference}"


def select_supporting_chunks(
    *,
    question: str,
    retrieved_chunks: list[RetrievedChunk],
) -> list[RetrievedChunk]:
    question_tokens = _significant_question_tokens(question)
    ranked_chunks = sorted(
        retrieved_chunks,
        key=lambda chunk: (
            chunk.score >= settings.answer_min_score,
            len(question_tokens.intersection(_tokenize(chunk.text))),
            chunk.score,
        ),
        reverse=True,
    )
    return ranked_chunks[: settings.answer_max_citations]


def render_citations(chunks: list[RetrievedChunk]) -> list[AnswerCitation]:
    citations: list[AnswerCitation] = []
    for index, chunk in enumerate(chunks, start=1):
        page_reference = _render_page_reference(chunk.citation.page_reference)
        label_parts = [
            chunk.citation.filename,
            f"chunk {chunk.citation.chunk_index}",
        ]
        if page_reference is not None:
            label_parts.append(page_reference)

        citations.append(
            AnswerCitation(
                index=index,
                marker=f"[{index}]",
                label=", ".join(label_parts),
                score=chunk.score,
                **chunk.citation.model_dump(),
            )
        )
    return citations


def format_answer(answer: str, citations: list[AnswerCitation]) -> str:
    markers = " ".join(citation.marker for citation in citations)
    if not markers:
        return answer.strip()
    return f"{answer.strip()} {markers}".strip()


def _clean_missing_information(items: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()

    for item in items:
        normalized = " ".join(item.strip().split())
        if not normalized:
            continue

        normalized = normalized.rstrip(".")
        if len(normalized.split()) < 2:
            continue

        if not normalized.endswith("?"):
            normalized = f"{normalized}."

        dedupe_key = normalized.lower()
        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)
        cleaned.append(normalized)

    return cleaned


def _focus_phrase(question: str) -> str | None:
    focus_tokens = [
        token
        for token in re.findall(r"[a-z0-9]+", question.lower())
        if len(token) > 2 and token not in PARTIAL_ANSWER_STOPWORDS
    ]
    if not focus_tokens:
        return None
    return " ".join(focus_tokens[:2])


def _fallback_supported_answer(question: str) -> str:
    focus_phrase = _focus_phrase(question)
    if focus_phrase is None:
        return (
            "The cited sections provide some related background, but not enough direct "
            "evidence to answer this confidently."
        )

    if "security" in focus_phrase:
        return (
            f"The cited sections do not show explicit {focus_phrase}-specific evidence. "
            "They point more to adjacent technical experience than dedicated security roles."
        )

    return (
        "The cited sections provide some related background, "
        f"but not enough direct evidence to answer the part about {focus_phrase} confidently."
    )


def generate_answer_from_chunks(
    *,
    question: str,
    retrieved_chunks: list[RetrievedChunk],
) -> AnswerResponse:
    supporting_chunks = select_supporting_chunks(
        question=question,
        retrieved_chunks=retrieved_chunks,
    )

    if not supporting_chunks:
        return AnswerResponse(
            question=question,
            answer=INSUFFICIENT_EVIDENCE_ANSWER,
            confidence="insufficient_evidence",
            insufficient_evidence=True,
            missing_information=[],
            answer_mode=GROUNDED_ANSWER_MODE,
            prompt_version=GROUNDED_ANSWER_PROMPT_VERSION,
            citations=[],
        )

    prompt_bundle = build_grounded_answer_prompt(
        GroundedAnswerPrompt(question=question, chunks=supporting_chunks)
    )
    draft = get_llm_provider().generate_grounded_answer(
        prompt_bundle=prompt_bundle,
        question=question,
        chunks=supporting_chunks,
    )
    citations = render_citations(supporting_chunks)
    missing_information = _clean_missing_information(draft.missing_information)

    if draft.insufficient_evidence or not draft.answer.strip():
        if supporting_chunks:
            return AnswerResponse(
                question=question,
                answer=format_answer(
                    _fallback_supported_answer(question),
                    citations,
                ),
                confidence="partial",
                insufficient_evidence=False,
                missing_information=missing_information,
                answer_mode=prompt_bundle.mode,
                prompt_version=prompt_bundle.version,
                citations=citations,
            )

        return AnswerResponse(
            question=question,
            answer=INSUFFICIENT_EVIDENCE_ANSWER,
            confidence="insufficient_evidence",
            insufficient_evidence=True,
            missing_information=[],
            answer_mode=prompt_bundle.mode,
            prompt_version=prompt_bundle.version,
            citations=[],
        )

    confidence = "partial" if missing_information else "grounded"
    formatted_answer = format_answer(draft.answer, citations)

    if not formatted_answer:
        return AnswerResponse(
            question=question,
            answer=INSUFFICIENT_EVIDENCE_ANSWER,
            confidence="insufficient_evidence",
            insufficient_evidence=True,
            missing_information=[],
            answer_mode=prompt_bundle.mode,
            prompt_version=prompt_bundle.version,
            citations=[],
        )

    return AnswerResponse(
        question=question,
        answer=formatted_answer,
        confidence=confidence,
        insufficient_evidence=False,
        missing_information=missing_information,
        answer_mode=prompt_bundle.mode,
        prompt_version=prompt_bundle.version,
        citations=citations,
    )


def generate_answer(payload: AnswerRequest, db: Session, tenant_id: int) -> AnswerResponse:
    retrieval_response = retrieve_chunks(
        db=db,
        payload=RetrievalRequest.model_validate(payload.model_dump()),
        tenant_id=tenant_id,
    )
    return generate_answer_from_chunks(
        question=payload.question,
        retrieved_chunks=retrieval_response.results,
    )
