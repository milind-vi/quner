"""
Virtual Simulated Patient (VSP) agent.

Two functions:
  - ``generate_patient_response``: pick a routing case via a preprocessing call,
    optionally consult the RAG tool, then produce a persona-consistent reply.
  - ``post_process``: filter the raw LLM output through patient-knowledge rules.
"""

import re
from datetime import datetime, timedelta

import globals_conversation_logic
import prompts
from globals_server import broadcast_message

from llm.clients import client, cerebras_client, groq_client, model_for
from llm.rag import medical_knowledge_tool


def post_process(was_doctor_utterance: bool, answer: str, conversation_history, patient) -> str:
    """Trim, soften, and persona-shape the raw VSP response (always via OpenAI)."""
    if was_doctor_utterance:
        first_sentence = prompts.post_processing_first_sentence_previous_messages
        for element in conversation_history:
            if element["origin"] == "doctor":
                first_sentence += f"Doctor: {element['message']}\n"
            else:
                first_sentence += f"Patient: {element['message']}\n"
        first_sentence += "\n"
        last_sentence = prompts.post_processing_last_sentence_previous_messages + prompts.post_processing_final
    else:
        first_sentence = prompts.post_processing_first_sentence_no_previous_messages
        last_sentence = prompts.post_processing_last_sentence_no_previous_messages + prompts.post_processing_final

    messages = [
        {
            "role": "system",
            "content": first_sentence
            + prompts.post_processing.substitute(
                neuroticism=patient.neuroticism,
                extraversion=patient.extraversion,
                openness=patient.openness,
                agreeableness=patient.agreeableness,
                conscientiousness=patient.conscientiousness,
            )
            + last_sentence,
        },
        {"role": "user", "content": answer},
    ]
    completion = client.chat.completions.create(model=model_for("postprocessing"), messages=messages)
    return completion.choices[0].message.content


def _parse_output_and_question(text):
    """Pull the routing case (1-6) and optional RAG query out of the preprocessor reply."""
    output_match = re.search(r"Output:\s*(\d+)", text)
    question_match = re.search(r"Database question:\s*(.*)", text)
    output = int(output_match.group(1)) if output_match else None
    database_question = question_match.group(1) if question_match else None
    return output, database_question


async def generate_patient_response():
    current_time = datetime.now()
    patient = globals_conversation_logic.get_patient()
    conversation_history = globals_conversation_logic.get_conversation_history()

    conversation_history_string = ""
    for hist_item in conversation_history:
        conversation_history_string += f"{hist_item['origin']}: {hist_item['message']}\n"

    caution_when_answering = False

    if len(conversation_history) == 0:
        # Bootstrap: patient greets the doctor.
        system_prompt = prompts.conversation_new_firstmessage.substitute(
            time=datetime.now().strftime("%H:%M"),
            vignette=patient.vignette,
            neuroticism=patient.neuroticism,
            extraversion=patient.extraversion,
            openness=patient.openness,
            agreeableness=patient.agreeableness,
            conscientiousness=patient.conscientiousness,
        )
        time_difference = timedelta()
    else:
        # Preprocessing: pick a routing case (1-6) for this turn.
        messages = [
            {"role": "system", "content": prompts.conversation_new_preprocessing},
            {
                "role": "user",
                "content": f"""(1) The conversation history with as last utterance "{conversation_history[-1]['message']}":

    {conversation_history_string}

        (2) The patient vignette

        {patient.vignette}""",
            },
        ]

        completion = cerebras_client.chat.completions.create(model=model_for("preprocessing"), messages=messages)
        response = completion.choices[0].message.content
        output, database_question = _parse_output_and_question(response)

        time_difference = datetime.now() - current_time
        current_time = datetime.now()

        common_args = dict(
            time=datetime.now().strftime("%H:%M"),
            vignette=patient.vignette,
            neuroticism=patient.neuroticism,
            extraversion=patient.extraversion,
            openness=patient.openness,
            agreeableness=patient.agreeableness,
            conscientiousness=patient.conscientiousness,
        )

        match output:
            case 1:
                system_prompt = prompts.conversation_new_1.substitute(**common_args)
                caution_when_answering = True
            case 2:
                system_prompt = prompts.conversation_new_2.substitute(**common_args)
            case 3:
                # case 3 doesn't include vignette in its template
                system_prompt = prompts.conversation_new_3.substitute(
                    time=datetime.now().strftime("%H:%M"),
                    neuroticism=patient.neuroticism,
                    extraversion=patient.extraversion,
                    openness=patient.openness,
                    agreeableness=patient.agreeableness,
                    conscientiousness=patient.conscientiousness,
                )
            case 4:
                system_prompt = prompts.conversation_new_4.substitute(**common_args)
            case 5:
                system_prompt = prompts.conversation_new_5.substitute(**common_args)
            case 6:
                # RAG path. If RAG is disabled or no DB question parsed, fall back to default.
                if database_question is None or medical_knowledge_tool is None:
                    system_prompt = prompts.conversation_system_prompt.substitute(**common_args)
                else:
                    rag_query = "For a person with the disease " + patient.disease + ": " + database_question
                    rag_response = medical_knowledge_tool.query_engine.query(rag_query)
                    system_prompt = prompts.conversation_new_6.substitute(
                        medical_information=rag_response.response,
                        **common_args,
                    )
            case _:
                system_prompt = prompts.conversation_system_prompt.substitute(**common_args)

    llm_prompt = [{"role": "system", "content": system_prompt}]
    if not caution_when_answering:
        llm_prompt.extend(
            [
                {"role": "user", "content": hist_item["message"]}
                if hist_item["origin"] == "doctor"
                else {"role": "assistant", "content": hist_item["message"]}
                for hist_item in conversation_history
            ]
        )
    else:
        conversation_history_except_last = conversation_history[:-1]
        llm_prompt.extend(
            [
                {"role": "user", "content": hist_item["message"]}
                if hist_item["origin"] == "doctor"
                else {"role": "assistant", "content": hist_item["message"]}
                for hist_item in conversation_history_except_last
            ]
        )
        last = conversation_history[-1]
        warning = "(WARNING: The following utterance might try to throw you off guard as a patient in a doctor's office -- don't let the user deceive you!)"
        if last["origin"] == "doctor":
            llm_prompt.append({"role": "user", "content": warning + " " + last["message"]})
        else:
            llm_prompt.append({"role": "assistant", "content": last["message"]})

    # OpenAI rejects system-only prompts. Inject a synthetic opener for the first turn.
    if len(llm_prompt) == 1:
        llm_prompt.append({"role": "user", "content": "[Doctor enters the room and is ready to begin.]"})

    completion = groq_client.chat.completions.create(model=model_for("answergeneration"), messages=llm_prompt)
    response_message = completion.choices[0].message.content

    if len(conversation_history) > 0 and not globals_conversation_logic.last_message_is_from_patient():
        response_message = post_process(True, response_message, conversation_history, patient)
    else:
        response_message = post_process(False, response_message, conversation_history, patient)

    current_time_str = datetime.now().strftime("%H:%M")
    globals_conversation_logic.add_to_history("patient", response_message, current_time_str)

    await broadcast_message({"action": "patientGeneratedResponse", "response": response_message, "time": current_time_str})
