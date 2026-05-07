from string import Template

post_processing_first_sentence_previous_messages = "**Role**: You are an assistant tasked with slightly modifying a patient's response in a medical conversation. Your goal is to ensure the response adheres to the rules provided while keeping the wording as close to the original as possible.\n\n**Context**: A conversation between a doctor and a patient meeting for the first time. The patient has a certain disease. The conversation so far, just for reference, is:\n\n"
post_processing_last_sentence_previous_messages = "6. **Answer the Doctor's Question**: Ensure that the revised text directly answers the doctor's last utterance, possibly by rephrasing the original response. Do not introduce any new information or knowledge.\n\n"
post_processing_first_sentence_no_previous_messages = "**Role**: You are an assistant tasked with slightly modifying a patient's response in a medical conversation. Your goal is to ensure the response adheres to the rules provided while keeping the wording as close to the original as possible.\n\n**Context**: an INTRODUCTION of a patient meeting a doctor for the first time. The patient has a certain disease. The introduction possibly contains a first greeting.\n"
post_processing_last_sentence_no_previous_messages = "6. **Answer the Doctor's Utterance**: Ensure that the revised text directly answers the doctor's last utterance, possibly by rephrasing the original response. Do not introduce any new information or knowledge.\n\n"

# Removed: - It is forbidden to give more details than needed. Remove any unnecessary details.
# Removed: - It is forbidden to use terms that signify uncertainty, such as likely, such as, possibly, probably, etc. Change them to be certain.
# Removed: - It is mandatory for the revised answer to be approximately the same length as the original answer. Do not add or remove more than 10% of the original length.
post_processing = Template("""You are provided with the patient's possible response, which may need slight adjustments to comply with the following rules. Modify the text accordingly, while leaving everything else unchanged:

1. **Patient's Knowledge Limitations**: The response should only include information that a patient would reasonably know or can deduce from the conversation history. Remove any medical knowledge that can only be known by a doctor or specialist. However, it's acceptable for the patient to mention names and doses of medications they are currently taking or have taken before, or to mention diseases and treatments of close relatives or friends or of a former self, if and only if it is not the same disease they have.

2. **Avoid Medical Diagnoses and Plans**: Do not include possible diagnoses, treatments, medications, or management plans regarding the patient's own condition except if the doctor has mentioned it before. The patient may reference disease knowledge related to relatives or friends or very basic general medical knowledge, except if this very basic general medical knowledge is about the patient's own condition. Do not include diseases, treatment, drugs... about what the patient has been hearing, thinking, hearing... concerning their own condition.

3. **No Disease Hypotheses**: Exclude any hypotheses or statements about what disease the patient has or might have if the doctor didn't mention it before. Replace such information with expressions of uncertainty or remove it entirely.

4. **Adjust Tone According to Personality Traits**: Without altering the content or introducing new information, adjust the tone of the text to match the following personality traits and make sure it's noticeable in the result:

    - $neuroticism
    - $extraversion
    - $openness
    - $agreeableness
    - $conscientiousness

5. **Direct Patient Speech Only**: Provide only the words that the patient would say. Do not include any thoughts, actions, or descriptions beyond the patient's spoken words. Avoid introductory phrases like "The patient says." or actions like *standing up* or (laughing), nor modifiers like (anxiously).

""")
post_processing_final = "7. **Maintain Originality**: Other than the adjustments required by the rules above, do not change anything else about the original response. Avoid unnecessary word changes. The edited answer should closely resemble the original."

# ---------------------------------------------------------------------------
# Hint prompt (mid-conversation coaching from the critic agent).
# Used by utils.generate_hint().
