from string import Template

vignette_template = """# Basic patient information
- Patient name:
- Patient age, gender, height in cm, weight in kg:
- Patient ethnicity: African-American / Caucasian / Hispanic / Asian
- Results of previous physical surgeries relevant for the disease (e.g. amputation, tracheostomy, pacemaker, appendectomy …):
# Chief complaint
- Chief complaint:
	* In medical terms, concrete and detailed:
	* In layman's terms:
- First statement the patient will make after the introduction or in the response to the examinee's opening question:
# History of present illness / Symptoms
- History of Present Illness (OPQRST): 
- Aggravating factors: (what brings on the symptom?)
- Relieving factors: (what lessens the symptom?)
- Associated symptoms: (what else has occurred at the same time / what does the patient associate with the primary symptom?)
- If specifically asked: what does the patient think is going on with their health:
- If specifically asked: what is the patient's primary concern about the problem: 
# Past medical history
- Patient's response to \"how is your health in general?\":
- Hospitalizations (specify dates or patient age and location):
- Medical Illnesses / chronic problems (has the patient been under a doctor's care for anything? ):
- Past surgery (when?):
- Accidents or Injuries  (when?):
# Current medications
- Medications (include drug name, dose, schedule of use and length of time patient has been on the drug):
- Other forms of therapy tried (such as acupuncture, massage therapy, chiropractor):
# Allergies
- Medication (allergen, reaction):
- Environmental (allergen, reaction):
# Exposure History
- Chemical Toxins:
- Blood Transfusions:
# Immuniations
- Year of last tetanus vaccination
- Annual flu shot (yes/no):
- Other vaccinations received: 
# Preventive healthcare (specify how often this occurs (including never) and time of most recent visit)
- Primary care physician (how often / most recent):
- Emergency room (how often / most recent):
- Eye doctor (how often / most recent):
- Alternative therapy (how often / most recent):
- Others (how often / most recent):
 # Health Care Maintenance (most recent # of months / years ago / is the outcome normal or abnormal):
- PAP (most recent / outcome):
- Mammogram (most recent / outcome):
- Prostate exam (most recent / outcome):
- Cholestorol check (most recent / outcome):
- Colonoscopy (most recent / outcome (can specify further)):
- Others (most recent / outcome (can specify further)):
# Results of earlier tests concerning ongoing disease (imaging, blood values…) , if any:
- Tests (include which tests, test results, and descriptions of specialists that does not include diagnosis), if any:"""

generate_prompt_1_part1a = Template("Given is an EBM page about $disease_name.")
generate_prompt_1_part1b = Template("Given are EBM pages about $disease_name.")
generate_prompt_1_part2 = Template("""
```
$content
```

I will now reveal your final goal. Your goal, as an AI expert in the medical domain, is to create a patient vignette based on the information above, following a certain template.
Now as a second step: 
1. Reason about how you will change vignette of the patient that effectively has this disease to make the difficulty to diagnose the patient from the inherent $score to a $disease_difficulty/10.
2. State the difference with a $disease_difficulty_lower/10 (easier to diagnose) and a $disease_difficulty_upper/10 (harder to diagnose).
3. State in detail the typical incubation period for the symptoms.
4. Say exactly how long ago the patient in the vignette contracted the disease (a very specific time period, not a range in time!) after presenting to the clinic, considering the requested diagnostic difficulty score of $disease_difficulty/10. Take into account the incubation period for this!

Be concrete. Don't output anything else.""")

generate_prompt_2 = Template("""Now, fill in the following patient vignette template for a $disease_difficulty/10 difficulty. Be detailed, consistent and concrete. Strictly adhere to the details of the EBM page previously given, and additionally incorporate the previously mentioned elements, that you can also find on the EBM page. Strictly adhere to the vignette template. Be creative with the name.
                                              
```
$vignette
```
""")

generate_prompt_3 = Template("""Given is a patient vignette that has a current disease, possibly has some symptoms due to this and presents to the clinic. Spot inconsistencies within or between list elements of the vignette, regardless of the disease. Redundancy or irrelevancy is expected and is not an inconsistency: do not mention them. Adding list items is prohibited.

```
$markdown_block
```
""")

generate_prompt_4 = "Now think about **how** you want to change the incorrect elements in the patient vignette, if there are any. If none, state so. Redundancy or irrelevancy is expected and is not an inconsistency: do not change this. Adding or removing list items is prohibited."

generate_prompt_5 = "Now correct the patient vignette by changing only the inconsistencies. Leave the rest unchanged. Output the full vignette with changes."

generate_prompt_6 = Template("""Given is a patient vignette. The patient in the vignette needs a face and a voice. Pick the most appropriate face and voice from the list. Only output their names, not their descriptions.

Faces:
$faces

Voices:
$voices

```
$vignette
```
""")

