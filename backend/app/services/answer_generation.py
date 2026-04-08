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


def _supports_question(question_tokens: set[str], chunk: RetrievedChunk) -> bool:
    chunk_tokens = _tokenize(chunk.text)
    overlap = question_tokens.intersection(chunk_tokens)
    return chunk.score >= settings.answer_min_score and len(overlap) >= 2


def select_supporting_chunks(
    *,
    question: str,
    retrieved_chunks: list[RetrievedChunk],
) -> list[RetrievedChunk]:
    question_tokens = _significant_question_tokens(question)
    return [
        chunk
        for chunk in retrieved_chunks
        if _supports_question(question_tokens, chunk)
    ][: settings.answer_max_citations]


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


def _append_missing_information(answer: str, missing_information: list[str]) -> str:
    if not missing_information:
        return answer.strip()
    suffix = " ".join(missing_information)
    return f"{answer.strip()} {suffix}".strip()


def _derive_missing_information(
    *, question: str, supporting_chunks: list[RetrievedChunk]
) -> list[str]:
    question_tokens = _significant_question_tokens(question)
    supported_tokens = set()
    for chunk in supporting_chunks:
        supported_tokens.update(_tokenize(chunk.text))

    missing_tokens = sorted(question_tokens - supported_tokens)
    if not missing_tokens:
        return []

    return [
        "The indexed documents do not specify details about: "
        + ", ".join(missing_tokens[:5])
        + "."
    ]


def _fallback_supported_answer(supporting_chunks: list[RetrievedChunk]) -> str:
    if not supporting_chunks:
        return INSUFFICIENT_EVIDENCE_ANSWER
    return supporting_chunks[0].text.strip()


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
    fallback_missing_information = _derive_missing_information(
        question=question,
        supporting_chunks=supporting_chunks,
    )

    if draft.insufficient_evidence or not draft.answer.strip():
        if fallback_missing_information:
            guarded_answer = _append_missing_information(
                _fallback_supported_answer(supporting_chunks),
                fallback_missing_information,
            )
            return AnswerResponse(
                question=question,
                answer=format_answer(guarded_answer, citations),
                confidence="partial",
                insufficient_evidence=False,
                missing_information=fallback_missing_information,
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

    missing_information = draft.missing_information or fallback_missing_information
    confidence = "partial" if missing_information else "grounded"
    guarded_answer = _append_missing_information(draft.answer, missing_information)
    formatted_answer = format_answer(guarded_answer, citations)

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


def generate_answer(payload: AnswerRequest, db: Session) -> AnswerResponse:
    retrieval_response = retrieve_chunks(
        db=db,
        payload=RetrievalRequest(
            question=payload.question,
            collection_id=payload.collection_id,
            document_id=payload.document_id,
            top_k=payload.top_k,
        ),
    )
    return generate_answer_from_chunks(
        question=payload.question,
        retrieved_chunks=retrieval_response.results,
    )
