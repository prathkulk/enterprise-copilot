from dataclasses import dataclass

from backend.app.schemas.retrieval import RetrievedChunk

GROUNDED_ANSWER_PROMPT_VERSION = "grounded-answer-v2"
GROUNDED_ANSWER_MODE = "structured_json"


@dataclass(frozen=True)
class GroundedAnswerPrompt:
    question: str
    chunks: list[RetrievedChunk]


@dataclass(frozen=True)
class GroundedAnswerPromptBundle:
    version: str
    mode: str
    prompt: str


def _render_page_reference(page_reference: int | list[int] | None) -> str:
    if page_reference is None:
        return "page n/a"
    if isinstance(page_reference, list):
        return f"pages {', '.join(str(page) for page in page_reference)}"
    return f"page {page_reference}"


def build_grounded_answer_prompt(payload: GroundedAnswerPrompt) -> GroundedAnswerPromptBundle:
    source_blocks = []
    for index, chunk in enumerate(payload.chunks, start=1):
        source_blocks.append(
            "\n".join(
                [
                    f"[{index}] file={chunk.citation.filename}",
                    f"collection={chunk.citation.collection_name}",
                    f"chunk_index={chunk.citation.chunk_index}",
                    f"location={_render_page_reference(chunk.citation.page_reference)}",
                    f"score={chunk.score}",
                    "content:",
                    chunk.text,
                ]
            )
        )

    sources = "\n\n".join(source_blocks)
    prompt = (
        "You are an enterprise knowledge assistant.\n"
        "Rules:\n"
        "1. Answer only from the provided context.\n"
        "2. If the context does not support a claim, do not infer or fabricate it.\n"
        "3. If the question is only partially answerable, answer the supported portion and list the missing information separately.\n"
        "4. If the question is not answerable from context, set insufficient_evidence=true.\n"
        "5. Use a concise, professional enterprise tone.\n"
        "6. Do not include citation markers like [1] in the answer text.\n"
        "7. Do not mention missing_information inside the answer field.\n"
        "8. Keep missing_information useful, specific, and short. Avoid single-word fragments.\n"
        "9. Return valid JSON only.\n\n"
        "Return this JSON schema:\n"
        "{\n"
        '  "answer": "string",\n'
        '  "insufficient_evidence": true | false,\n'
        '  "missing_information": ["string", "..."]\n'
        "}\n\n"
        f"Question:\n{payload.question}\n\n"
        f"Context:\n{sources}\n"
    )
    return GroundedAnswerPromptBundle(
        version=GROUNDED_ANSWER_PROMPT_VERSION,
        mode=GROUNDED_ANSWER_MODE,
        prompt=prompt,
    )
