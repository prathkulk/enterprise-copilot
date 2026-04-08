from dataclasses import dataclass

QUERY_REWRITE_PROMPT_VERSION = "query-rewrite-v1"
QUERY_REWRITE_MODE = "structured_json"


@dataclass(frozen=True)
class QueryRewriteHistoryTurn:
    role: str
    content: str


@dataclass(frozen=True)
class QueryRewritePrompt:
    question: str
    history: list[QueryRewriteHistoryTurn]


@dataclass(frozen=True)
class QueryRewritePromptBundle:
    version: str
    mode: str
    prompt: str


def build_query_rewrite_prompt(payload: QueryRewritePrompt) -> QueryRewritePromptBundle:
    history_lines = [
        f"{turn.role.upper()}: {turn.content}" for turn in payload.history if turn.content.strip()
    ]
    rendered_history = "\n".join(history_lines) if history_lines else "No prior conversation."
    prompt = (
        "You rewrite enterprise chat follow-up questions into standalone retrieval queries.\n"
        "Rules:\n"
        "1. Use the conversation history only to resolve missing context.\n"
        "2. Preserve the user's exact intent.\n"
        "3. Keep the rewritten question concise and specific for retrieval.\n"
        "4. If the latest question is already standalone, return it unchanged.\n"
        "5. Do not answer the question.\n"
        "6. Return valid JSON only.\n\n"
        "Return this JSON schema:\n"
        "{\n"
        '  "standalone_question": "string",\n'
        '  "rewrite_applied": true | false\n'
        "}\n\n"
        f"Conversation history:\n{rendered_history}\n\n"
        f"Latest user question:\n{payload.question}\n"
    )
    return QueryRewritePromptBundle(
        version=QUERY_REWRITE_PROMPT_VERSION,
        mode=QUERY_REWRITE_MODE,
        prompt=prompt,
    )
