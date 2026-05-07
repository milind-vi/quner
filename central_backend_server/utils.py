"""
Public API facade for the backend.

The implementation now lives in ``llm/`` (clients, RAG, parsers) and ``agents/``
(generator, vsp, critic, predefined, lifecycle). This file re-exports the names
that ``ws_server.py`` and external scripts have always imported as ``utils.X``,
so existing call sites keep working.
"""

# Side-effectful imports first so the LLM clients are constructed once at boot
# (preserving the previous ``import utils`` initialisation order).
from llm.clients import (  # noqa: F401
    client,
    cerebras_client,
    groq_client,
    model_for,
    structured_response_format,
    _model_for,
    _structured_response_format,
)
from llm.rag import medical_knowledge_tool  # noqa: F401
from llm.parsers import (  # noqa: F401
    extract_markdown_or_fail,
    parse_face_voice_or_default,
    sanitize_filename,
    _extract_markdown_or_fail,
    _parse_face_voice_or_default,
    _sanitize_filename,
)

# Public agent API (what ws_server.py calls).
from agents.lifecycle import stop_patient, save_patient_artifact  # noqa: F401
from agents.critic import (  # noqa: F401
    ask_quick_feedback,
    final_feedback,
    generate_hint,
)
from agents.generator import generate_patient  # noqa: F401
from agents.predefined import launch_predefined_patient  # noqa: F401
from agents.vsp import generate_patient_response, post_process  # noqa: F401

__all__ = [
    "client", "cerebras_client", "groq_client",
    "model_for", "structured_response_format",
    "medical_knowledge_tool",
    "extract_markdown_or_fail", "parse_face_voice_or_default", "sanitize_filename",
    "stop_patient", "save_patient_artifact",
    "ask_quick_feedback", "final_feedback", "generate_hint",
    "generate_patient", "launch_predefined_patient",
    "generate_patient_response", "post_process",
]
