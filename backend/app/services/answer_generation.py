import re

from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.schemas.answers import AnswerCitation, AnswerRequest, AnswerResponse
from backend.app.schemas.retrieval import RetrievedChunk, RetrievalRequest
from backend.app.services.llm import get_llm_provider
from backend.app.services.retrieval import retrieve_chunks

settings = get_settings()
llm_provider = get_llm_provider()

INSUFFICIENT_EVIDENCE_ANSWER = (
    "I do not have enough evidence in the indexed documents to answer that confidently."
)


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if token}


def _render_page_reference(page_reference: int | list[int] | None) -> str | None:
    if page_reference is None:
        return None
    if isinstance(page_reference, list):
        joined_pages = ", ".join(str(page) for page in page_reference)
        return f"pages {joined_pages}"
    return f"page {page_reference}"


def build_answer_prompt(question: str, chunks: list[RetrievedChunk]) -> str:
    source_blocks = []
    for index, chunk in enumerate(chunks, start=1):
        page_reference = _render_page_reference(chunk.citation.page_reference) or "page n/a"
        source_blocks.append(
            "\n".join(
                [
                    f"[{index}] {chunk.citation.filename}",
                    f"collection: {chunk.citation.collection_name}",
                    f"chunk: {chunk.citation.chunk_index}",
                    f"location: {page_reference}",
                    f"score: {chunk.score}",
                    chunk.text,
                ]
            )
        )

    sources = "\n\n".join(source_blocks)
    return (
        "You are a grounded answer generator. Use only the provided sources. "
        "If the evidence is weak or missing, say that there is insufficient evidence.\n\n"
        f"Question: {question}\n\n"
        f"Sources:\n{sources}"
    )


def _supports_question(question_tokens: set[str], chunk: RetrievedChunk) -> bool:
    chunk_tokens = _tokenize(chunk.text)
    overlap = question_tokens.intersection(chunk_tokens)
    return chunk.score >= settings.answer_min_score and len(overlap) >= 2


def select_supporting_chunks(
    *,
    question: str,
    retrieved_chunks: list[RetrievedChunk],
) -> list[RetrievedChunk]:
    question_tokens = _tokenize(question)
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


def format_answer(sections: list[str], citations: list[AnswerCitation]) -> str:
    formatted_sections = [
        f"{section.rstrip()} {citation.marker}"
        for section, citation in zip(sections, citations, strict=False)
    ]
    return " ".join(formatted_sections).strip()


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
            citations=[],
        )

    prompt = build_answer_prompt(question, supporting_chunks)
    sections = llm_provider.generate_answer_sections(
        prompt=prompt,
        question=question,
        chunks=supporting_chunks,
    )
    citations = render_citations(supporting_chunks)
    formatted_answer = format_answer(sections, citations)

    if not formatted_answer:
        return AnswerResponse(
            question=question,
            answer=INSUFFICIENT_EVIDENCE_ANSWER,
            confidence="insufficient_evidence",
            insufficient_evidence=True,
            citations=[],
        )

    return AnswerResponse(
        question=question,
        answer=formatted_answer,
        confidence="grounded",
        insufficient_evidence=False,
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
