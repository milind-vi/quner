"""Small parsing utilities used by the agents to clean LLM output."""

import json
import re

from mdextractor import extract_md_blocks


def extract_markdown_or_fail(response_message: str):
    """Extract a markdown block from a response. Returns None if it can't be parsed."""
    if not response_message:
        return None
    stripped = response_message.strip().replace("\n", "").replace(" ", "")
    if stripped and stripped[0] == "#":
        return response_message
    blocks = extract_md_blocks(response_message)
    if blocks:
        return blocks[0]
    if "#" in response_message:
        return response_message
    return None


def parse_face_voice_or_default(response_message: str):
    """Parse the {face, voice} JSON returned by the avatar-selection step."""
    text = response_message.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[^{}]*\"face\"[^{}]*\"voice\"[^{}]*\}", text, re.DOTALL)
        if not m:
            m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            return None, None
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None, None
    return obj.get("face"), obj.get("voice")


def sanitize_filename(s: str, max_len: int = 80) -> str:
    out = re.sub(r"[^\w\-. ]+", "_", s, flags=re.UNICODE)
    out = re.sub(r"\s+", "_", out.strip())[:max_len].strip("_") or "patient"
    return out


# Backward-compatible underscore aliases.
_extract_markdown_or_fail = extract_markdown_or_fail
_parse_face_voice_or_default = parse_face_voice_or_default
_sanitize_filename = sanitize_filename
