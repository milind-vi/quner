"""
Critic agent.

  - ``ask_quick_feedback``: streamed actionable tips on the most recent doctor utterance
  - ``final_feedback``: clinical evaluation + 8 MIRS criteria after the session ends
  - ``generate_hint``: on-demand mid-conversation suggestion for the doctor
"""

import json

import config
import conversion_tables
import globals_conversation_logic
import prompts
from globals_server import broadcast_message

from llm.clients import client, model_for, structured_response_format


async def ask_quick_feedback():
    messages = globals_conversation_logic.get_conversation_history()

    prompt = ""
    for i in range(len(messages)):
        if messages[i]["origin"] == "doctor":
            if i == len(messages) - 1 or i == len(messages) - 2:
                prompt += f"Last utterance of the doctor: {messages[i]['message']}\n"
            else:
                prompt += f"Doctor: {messages[i]['message']}\n"
        elif messages[i]["origin"] == "patient" and i != len(messages) - 1:
            prompt += f"Patient: {messages[i]['message']}\n"

    prompt = prompts.quick_feedback_prompt.substitute(conversation=prompt)
    completion = client.chat.completions.create(
        model=model_for("quick_feedback"),
        messages=[{"role": "user", "content": prompt}],
    )
    response_message = completion.choices[0].message.content
    await globals_conversation_logic.set_quick_feedback(response_message)


