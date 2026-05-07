"""
LLM client setup and model dispatch.

Three pipeline modes (driven by config.PIPELINE_MODE):
  - openai-only : everything routes through OpenAI
  - groq-only   : everything routes through Groq's OpenAI-compatible endpoint
  - full        : Cerebras (preprocessing) + Groq (vignette/answers) + OpenAI (post/feedback)

In the first two modes, ``cerebras_client`` and ``groq_client`` are aliases to
``client`` so callers don't need to know the mode.
"""

from openai import OpenAI

import config

print(f"Initializing language models (PIPELINE_MODE={config.PIPELINE_MODE})...")

if config.GROQ_ONLY:
    if not config.GROQ_API_KEY:
        raise RuntimeError(
            "PIPELINE_MODE=groq-only requires GROQ_API_KEY in the project-root .env."
        )
    client = OpenAI(base_url="https://api.groq.com/openai/v1/", api_key=config.GROQ_API_KEY)
    cerebras_client = client
    groq_client = client
elif config.OPENAI_ONLY:
    if not config.OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Set it in the project-root .env (see .env.example)."
        )
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    cerebras_client = client
    groq_client = client
else:
    if not config.OPENAI_API_KEY:
        raise RuntimeError("PIPELINE_MODE=full requires OPENAI_API_KEY in .env.")
    if not config.CEREBRAS_API_KEY or not config.GROQ_API_KEY:
        raise RuntimeError(
            "PIPELINE_MODE=full requires CEREBRAS_API_KEY and GROQ_API_KEY in .env."
        )
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    cerebras_client = OpenAI(base_url="https://api.cerebras.ai/v1/", api_key=config.CEREBRAS_API_KEY)
    groq_client = OpenAI(base_url="https://api.groq.com/openai/v1/", api_key=config.GROQ_API_KEY)


def model_for(stage: str) -> str:
    """
    Resolve the model name for a generation stage based on pipeline mode.

    `stage` is one of: vignette, preprocessing, answergeneration, postprocessing,
    quick_feedback, full_feedback.
    """
    if config.GROQ_ONLY:
        # Use the same Groq model everywhere — simplest and Groq's free tier is fast enough.
        return config.vignette_generation_groq_model
    if config.OPENAI_ONLY:
        return {
            "vignette": config.VSP_model_openai,
            "preprocessing": config.VSP_model_openai,
            "answergeneration": config.VSP_model_openai,
            "postprocessing": config.VSP_model_postprocessing,
            "quick_feedback": config.quick_feedback_api_model,
            "full_feedback": config.full_feedback_api_model,
        }[stage]
    return {
        "vignette": config.vignette_generation_groq_model,
        "preprocessing": config.VSP_model_preprocessing,
        "answergeneration": config.VSP_model_answergeneration,
        "postprocessing": config.VSP_model_postprocessing,
        "quick_feedback": config.quick_feedback_api_model,
        "full_feedback": config.full_feedback_api_model,
    }[stage]


def structured_response_format(schema_dict: dict):
    """
    Build a chat-completions response_format. OpenAI supports strict json_schema; Groq
    only supports json_object, so we fall back and rely on prompt instructions to keep
    the shape correct.
    """
    if config.GROQ_ONLY:
        return {"type": "json_object"}
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "output",
            "strict": True,
            "schema": schema_dict,
        },
    }


# Backward-compatible underscore aliases used during the pre-refactor phase.
_model_for = model_for
_structured_response_format = structured_response_format
