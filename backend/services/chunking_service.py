import re
import tiktoken
from typing import Optional
from core.config import get_settings
from core.logging import logger

settings = get_settings()

SECTION_HEADERS = re.compile(
    r"^(abstract|introduction|background|related work|methodology|methods|"
    r"experiments?|results?|discussion|conclusion|references?|acknowledgements?|"
    r"appendix|supplementary)",
    re.IGNORECASE | re.MULTILINE,
)

try:
    _enc = tiktoken.get_encoding("cl100k_base")
except Exception:
    _enc = None


def count_tokens(text: str) -> int:
    if _enc:
        return len(_enc.encode(text))
    return len(text.split())


def chunk_text(
    text: str,
    paper_id: str,
    section: str = "abstract",
    min_tokens: int = 128,
    max_tokens: int = 512,
    overlap: int = 64,
) -> list[dict]:
    """Sliding window chunking with token-based overlap."""
    if not text or not text.strip():
        return []

    words = text.split()
    if not words:
        return []

    # Estimate tokens per word (rough, avoids heavy tokenization for every word)
    total_tokens = count_tokens(text)
    tokens_per_word = max(1.0, total_tokens / len(words))

    # Convert token limits to word counts
    max_words = int(max_tokens / tokens_per_word)
    overlap_words = int(overlap / tokens_per_word)

    chunks = []
    start = 0
    chunk_idx = 0

    while start < len(words):
        end = min(start + max_words, len(words))
        chunk_words = words[start:end]
        chunk_text = " ".join(chunk_words)
        token_count = count_tokens(chunk_text)

        if token_count >= min_tokens or (start == 0 and len(words) < min_tokens // 2):
            chunk_id = f"{paper_id}:{section}:{chunk_idx}"
            chunks.append({
                "id": chunk_id,
                "paper_id": paper_id,
                "section": section,
                "chunk_index": chunk_idx,
                "content": chunk_text,
                "token_count": token_count,
            })
            chunk_idx += 1

        if end >= len(words):
            break

        # Slide forward with overlap
        start = end - overlap_words

    return chunks


def split_into_sections(text: str) -> dict[str, str]:
    """Split full paper text into named sections."""
    if not text:
        return {"full_text": text}

    # Find section boundaries
    boundaries = [(m.start(), m.group().strip().lower()) for m in SECTION_HEADERS.finditer(text)]

    if not boundaries:
        return {"full_text": text}

    sections = {}
    for i, (start, header) in enumerate(boundaries):
        end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
        section_text = text[start:end].strip()
        sections[header] = section_text

    return sections


def chunk_paper(
    paper_id: str,
    abstract: Optional[str],
    full_text: Optional[str] = None,
    min_tokens: int = 128,
    max_tokens: int = 512,
    overlap: int = 64,
) -> list[dict]:
    """Chunk an entire paper into semantically meaningful pieces."""
    all_chunks = []

    if abstract:
        abstract_chunks = chunk_text(
            abstract, paper_id, "abstract", min_tokens, max_tokens, overlap
        )
        all_chunks.extend(abstract_chunks)

    if full_text:
        sections = split_into_sections(full_text)
        for section_name, section_content in sections.items():
            if section_name == "references":
                continue  # skip references
            section_chunks = chunk_text(
                section_content, paper_id, section_name, min_tokens, max_tokens, overlap
            )
            all_chunks.extend(section_chunks)
    elif not abstract:
        logger.warning("no_text_to_chunk", paper_id=paper_id)

    return all_chunks
