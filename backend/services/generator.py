import asyncio
from typing import List, Optional

import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
from tenacity import retry, retry_if_not_exception_type, stop_after_attempt, wait_exponential

from backend.core.config import get_settings
from backend.core.logging import get_logger
from backend.services.retriever import RetrievedChunk

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are GitLab Assistant, an expert on GitLab's handbook, product, and DevOps practices.

## Your Role
Help users understand GitLab — its culture, policies, product features, CI/CD, APIs, and DevOps workflows.

## Rules

1. **Prioritise the provided CONTEXT.** When the context contains relevant information, base your answer
   on it and cite it. This is your primary knowledge source.

2. **Supplement when needed.** If the context is incomplete but you have reliable knowledge about GitLab
   (features, CI/CD syntax, API usage, comparisons), you may use it to give a complete answer.

3. If a question is about specific internal policies (team names, hiring details,
   compensation) and the context doesn't cover it, link to https://handbook.gitlab.com/.
   Don't guess at internal specifics.

4. **For technical questions**, provide complete, working code examples (YAML, curl, CLI).
   Don't truncate. Add brief comments explaining key sections.

5. **Be concise and direct.** Lead with the answer, then supporting detail. Use markdown formatting
   (bullets, bold, code blocks). Keep answers focused — under 400 words unless code or detail demands more.

6. **For follow-ups**, use conversation history to resolve references like "it" or "that".

7. **Never fabricate** policies, team structures, or product features that don't exist.
   Stay within what you know to be true about GitLab.

8. **Code blocks:** Use standard markdown fences (three backticks + bash/yaml). GitLab REST URLs must include `<PROJECT_ID>` in `/api/v4/projects/<PROJECT_ID>/...` — never `projects//`.
"""

CONTEXT_TEMPLATE = """
## Retrieved Context

{context_blocks}

---

{history_section}

## Question
{query}

## Answer
"""


def _format_context_blocks(chunks: List[RetrievedChunk]) -> str:
    blocks = []
    for i, chunk in enumerate(chunks, 1):
        source_label = chunk.section if chunk.section else chunk.title
        blocks.append(
            f"[Source {i}] **{source_label}** ({chunk.section_url})\n{chunk.text}"
        )
    return "\n\n---\n\n".join(blocks)


def _format_history_section(history_text: str) -> str:
    if not history_text:
        return ""
    return f"## Conversation History\n{history_text}\n"


class GeneratorService:
    def __init__(self):
        cfg = get_settings()
        genai.configure(api_key=cfg.gemini_api_key)
        self._model = genai.GenerativeModel(
            model_name=cfg.gemini_chat_model,
            system_instruction=SYSTEM_PROMPT,
            generation_config=genai.GenerationConfig(
                temperature=0.2,
                top_p=0.8,
                max_output_tokens=4096,
            ),
        )
        logger.info("GeneratorService ready", model=cfg.gemini_chat_model)

    @retry(
        retry=retry_if_not_exception_type(ResourceExhausted),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        reraise=True,
    )
    async def generate(
        self,
        query: str,
        retrieved_chunks: List[RetrievedChunk],
        history_text: str = "",
    ) -> str:
        if not retrieved_chunks:
            return (
                "I don't have enough information in the GitLab documentation to answer "
                "this question confidently. Please visit "
                "[handbook.gitlab.com](https://handbook.gitlab.com/) or "
                "[about.gitlab.com/direction](https://about.gitlab.com/direction/) "
                "for more information."
            )

        context_blocks = _format_context_blocks(retrieved_chunks)
        history_section = _format_history_section(history_text)

        prompt = CONTEXT_TEMPLATE.format(
            context_blocks=context_blocks,
            history_section=history_section,
            query=query,
        )

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._model.generate_content(prompt),
        )

        answer = response.text.strip()
        logger.debug("Generated answer", query=query[:80], answer_length=len(answer))
        return answer


_generator: GeneratorService | None = None


def get_generator() -> GeneratorService:
    global _generator
    if _generator is None:
        _generator = GeneratorService()
    return _generator
