# ⚠️ WARNING: RESEARCH DEMO ONLY – NOT FOR PRODUCTION USE ⚠️
#
# This code is a research prototype and should NOT be deployed in any
# production environment. It lacks critical features required for safe and
# scalable operation, including:
#
# - No transport security (no HTTPS, no authentication)
# - Global shared state with no isolation between clients
# - Blocking I/O inside async handlers (can freeze the event loop)
# - No error recovery, retry logic, or request timeouts
# - Uses `print()` instead of structured logging
#
# Use at your own risk. This repository is intended for experimentation only.

"""
Application configuration.

Secrets and pipeline-mode flags are read from a project-root .env file (see
.env.example). Model names and pipeline-shaped defaults live in this file so they
can be tweaked without restarting your shell.
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    # Project root .env (one level above central_backend_server/).
    _ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
    if _ENV_PATH.exists():
        load_dotenv(_ENV_PATH)
    else:
        # Fall back to default search (cwd + parents).
        load_dotenv()
except ImportError:
    # python-dotenv not installed; rely on real env vars.
    pass


def _get_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(int(default))).strip().lower() in ("1", "true", "yes", "on")


# ---------------------------------------------------------------------------
# Secrets
# ---------------------------------------------------------------------------
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY", "")

# ---------------------------------------------------------------------------
# Pipeline mode
# ---------------------------------------------------------------------------
# "openai-only" : every LLM call routes through OpenAI; Pinecone/RAG disabled.
# "groq-only"   : every LLM call routes through Groq (OpenAI-compatible). Free tier.
# "full"        : original paper pipeline (Cerebras preprocessing + Groq generation + OpenAI post/feedback).
PIPELINE_MODE = os.environ.get("PIPELINE_MODE", "openai-only").strip().lower()
OPENAI_ONLY = PIPELINE_MODE == "openai-only"
GROQ_ONLY = PIPELINE_MODE == "groq-only"

# RAG is independent of pipeline mode but is only meaningful when "full" is selected.
USE_RAG = _get_bool("USE_RAG", default=False) and not (OPENAI_ONLY or GROQ_ONLY)

# ---------------------------------------------------------------------------
# Disease / EBM corpus
# ---------------------------------------------------------------------------
EBM_path = os.environ.get("EBM_PATH", "")
EBM_file_extension = os.environ.get("EBM_FILE_EXTENSION", "md")

# ---------------------------------------------------------------------------
# Pinecone (only used when USE_RAG)
# ---------------------------------------------------------------------------
pinecone_index_name = os.environ.get("PINECONE_INDEX_NAME", "quner2")

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
# Where to save each generated/launched patient as a readable .md file (empty = disabled).
GENERATED_PATIENT_OUTPUT_DIR = os.environ.get("GENERATED_PATIENT_OUTPUT_DIR", "generated_patients")

# ---------------------------------------------------------------------------
# RAG embedding (only used when USE_RAG)
# ---------------------------------------------------------------------------
RAG_EMBEDDING_MODEL = os.environ.get("RAG_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
RAG_EMBEDDING_DIMENSION = int(os.environ.get("RAG_EMBEDDING_DIMENSION", "384"))

# ---------------------------------------------------------------------------
# Models — OpenAI path (always used in openai-only mode; also used for feedback in full mode)
# ---------------------------------------------------------------------------
quick_feedback_api_model = os.environ.get("QUICK_FEEDBACK_MODEL", "gpt-4o-mini")
full_feedback_api_model = os.environ.get("FULL_FEEDBACK_MODEL", "gpt-4o-mini")
VSP_model_ragprocessing = os.environ.get("VSP_MODEL_RAGPROCESSING", "gpt-4o-mini")
VSP_model_postprocessing = os.environ.get("VSP_MODEL_POSTPROCESSING", "gpt-4o-mini")
vignette_generation_model = os.environ.get("VIGNETTE_GENERATION_MODEL", "gpt-4o-mini")

# In openai-only mode the same OpenAI model handles preprocessing and answer generation.
VSP_model_openai = os.environ.get("VSP_MODEL_OPENAI", "gpt-4o-mini")

# ---------------------------------------------------------------------------
# Models — full pipeline (Groq / Cerebras)
# ---------------------------------------------------------------------------
vignette_generation_groq_model = os.environ.get("VIGNETTE_GENERATION_GROQ_MODEL", "llama-3.3-70b-versatile")
VSP_model_preprocessing = os.environ.get("VSP_MODEL_PREPROCESSING", "llama-4-scout-17b-16e-instruct")
VSP_model_answergeneration = os.environ.get("VSP_MODEL_ANSWERGENERATION", "llama-3.3-70b-versatile")
