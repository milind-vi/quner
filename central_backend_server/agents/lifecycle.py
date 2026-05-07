"""Lifecycle helpers: stopping a patient and persisting generated patients to disk."""

import os
from datetime import datetime

import config
import globals_conversation_logic
from globals_server import broadcast_message
from llm.parsers import sanitize_filename


async def stop_patient():
    """Mark the patient as paused and broadcast the state change."""
    await globals_conversation_logic.stop_patient()
    await broadcast_message({"action": "stopPatient"})


def save_patient_artifact(patient, source: str = "generated"):
    """
    Write patient vignette + metadata to a Markdown file under
    ``config.GENERATED_PATIENT_OUTPUT_DIR``. Returns the file path or None.
    """
    out_dir = getattr(config, "GENERATED_PATIENT_OUTPUT_DIR", None)
    if not out_dir or not str(out_dir).strip():
        return None
    out_dir = os.path.abspath(out_dir)
    try:
        os.makedirs(out_dir, exist_ok=True)
    except OSError as e:
        print(f"save_patient_artifact: could not create {out_dir}: {e}")
        return None
    cid = globals_conversation_logic.get_conversation_id()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = sanitize_filename(patient.disease)
    path = os.path.join(out_dir, f"{ts}_{slug}.md")
    meta = (
        f"# Generated patient — {patient.disease}\n\n"
        f"| Field | Value |\n|-------|-------|\n"
        f"| source | {source} |\n"
        f"| conversation_id | {cid} |\n"
        f"| face | {patient.face} |\n"
        f"| voice | {patient.voice} |\n\n"
        f"---\n\n"
    )
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(meta)
            f.write(patient.vignette)
        print(f"Saved patient artifact: {path}")
        return path
    except OSError as e:
        print(f"save_patient_artifact: could not write {path}: {e}")
        return None
