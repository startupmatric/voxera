def chunk_text(text: str, target_chars: int = 1800, overlap: int = 200) -> list[str]:
    """
    Simple paragraph-aware chunker.

    - target_chars ≈ 500 tokens (roughly 1800 chars)
    - overlap ≈ 50-100 tokens
    """
    text = (text or "").strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""

    for p in paragraphs:
        if len(current) + len(p) + 2 <= target_chars:
            current = (current + "\n\n" + p).strip() if current else p
        else:
            if current:
                chunks.append(current)
            # if paragraph itself is too big, hard-split it
            if len(p) > target_chars:
                start = 0
                while start < len(p):
                    end = min(start + target_chars, len(p))
                    chunks.append(p[start:end])
                    start = end - overlap if end < len(p) else len(p)
                current = ""
            else:
                current = p

    if current:
        chunks.append(current)

    return chunks
