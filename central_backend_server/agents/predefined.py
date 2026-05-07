"""Launch one of the hard-coded predefined patients."""

import globals_conversation_logic
import predefined_patients

from agents.lifecycle import save_patient_artifact


async def launch_predefined_patient(patient_nr):
    """Load patient #N from ``predefined_patients.mapping`` and start the session."""
    patient = predefined_patients.mapping[patient_nr]
    await globals_conversation_logic.add_debug_log(
        f"""Picked the patient with the following parameters:

- Disease: {patient.disease}
- Face: {patient.face}
- Voice: {patient.voice}
- Personality

    - Neuroticism: {patient.neuroticism}
    - Extraversion: {patient.extraversion}
    - Openness: {patient.openness}
    - Agreeableness: {patient.agreeableness}
    - Conscientiousness: {patient.conscientiousness}
- Vignette:
```
{patient.vignette}
```"""
    )
    print("Patient started")
    await globals_conversation_logic.start_patient(patient)
    save_patient_artifact(patient, source=f"predefined_{patient_nr}")
