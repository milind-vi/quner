"""
Prompt templates for the agentic GP-skills framework.

Originally one 879-line ``prompts.py``; split by purpose for navigability.
The previous flat namespace is preserved by re-exporting everything here, so
``import prompts; prompts.vignette_template`` still works.
"""

# Vignette + scenario generation (Generator agent)
from .generation import (
    vignette_template,
    generate_prompt_1_part1a,
    generate_prompt_1_part1b,
    generate_prompt_1_part2,
    generate_prompt_2,
    generate_prompt_3,
    generate_prompt_4,
    generate_prompt_5,
    generate_prompt_6,
)

# VSP (Virtual Simulated Patient) conversational prompts
from .vsp import (
    conversation_system_prompt,
    conversation_new_preprocessing,
    conversation_new_1,
    conversation_new_2,
    conversation_new_3,
    conversation_new_4,
    conversation_new_5,
    conversation_new_6,
    conversation_new_firstmessage,
)

# Critic agent — quick + final feedback
from .feedback import (
    quick_feedback_prompt,
    final_feedback_system_prompt,
    final_feedback_criteria,
    final_feedback_diagnostic,
)

# Patient-reply post-processing (style + safety filter)
from .post_processing import (
    post_processing_first_sentence_previous_messages,
    post_processing_last_sentence_previous_messages,
    post_processing_first_sentence_no_previous_messages,
    post_processing_last_sentence_no_previous_messages,
    post_processing,
    post_processing_final,
)

# Mid-conversation coaching
from .hint import hint_prompt

__all__ = [
    "vignette_template",
    "generate_prompt_1_part1a",
    "generate_prompt_1_part1b",
    "generate_prompt_1_part2",
    "generate_prompt_2",
    "generate_prompt_3",
    "generate_prompt_4",
    "generate_prompt_5",
    "generate_prompt_6",
    "conversation_system_prompt",
    "conversation_new_preprocessing",
    "conversation_new_1",
    "conversation_new_2",
    "conversation_new_3",
    "conversation_new_4",
    "conversation_new_5",
    "conversation_new_6",
    "conversation_new_firstmessage",
    "quick_feedback_prompt",
    "final_feedback_system_prompt",
    "final_feedback_criteria",
    "final_feedback_diagnostic",
    "post_processing_first_sentence_previous_messages",
    "post_processing_last_sentence_previous_messages",
    "post_processing_first_sentence_no_previous_messages",
    "post_processing_last_sentence_no_previous_messages",
    "post_processing",
    "post_processing_final",
    "hint_prompt",
]
