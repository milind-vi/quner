"""
Generator agent.

Builds an EBM-grounded vignette (8 numbered steps), picks a Furhat face + voice,
and starts the resulting Patient via globals_conversation_logic.
"""

import json
import os
import random

import config
import conversion_tables
import globals_conversation_logic
import prompts
from globals_server import broadcast_message

from agents.lifecycle import save_patient_artifact
from llm.clients import groq_client, model_for
from llm.parsers import extract_markdown_or_fail, parse_face_voice_or_default

NR_OF_STEPS = 8


async def generate_patient(disease_difficulty, neuroticism, extraversion, openness, agreeableness, conscientiousness):
    print("Generating patient...")
    await broadcast_message({"action": "generationStart"})

    # ---- Step 1: pick a disease ---------------------------------------------
    await broadcast_message({"action": "generationUpdate", "text": "Picking a disease with given parameters...", "step": 1, "totalSteps": NR_OF_STEPS})

    disease_name = random.choice(list(conversion_tables.diseases.keys()))
    disease_documents, score = conversion_tables.diseases[disease_name]

    await globals_conversation_logic.add_debug_log(
        f"1. Picked the disease: {disease_name} with a difficulty of {score}/10."
    )

    # ---- Step 2: reason about target difficulty -----------------------------
    await broadcast_message({"action": "generationUpdate", "text": f"Reasoning about changing the difficulty to {disease_difficulty}/10...", "step": 2, "totalSteps": NR_OF_STEPS})

    disease_difficulty_lower = (
        ((disease_difficulty // 5) * 5) - 5 if disease_difficulty % 5 == 0
        else (disease_difficulty // 5) * 5
    )
    disease_difficulty_upper = ((disease_difficulty // 5) * 5) + 5

    if len(disease_documents) == 1:
        prompt_pt1 = prompts.generate_prompt_1_part1a.substitute(disease_name=disease_name)
    else:
        prompt_pt1 = prompts.generate_prompt_1_part1b.substitute(disease_name=disease_name)

    prompt_blocks = [prompt_pt1]

    for document in disease_documents:
        try:
            with open(f"{config.EBM_path}{document}.{config.EBM_file_extension}", "r", encoding="utf-8") as f:
                content = f.read()
            prompt_blocks.append(
                prompts.generate_prompt_1_part2.substitute(
                    content=content,
                    score=score,
                    disease_difficulty=disease_difficulty,
                    disease_difficulty_lower=disease_difficulty_lower,
                    disease_difficulty_upper=disease_difficulty_upper,
                )
            )
        except (FileNotFoundError, IsADirectoryError):
            print(f"generate_patient: EBM document {document} not found, falling back to general knowledge.")

    if not disease_documents:
        no_ebm_block = (
            f"No EBM markdown file is attached for **{disease_name}**. "
            "Use only general medical knowledge for this disease. "
            "Do not output a survey of EBM topics; answer only the four numbered points below, concretely and briefly."
        )
        prompt_blocks.append(
            prompts.generate_prompt_1_part2.substitute(
                content=no_ebm_block,
                score=score,
                disease_difficulty=disease_difficulty,
                disease_difficulty_lower=disease_difficulty_lower,
                disease_difficulty_upper=disease_difficulty_upper,
            )
        )

    prompt = "\n".join(prompt_blocks)
    await globals_conversation_logic.add_debug_log("2a. Prompt\n```\n" + prompt.replace("`", "'") + "\n```")

    running_prompt = [{"role": "user", "content": prompt}]
    completion = groq_client.chat.completions.create(model=model_for("vignette"), messages=running_prompt)
    response_message = completion.choices[0].message.content
    running_prompt.append({"role": "assistant", "content": response_message})
    cleaned = response_message.replace("`", "'")
    await globals_conversation_logic.add_debug_log(f"2b. Answer:\n```\n{cleaned}\n```")

    # ---- Step 3: first vignette draft ---------------------------------------
    await broadcast_message({"action": "generationUpdate", "text": "Generating the first version of the patient...", "step": 3, "totalSteps": NR_OF_STEPS})

    prompt = prompts.generate_prompt_2.substitute(disease_difficulty=disease_difficulty, vignette=prompts.vignette_template)
    await globals_conversation_logic.add_debug_log("3a. Prompt\n```\n" + prompt.replace("`", "'") + "\n```")

    running_prompt.append({"role": "user", "content": prompt})
    completion = groq_client.chat.completions.create(model=model_for("vignette"), messages=running_prompt)
    response_message = completion.choices[0].message.content
    markdown_block = extract_markdown_or_fail(response_message)
    if markdown_block is None:
        await broadcast_message({"action": "generationStop", "state": "error", "text": "Failed to parse the result. Please try again."})
        return
    cleaned = markdown_block.replace("`", "'")
    await globals_conversation_logic.add_debug_log(f"3b. Answer:\n```\n{cleaned}\n```")

    # ---- Step 4: scan for inconsistencies -----------------------------------
    await broadcast_message({"action": "generationUpdate", "text": "Scanning the generated patient's parameters...", "step": 4, "totalSteps": NR_OF_STEPS})

    prompt = prompts.generate_prompt_3.substitute(markdown_block=markdown_block)
    await globals_conversation_logic.add_debug_log("4a. Prompt\n```\n" + prompt.replace("`", "'") + "\n```")

    running_prompt = [{"role": "user", "content": prompt}]
    completion = groq_client.chat.completions.create(model=model_for("vignette"), messages=running_prompt)
    response_message = completion.choices[0].message.content
    cleaned = response_message.replace("`", "'")
    await globals_conversation_logic.add_debug_log(f"4b. Answer:\n```\n{cleaned}\n```")
    running_prompt.append({"role": "assistant", "content": response_message})

    # ---- Step 5: reason about post-process changes --------------------------
    await broadcast_message({"action": "generationUpdate", "text": "Reasoning about post-process changes...", "step": 5, "totalSteps": NR_OF_STEPS})
    prompt = prompts.generate_prompt_4
    await globals_conversation_logic.add_debug_log("5a. Prompt\n```\n" + prompt + "\n```")

    running_prompt.append({"role": "user", "content": prompt})
    completion = groq_client.chat.completions.create(model=model_for("vignette"), messages=running_prompt)
    response_message = completion.choices[0].message.content
    cleaned = response_message.replace("`", "'")
    await globals_conversation_logic.add_debug_log(f"5b. Answer:\n```\n{cleaned}\n```")
    running_prompt.append({"role": "assistant", "content": response_message})

    # ---- Step 6: final vignette ---------------------------------------------
    await broadcast_message({"action": "generationUpdate", "text": "Generating the final version of the patient...", "step": 6, "totalSteps": NR_OF_STEPS})

    prompt = prompts.generate_prompt_5
    await globals_conversation_logic.add_debug_log("6a. Prompt\n```\n" + prompt + "\n```")

    running_prompt.append({"role": "user", "content": prompt})
    completion = groq_client.chat.completions.create(model=model_for("vignette"), messages=running_prompt)
    response_message = completion.choices[0].message.content
    markdown_block = extract_markdown_or_fail(response_message)
    if markdown_block is None:
        await broadcast_message({"action": "generationStop", "state": "error", "text": "Failed to parse the result. Please try again."})
        return
    cleaned = markdown_block.replace("`", "'")
    await globals_conversation_logic.add_debug_log(f"6b. Answer:\n```\n{cleaned}\n```")

    # ---- Step 7: pick a face + voice ----------------------------------------
    await broadcast_message({"action": "generationUpdate", "text": "Choosing an avatar...", "step": 7, "totalSteps": NR_OF_STEPS})

    prompt = prompts.generate_prompt_6.substitute(
        faces=conversion_tables.furhat_faces_list,
        voices=conversion_tables.furhat_elevenlabs_voices_list,
        vignette=markdown_block,
    )
    await globals_conversation_logic.add_debug_log("7a. Prompt\n```\n" + prompt.replace("`", "'") + "\n```")

    prompt_json = (
        prompt
        + '\n\nReply with ONLY a single JSON object, no markdown fences, no other text. '
        + 'Format: {"face": "<exact face name from list>", "voice": "<exact voice name from list>"}'
    )
    completion = groq_client.chat.completions.create(
        model=model_for("vignette"),
        messages=[{"role": "user", "content": prompt_json}],
    )
    response_message = completion.choices[0].message.content
    cleaned = response_message.replace("`", "'")
    await globals_conversation_logic.add_debug_log(f"7b. Answer:\n```\n{cleaned}\n```")

    face, voice = parse_face_voice_or_default(response_message)
    if face is None:
        await broadcast_message({"action": "generationStop", "state": "error", "text": "Failed to parse face/voice JSON. Please try again."})
        return

    # ---- Step 8: start the patient ------------------------------------------
    await broadcast_message({"action": "generationUpdate", "text": "Sending generated details to the robot head...", "step": 8, "totalSteps": NR_OF_STEPS})

    patient = globals_conversation_logic.Patient(
        disease=disease_name,
        vignette=markdown_block,
        face=face,
        voice=voice,
        neuroticism=conversion_tables.translate_score("neuroticism", neuroticism),
        extraversion=conversion_tables.translate_score("extraversion", extraversion),
        openness=conversion_tables.translate_score("openness", openness),
        agreeableness=conversion_tables.translate_score("agreeableness", agreeableness),
        conscientiousness=conversion_tables.translate_score("conscientiousness", conscientiousness),
    )

    if os.environ.get("PRINT_VIGNETTE"):
        print("\n--- GENERATED VIGNETTE (PRINT_VIGNETTE) ---\n")
        print(patient.vignette)
        print(f"\n--- disease={disease_name} face={face} voice={voice} ---\n")

    await globals_conversation_logic.start_patient(patient)
    save_patient_artifact(patient, source="generated")