async def final_feedback():
    """Generate and broadcast clinical + per-criterion conversational feedback."""

    # ---- Clinical feedback ----
    clinical_schema = {
        "type": "object",
        "properties": {
            "diagnosis_feedback": {"type": "string"},
            "treatment_planning_feedback": {"type": "string"},
            "follow_up_and_monitoring_feedback": {"type": "string"},
            "adherence_to_guidelines_feedback": {"type": "string"},
            "risk_assessment_feedback": {"type": "string"},
            "test_and_investigation_ordering_feedback": {"type": "string"},
            "preventive_care_feedback": {"type": "string"},
        },
        "required": [
            "diagnosis_feedback",
            "treatment_planning_feedback",
            "follow_up_and_monitoring_feedback",
            "adherence_to_guidelines_feedback",
            "risk_assessment_feedback",
            "test_and_investigation_ordering_feedback",
            "preventive_care_feedback",
        ],
        "additionalProperties": False,
    }
    response_format = structured_response_format(clinical_schema)

    disease_name = globals_conversation_logic.get_patient().disease
    disease_documents, score = conversion_tables.diseases[disease_name]
    disease_documents_content = []
    for document in disease_documents:
        try:
            with open(
                f"{config.EBM_path}{document}.{config.EBM_file_extension}",
                "r",
                encoding="utf-8",
            ) as f:
                disease_documents_content.append(f.read())
        except (FileNotFoundError, IsADirectoryError):
            print(f"final_feedback: EBM document not found for {document}, skipping.")

    system_prompt = prompts.final_feedback_diagnostic
    user_prompt = "**Patient Vignette:**\n\n"
    user_prompt += f"```\n{globals_conversation_logic.get_patient().vignette}\n```\n\n"
    user_prompt += "**Doctor-Patient Dialog History:**\n\n"
    user_prompt += "```"
    for entry in globals_conversation_logic.get_conversation_history():
        role = "Doctor" if entry["origin"] == "doctor" else "Patient"
        user_prompt += f"\n{role}: {entry['message']}"
    user_prompt += "\n```"
    if disease_documents_content:
        user_prompt += "\n\n**Golden Standard for Diagnosis and Treatment:**\n\n"
        for document in disease_documents_content:
            user_prompt += f"```\n{document}\n```\n\n"
    else:
        user_prompt += (
            "\n\n**Golden Standard for Diagnosis and Treatment:**\n\n"
            f"No EBM corpus is loaded for this disease ({disease_name}). "
            "Use general medical knowledge to evaluate the doctor's reasoning.\n"
        )

    if config.GROQ_ONLY:
        user_prompt += (
            "\n\nReturn ONLY a single JSON object with EXACTLY these string keys: "
            "diagnosis_feedback, treatment_planning_feedback, follow_up_and_monitoring_feedback, "
            "adherence_to_guidelines_feedback, risk_assessment_feedback, "
            "test_and_investigation_ordering_feedback, preventive_care_feedback. "
            "No other keys, no markdown fences."
        )

    completion = client.chat.completions.create(
        model=model_for("full_feedback"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=response_format,
    )
    response_message_json = json.loads(completion.choices[0].message.content)

    feedback_dict = {
        "action": "clinicalFeedbackResponse",
        "feedback": [
            {"criterium": "Diagnosis", "feedback": response_message_json["diagnosis_feedback"]},
            {"criterium": "Treatment planning", "feedback": response_message_json["treatment_planning_feedback"]},
            {"criterium": "Follow-up and monitoring", "feedback": response_message_json["follow_up_and_monitoring_feedback"]},
            {"criterium": "Adherence to guidelines", "feedback": response_message_json["adherence_to_guidelines_feedback"]},
            {"criterium": "Risk assessment", "feedback": response_message_json["risk_assessment_feedback"]},
            {"criterium": "Test and investigation ordering", "feedback": response_message_json["test_and_investigation_ordering_feedback"]},
            {"criterium": "Preventive care", "feedback": response_message_json["preventive_care_feedback"]},
        ],
    }
    globals_conversation_logic.add_final_feedback(feedback_dict)
    await broadcast_message(feedback_dict)

    # ---- Conversational feedback (per MIRS criterion) ----
    per_criterion_format = structured_response_format({
        "type": "object",
        "properties": {
            "mark": {"type": "number"},
            "explanation": {"type": "string"},
            "evidence": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["mark", "explanation", "evidence"],
        "additionalProperties": False,
    })

    conversation_text = ""
    for entry in globals_conversation_logic.get_conversation_history():
        role = "Doctor" if entry["origin"] == "doctor" else "Patient"
        conversation_text += f"\n{role}: {entry['message']}"

    system_prompt = prompts.final_feedback_system_prompt.substitute(conversation=conversation_text)

    def _eval_criterion(criterium: str):
        user_content = criterium
        if config.GROQ_ONLY:
            user_content += (
                "\n\nReturn ONLY a single JSON object with EXACTLY these keys: "
                "mark (integer 1-5), explanation (string), evidence (array of strings). "
                "No other keys, no markdown fences."
            )
        completion = client.chat.completions.create(
            model=model_for("full_feedback"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.1,
            response_format=per_criterion_format,
        )
        return json.loads(completion.choices[0].message.content)

    for i, criterium in enumerate(prompts.final_feedback_criteria):
        feedback = _eval_criterion(criterium["content"])
        feedback_dict = {
            "action": "feedbackResponse",
            "i": i,
            "criterium": criterium["title"],
            "mark": feedback["mark"],
            "explanation": feedback["explanation"],
            "evidence": feedback["evidence"],
        }
        globals_conversation_logic.add_final_feedback(feedback_dict)
        await broadcast_message(feedback_dict)


async def generate_hint():
    """
    Mid-conversation coaching: ask the critic for one concise next-step suggestion.
    Broadcasts a {"action": "hintResponse", "hint": ...} message.
    """
    patient = globals_conversation_logic.get_patient()
    if patient is None:
        await broadcast_message({"action": "hintResponse", "hint": "Start a patient first."})
        return

    history = globals_conversation_logic.get_conversation_history()
    conversation_text = ""
    for entry in history:
        role = "Doctor" if entry["origin"] == "doctor" else "Patient"
        conversation_text += f"{role}: {entry['message']}\n"
    if not conversation_text.strip():
        conversation_text = "(no exchanges yet — the patient has just walked in)"

    prompt = prompts.hint_prompt.substitute(
        vignette=patient.vignette,
        conversation=conversation_text,
    )
    try:
        completion = client.chat.completions.create(
            model=model_for("quick_feedback"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
        )
        hint = completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"generate_hint failed: {e}")
        hint = f"Hint unavailable right now ({type(e).__name__})."

    await broadcast_message({"action": "hintResponse", "hint": hint})
