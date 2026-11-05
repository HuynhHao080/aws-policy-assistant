"""Bounded policy indexing: score a section, quote its surrounding context."""
import re

MAX_TEXT = 1400
MAX_CHUNKS = 64

def policy_chunks(content):
    parts = [part.strip() for part in re.split(r"\n(?=\s*\d+[.)]\s)|\n[ \t]*\n", content) if part.strip()]
    centers = [part[start:start + MAX_TEXT] for part in parts for start in range(0, len(part), 1200)]
    if len(centers) > MAX_CHUNKS:
        centers = [content[start:start + MAX_TEXT] for start in range(0, len(content), 1200)]
    chunks = []
    for index, center in enumerate(centers):
        # Never let adjacent context displace the section whose vector was matched.
        text = center
        if index and len(centers[index - 1]) + 1 + len(text) <= MAX_TEXT:
            text = centers[index - 1] + "\n" + text
        if index + 1 < len(centers) and len(text) + 1 + len(centers[index + 1]) <= MAX_TEXT:
            text += "\n" + centers[index + 1]
        chunks.append({"embedding_text": center, "text": text})
    return chunks
