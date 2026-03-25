import httpx
import json
from typing import Optional, AsyncIterator
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from core.config import get_settings
from core.cache import cache_get, cache_set, cache_key, content_hash
from core.logging import logger

settings = get_settings()

SUMMARIZE_PROMPT = """Summarize this research paper concisely, highlighting key contributions, methodology, and results.

Paper title: {title}
Abstract: {abstract}

Respond in JSON with:
{{
  "tldr": "<one-sentence summary>",
  "deep_summary": "<3-5 sentences covering contributions, methodology, and results>",
  "key_concepts": ["<concept1>", "<concept2>", "<concept3>"]
}}"""

GAP_EXPLAIN_PROMPT = """You are analyzing a research graph cluster. This community of {size} papers has low connectivity density ({density:.3f}), suggesting it may be an underexplored research area.

Paper titles in this cluster:
{titles}

In 2-3 sentences, explain why this could be a research gap and what directions could bridge it."""

LITERATURE_REVIEW_PROMPT = """Generate a coherent literature review section from these papers. Focus on thematic connections, progression of ideas, and open questions.

Papers:
{papers}

Write in academic prose. Cite papers by [Title, Year]. 3-5 paragraphs."""

COMPARISON_PROMPT = """Compare these two research papers analytically:

Paper A: {paper_a}
Paper B: {paper_b}

Cover: 1) Core contributions, 2) Methodology differences, 3) Results/impact, 4) Complementarity or conflict. Be concise (5-8 sentences total)."""


class LLMService:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=settings.llm_timeout)
        self.headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "HTTP-Referer": "https://semantic-research-explorer.ai",
            "X-Title": "Semantic Research Explorer",
            "Content-Type": "application/json",
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    )
    async def _call_openrouter(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        stream: bool = False,
        json_mode: bool = False,
    ) -> str:
        if not settings.openrouter_api_key:
            raise ValueError("OpenRouter API key not configured")

        payload: dict = {
            "model": model or settings.openrouter_model,
            "messages": messages,
            "max_tokens": settings.llm_max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            response = await self.client.post(
                f"{settings.openrouter_base_url}/chat/completions",
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                # Try fallback model
                payload["model"] = settings.openrouter_fallback_model
                response = await self.client.post(
                    f"{settings.openrouter_base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            raise

    async def summarize_paper(
        self,
        paper_id: str,
        title: str,
        abstract: str,
    ) -> dict:
        """Generate TL;DR + deep summary with caching."""
        ck = cache_key("summary", paper_id)
        cached = await cache_get(ck)
        if cached:
            logger.info("summary_cache_hit", paper_id=paper_id)
            return cached

        prompt = SUMMARIZE_PROMPT.format(title=title, abstract=abstract or "Not available")
        try:
            raw = await self._call_openrouter(
                [{"role": "user", "content": prompt}],
                json_mode=True,
            )
            result = json.loads(raw)
        except Exception as e:
            logger.warning("summarize_failed", paper_id=paper_id, error=str(e))
            # Fallback: return abstract snippet
            result = {
                "tldr": abstract[:200] + "..." if abstract and len(abstract) > 200 else abstract,
                "deep_summary": abstract or "Summary unavailable.",
                "key_concepts": [],
                "_fallback": True,
            }

        await cache_set(ck, result, settings.cache_summary_ttl)
        return result

    async def explain_gap(self, paper_titles: list[str], density: float, community_size: int) -> str:
        """Generate explanation for a research gap."""
        ck = cache_key("gap", content_hash("|".join(sorted(paper_titles))))
        cached = await cache_get(ck)
        if cached:
            return cached

        titles_text = "\n".join(f"- {t}" for t in paper_titles[:15])
        prompt = GAP_EXPLAIN_PROMPT.format(
            size=community_size,
            density=density,
            titles=titles_text,
        )
        try:
            result = await self._call_openrouter([{"role": "user", "content": prompt}])
        except Exception as e:
            logger.warning("gap_explain_failed", error=str(e))
            result = "This community shows sparse interconnections, suggesting an underexplored research niche."

        await cache_set(ck, result, settings.cache_summary_ttl)
        return result

    async def generate_literature_review(self, papers: list[dict]) -> str:
        """Generate a literature review from a list of papers."""
        papers_text = "\n\n".join(
            f"[{p.get('title', 'Untitled')}, {p.get('year', '?')}]: {p.get('abstract', '')[:300]}"
            for p in papers[:10]
        )
        prompt = LITERATURE_REVIEW_PROMPT.format(papers=papers_text)
        try:
            return await self._call_openrouter([{"role": "user", "content": prompt}])
        except Exception as e:
            logger.error("literature_review_failed", error=str(e))
            return "Literature review generation is temporarily unavailable."

    async def compare_papers(self, paper_a: dict, paper_b: dict) -> str:
        """Compare two papers."""
        def fmt(p: dict) -> str:
            return f"Title: {p.get('title')}\nAbstract: {p.get('abstract', '')[:400]}"

        ck = cache_key("compare", paper_a.get("id", ""), paper_b.get("id", ""))
        cached = await cache_get(ck)
        if cached:
            return cached

        prompt = COMPARISON_PROMPT.format(paper_a=fmt(paper_a), paper_b=fmt(paper_b))
        try:
            result = await self._call_openrouter([{"role": "user", "content": prompt}])
            await cache_set(ck, result, settings.cache_summary_ttl)
            return result
        except Exception as e:
            logger.error("compare_failed", error=str(e))
            return "Paper comparison is temporarily unavailable."

    async def concept_dependency_map(self, topic: str, context_papers: list[dict]) -> dict:
        """Map concept dependencies for a research topic."""
        abstracts = "\n".join(
            f"- {p.get('title')}: {p.get('abstract', '')[:200]}" for p in context_papers[:8]
        )
        prompt = f"""For the topic "{topic}", identify key concepts and their dependencies based on these papers:
{abstracts}

Respond in JSON:
{{"concepts": [{{"name": "...", "depends_on": ["..."], "description": "..."}}]}}"""
        try:
            raw = await self._call_openrouter(
                [{"role": "user", "content": prompt}], json_mode=True
            )
            return json.loads(raw)
        except Exception:
            return {"concepts": []}

    async def close(self):
        await self.client.aclose()


_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
