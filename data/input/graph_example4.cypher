// Identifying data
CREATE (idf:Category { name: "Identifying data" })
CREATE (patient_name:Subcategory { name: "patient name" })
CREATE (idf)-[:HAS_SUBCATEGORY]->(patient_name)
CREATE (blank_patient_name:Value { name: "blank", data_type: "string", range_candidate_guide: "None" })
CREATE (patient_name)-[:IS]->(blank_patient_name)

CREATE (age:Subcategory { name: "age" })
CREATE (idf)-[:HAS_SUBCATEGORY]->(age)
CREATE (blank_age:Value { name: "blank", data_type: "number", range_candidate_guide: "19-64" })
CREATE (age)-[:IS]->(blank_age)

CREATE (sex:Subcategory { name: "sex" })
CREATE (idf)-[:HAS_SUBCATEGORY]->(sex)
CREATE (blank_sex:Value { name: "blank", data_type: "string", range_candidate_guide: "male/female" })
CREATE (sex)-[:IS]->(blank_sex)

CREATE (marital_status:Subcategory { name: "marital status" })
CREATE (idf)-[:HAS_SUBCATEGORY]->(marital_status)
CREATE (blank_marital_status:Value { name: "blank", data_type: "string", range_candidate_guide: "single/married/divorced/widowed" })
CREATE (marital_status)-[:IS]->(blank_marital_status)

CREATE (occupation:Subcategory { name: "occupation" })
CREATE (idf)-[:HAS_SUBCATEGORY]->(occupation)
CREATE (blank_occupation:Value { name: "blank", data_type: "string", range_candidate_guide: "None" })
CREATE (occupation)-[:IS]->(blank_occupation)

// Chief complaint
CREATE (cc:Category { name: "Chief complaint" })
CREATE (cc_description:Subcategory { name: "cc_description" })
CREATE (cc)-[:HAS_SUBCATEGORY]->(cc_description)
CREATE (blank_cc_description:Value { name: "blank", data_type: "string", range_candidate_guide: "Describe in the patient's words" })
CREATE (cc_description)-[:IS]->(blank_cc_description)

// Present illness
CREATE (pi:Category { name: "Present illness" })
CREATE (pi_symptom:Subcategory { name: "pi_symptom_{n}" })
CREATE (pi)-[:HAS_SUBCATEGORY]->(pi_symptom)

CREATE (symptom_name:Attribute { name: "symptom_name" })
CREATE (blank_symptom_name:Value { name: "blank", data_type: "string", range_candidate_guide: "" })
CREATE (pi_symptom)-[:HAS_ATTRIBUTE]->(symptom_name)-[:IS]->(blank_symptom_name)

CREATE (length:Attribute { name: "length" })
CREATE (blank_length:Value { name: "blank", data_type: "number", range_candidate_guide: "0-24 (Unit: week, over 24 is represented as 24)" })
CREATE (pi_symptom)-[:HAS_ATTRIBUTE]->(length)-[:IS]->(blank_length)

CREATE (alleviating_factor:Attribute { name: "alleviating factor" })
CREATE (blank_alleviating_factor:Value { name: "blank", data_type: "string", range_candidate_guide: "None" })
CREATE (pi_symptom)-[:HAS_ATTRIBUTE]->(alleviating_factor)-[:IS]->(blank_alleviating_factor)

CREATE (exacerbating_factor:Attribute { name: "exacerbating factor" })
CREATE (blank_exacerbating_factor:Value { name: "blank", data_type: "string", range_candidate_guide: "None" })
CREATE (pi_symptom)-[:HAS_ATTRIBUTE]->(exacerbating_factor)-[:IS]->(blank_exacerbating_factor)

CREATE (triggering_factor:Subcategory { name: "triggering factor" })
CREATE (pi)-[:HAS_SUBCATEGORY]->(triggering_factor)
CREATE (blank_triggering_factor:Value { name: "blank", data_type: "string", range_candidate_guide: "The reason patient came to the hospital at this time" })
CREATE (triggering_factor)-[:IS]->(blank_triggering_factor)

CREATE (stressor:Subcategory { name: "stressor" })
CREATE (pi)-[:HAS_SUBCATEGORY]->(stressor)
CREATE (blank_stressor:Value { name: "blank", data_type: "string", range_candidate_guide: "(multiple answers available) home/work/school/legal issue/medical comorbidity/interpersonal difficulty/none" })
CREATE (stressor)-[:IS]->(blank_stressor)

// Past psychiatric history
CREATE (pph:Category { name: "Past psychiatric history" })
CREATE (presence:Subcategory { name: "presence" })
CREATE (pph)-[:HAS_SUBCATEGORY]->(presence)
CREATE (blank_presence:Value { name: "blank", data_type: "boolean", range_candidate_guide: "Randomize(50%) the presence or absence of past psychiatric history. If 'false', then remove all children of 'pph' except this 'presence' which has 'false' as a child." })
CREATE (presence)-[:IS]->(blank_presence)

CREATE (pph_diagnosis:Subcategory { name: "pph_diagnosis_{n}" })
CREATE (pph)-[:HAS_SUBCATEGORY]->(pph_diagnosis)

CREATE (diagnosis_name:Attribute { name: "diagnosis_name" })
CREATE (blank_diagnosis_name:Value { name: "blank", data_type: "string", range_candidate_guide: "" })
CREATE (pph_diagnosis)-[:HAS_ATTRIBUTE]->(diagnosis_name)-[:IS]->(blank_diagnosis_name)

CREATE ( WHEN :Attribute { name: "when" })
CREATE (blank_when:Value { name: "blank", data_type: "number", range_candidate_guide: "Enter the patient's age at the time of the event, not the date" })
CREATE (pph_diagnosis)-[:HAS_ATTRIBUTE]->( WHEN )-[:IS]->(blank_when)

CREATE (pph_length:Attribute { name: "length" })
CREATE (blank_pph_length:Value { name: "blank", data_type: "number", range_candidate_guide: "0-24 (Unit: week, over 24 is represented as 24)" })
CREATE (pph_diagnosis)-[:HAS_ATTRIBUTE]->(pph_length)-[:IS]->(blank_pph_length)

CREATE (frequency:Attribute { name: "frequency" })
CREATE (blank_frequency:Value { name: "blank", data_type: "number", range_candidate_guide: "number of episodes" })
CREATE (pph_diagnosis)-[:HAS_ATTRIBUTE]->(frequency)-[:IS]->(blank_frequency)

CREATE (severity:Attribute { name: "severity" })
CREATE (blank_severity:Value { name: "blank", data_type: "string", range_candidate_guide: "mild/moderate/severe" })
CREATE (pph_diagnosis)-[:HAS_ATTRIBUTE]->(severity)-[:IS]->(blank_severity)

CREATE (treatment_history_encounter:Subcategory { name: "treatment_history_encounter_{n}" })
CREATE (pph)-[:HAS_SUBCATEGORY]->(treatment_history_encounter)

CREATE (ecounter_type:Attribute { name: "ecounter_type" })
CREATE (blank_ecounter_type:Value { name: "blank", data_type: "string", range_candidate_guide: "outpatient clinic/day hospital/inpatient/vocational training" })
CREATE (treatment_history_encounter)-[:HAS_ATTRIBUTE]->(ecounter_type)-[:IS]->(blank_ecounter_type)

CREATE (modality:Attribute { name: "modality" })
CREATE (blank_modality:Value { name: "blank", data_type: "string", range_candidate_guide: "medication/CBT/psychotherapy/light therapy/biofeedback/ECT/group therapy/other" })
CREATE (treatment_history_encounter)-[:HAS_ATTRIBUTE]->(modality)-[:IS]->(blank_modality)

CREATE (effect:Attribute { name: "effect" })
CREATE (blank_effect:Value { name: "blank", data_type: "string", range_candidate_guide: "effective/partially effective/non-effective" })
CREATE (treatment_history_encounter)-[:HAS_ATTRIBUTE]->(effect)-[:IS]->(blank_effect)

CREATE (side_effect:Attribute { name: "side effect" })
CREATE (blank_side_effect:Value { name: "blank", data_type: "string", range_candidate_guide: "If there was a side effect, fill in this node. Otherwise, leave it as \"None\"." })
CREATE (treatment_history_encounter)-[:HAS_ATTRIBUTE]->(side_effect)-[:IS]->(blank_side_effect)

CREATE (reason_for_discontinuing:Attribute { name: "reason for discontinuing" })
CREATE (blank_reason_for_discontinuing:Value { name: "blank", data_type: "string", range_candidate_guide: "non-effective/financial problem/moving to new town/None (If there was discontinuing, fill in this node. Otherwise, leave it as \"None\".)" })
CREATE (treatment_history_encounter)-[:HAS_ATTRIBUTE]->(reason_for_discontinuing)-[:IS]->(blank_reason_for_discontinuing)

CREATE (compliance:Attribute { name: "compliance" })
CREATE (blank_compliance:Value { name: "blank", data_type: "string", range_candidate_guide: "good/bad" })
CREATE (treatment_history_encounter)-[:HAS_ATTRIBUTE]->(compliance)-[:IS]->(blank_compliance)

// Special rule: Create CAUSE_OF relationship
CREATE (pph_diagnosis)-[:CAUSE_OF]->(treatment_history_encounter)

// Past medical history
CREATE (pmh:Category { name: "Past medical history" })
CREATE (pmh_presence:Subcategory { name: "presence" })
CREATE (pmh)-[:HAS_SUBCATEGORY]->(pmh_presence)
CREATE (blank_pmh_presence:Value { name: "blank", data_type: "boolean", range_candidate_guide: "Randomize(50%) the presence or absence of past medical history. If 'false', then remove all children of 'pmh' except this 'presence' which has 'false' as a child." })
CREATE (pmh_presence)-[:IS]->(blank_pmh_presence)

CREATE (pmh_history:Subcategory { name: "pmh_history_{n}" })
CREATE (pmh)-[:HAS_SUBCATEGORY]->(pmh_history)
CREATE (blank_pmh_history:Value { name: "blank", data_type: "string", range_candidate_guide: "Describe a past medical history" })
CREATE (pmh_history)-[:IS]->(blank_pmh_history)

CREATE (current_medication:Subcategory { name: "current medication" })
CREATE (pmh)-[:HAS_SUBCATEGORY]->(current_medication)

CREATE (duration:Attribute { name: "duration" })
CREATE (blank_duration:Value { name: "blank", data_type: "number", range_candidate_guide: "Unit: week" })
CREATE (current_medication)-[:HAS_ATTRIBUTE]->(duration)-[:IS]->(blank_duration)

CREATE (med_compliance:Attribute { name: "compliance" })
CREATE (blank_med_compliance:Value { name: "blank", data_type: "string", range_candidate_guide: "good/bad" })
CREATE (current_medication)-[:HAS_ATTRIBUTE]->(med_compliance)-[:IS]->(blank_med_compliance)

CREATE (med_effect:Attribute { name: "effect" })
CREATE (blank_med_effect:Value { name: "blank", data_type: "string", range_candidate_guide: "effective/partially effective/non-effective" })
CREATE (current_medication)-[:HAS_ATTRIBUTE]->(med_effect)-[:IS]->(blank_med_effect)

CREATE (med_side_effect:Attribute { name: "side effect" })
CREATE (blank_med_side_effect:Value { name: "blank", data_type: "string", range_candidate_guide: "If there was a side effect, fill in this node. Otherwise, leave it as \"None\"." })
CREATE (current_medication)-[:HAS_ATTRIBUTE]->(med_side_effect)-[:IS]->(blank_med_side_effect)

// Family history
CREATE (fh:Category { name: "Family history" })
CREATE (fh_presence:Subcategory { name: "presence" })
CREATE (fh)-[:HAS_SUBCATEGORY]->(fh_presence)
CREATE (blank_fh_presence:Value { name: "blank", data_type: "boolean", range_candidate_guide: "Randomize(50%) the presence or absence of family history. If 'false', then remove all children of 'fh' except this 'presence' which has 'false' as a child." })
CREATE (fh_presence)-[:IS]->(blank_fh_presence)

CREATE (fh_diagnosis:Subcategory { name: "fh_diagnosis" })
CREATE (fh)-[:HAS_SUBCATEGORY]->(fh_diagnosis)
CREATE (blank_fh_diagnosis:Value { name: "blank", data_type: "string", range_candidate_guide: "Describe a psychiatric family history" })
CREATE (fh_diagnosis)-[:IS]->(blank_fh_diagnosis)

CREATE (fh_substance_use:Subcategory { name: "fh_substance_use" })
CREATE (fh)-[:HAS_SUBCATEGORY]->(fh_substance_use)
CREATE (blank_fh_substance_use:Value { name: "blank", data_type: "string", range_candidate_guide: "Describe a family history of substance use (alcohol, drugs, etc.)." })
CREATE (fh_substance_use)-[:IS]->(blank_fh_substance_use)

// Developmental/Social history
CREATE (dsh:Category { name: "Developmental/Social history" })
CREATE (abnormality:Subcategory { name: "abnormality in prenatal/birthing history" })
CREATE (dsh)-[:HAS_SUBCATEGORY]->(abnormality)
CREATE (blank_abnormality:Value { name: "blank", data_type: "string", range_candidate_guide: "Randomize presence/absence (50%). If yes, write a description; otherwise, enter None." })
CREATE (abnormality)-[:IS]->(blank_abnormality)

CREATE (delay:Subcategory { name: "delay in developmental milestone" })
CREATE (dsh)-[:HAS_SUBCATEGORY]->(delay)
CREATE (blank_delay:Value { name: "blank", data_type: "string", range_candidate_guide: "Randomize presence/absence (50%). If yes, write a description; otherwise, enter None." })
CREATE (delay)-[:IS]->(blank_delay)

CREATE (childhood_history:Subcategory { name: "childhood history" })
CREATE (dsh)-[:HAS_SUBCATEGORY]->(childhood_history)

CREATE (home_environment:Attribute { name: "home environment" })
CREATE (blank_home_environment:Value { name: "blank", data_type: "string", range_candidate_guide: "None" })
CREATE (childhood_history)-[:HAS_ATTRIBUTE]->(home_environment)-[:IS]->(blank_home_environment)

CREATE (members_of_family:Attribute { name: "members of family" })
CREATE (blank_members_of_family:Value { name: "blank", data_type: "string", range_candidate_guide: "None" })
CREATE (childhood_history)-[:HAS_ATTRIBUTE]->(members_of_family)-[:IS]->(blank_members_of_family)

CREATE (social_environment:Attribute { name: "social environment" })
CREATE (blank_social_environment:Value { name: "blank", data_type: "string", range_candidate_guide: "Describe things like number and quality of friends." })
CREATE (childhood_history)-[:HAS_ATTRIBUTE]->(social_environment)-[:IS]->(blank_social_environment)

CREATE (school_history:Subcategory { name: "school history" })
CREATE (dsh)-[:HAS_SUBCATEGORY]->(school_history)
CREATE (blank_school_history:Value { name: "blank", data_type: "string", range_candidate_guide: "special education/learning disorder/behavioral problem/low academic performance/problem in extracurricular activity" })
CREATE (school_history)-[:IS]->(blank_school_history)

CREATE (work_history:Subcategory { name: "work history" })
CREATE (dsh)-[:HAS_SUBCATEGORY]->(work_history)
CREATE (blank_work_history:Value { name: "blank", data_type: "string", range_candidate_guide: "Describe things like job, performance, reason for switching jobs, relationship with supervisor, coworker, etc." })
CREATE (work_history)-[:IS]->(blank_work_history)

// Marriage/relationship history
CREATE (mrh:Category { name: "Marriage/relationship history" })
CREATE (current_family_structure:Subcategory { name: "current family structure" })
CREATE (mrh)-[:HAS_SUBCATEGORY]->(current_family_structure)
CREATE (blank_current_family_structure:Value { name: "blank", data_type: "string", range_candidate_guide: "None" })
CREATE (current_family_structure)-[:IS]->(blank_current_family_structure)

// Mental Status Examination
CREATE (mse:Category { name: "Mental Status Examination" })

CREATE (general_attitude:Subcategory { name: "General attitude" })
CREATE (mse)-[:HAS_SUBCATEGORY]->(general_attitude)
CREATE (blank_general_attitude:Value { name: "blank", data_type: "string", range_candidate_guide: "None" })
CREATE (general_attitude)-[:IS]->(blank_general_attitude)

CREATE (appearance:Subcategory { name: "Appearance" })
CREATE (mse)-[:HAS_SUBCATEGORY]->(appearance)
CREATE (blank_appearance:Value { name: "blank", data_type: "string", range_candidate_guide: "None" })
CREATE (appearance)-[:IS]->(blank_appearance)

CREATE (behavior:Subcategory { name: "Behavior" })
CREATE (mse)-[:HAS_SUBCATEGORY]->(behavior)
CREATE (blank_behavior:Value { name: "blank", data_type: "string", range_candidate_guide: "None" })
CREATE (behavior)-[:IS]->(blank_behavior)

CREATE (mood:Subcategory { name: "mood" })
CREATE (mse)-[:HAS_SUBCATEGORY]->(mood)
CREATE (blank_mood:Value { name: "blank", data_type: "string", range_candidate_guide: "euphoric/elated/euthymic/dysphoric/depressed" })
CREATE (mood)-[:IS]->(blank_mood)

CREATE (affect:Subcategory { name: "affect" })
CREATE (mse)-[:HAS_SUBCATEGORY]->(affect)
CREATE (blank_affect:Value { name: "blank", data_type: "string", range_candidate_guide: "broad/restricted/blunt/flat/labile/anxious/tense/shallow/inadequate/inappropriate" })
CREATE (affect)-[:IS]->(blank_affect)

CREATE (speech_characteristic:Subcategory { name: "speech characteristic" })
CREATE (mse)-[:HAS_SUBCATEGORY]->(speech_characteristic)

CREATE (spontaneity:Attribute { name: "Spontaneity" })
CREATE (blank_spontaneity:Value { name: "blank", data_type: "boolean", range_candidate_guide: "None" })
CREATE (speech_characteristic)-[:HAS_ATTRIBUTE]->(spontaneity)-[:IS]->(blank_spontaneity)

CREATE (verbal_productivity:Attribute { name: "Verbal productivity" })
CREATE (blank_verbal_productivity:Value { name: "blank", data_type: "string", range_candidate_guide: "increased/moderate/decreased" })
CREATE (speech_characteristic)-[:HAS_ATTRIBUTE]->(verbal_productivity)-[:IS]->(blank_verbal_productivity)

CREATE (tone_of_voice:Attribute { name: "Tone of voice" })
CREATE (blank_tone_of_voice:Value { name: "blank", data_type: "string", range_candidate_guide: "increased/moderate/decreased" })
CREATE (speech_characteristic)-[:HAS_ATTRIBUTE]->(tone_of_voice)-[:IS]->(blank_tone_of_voice)

CREATE (perception:Subcategory { name: "perception" })
CREATE (mse)-[:HAS_SUBCATEGORY]->(perception)
CREATE (blank_perception:Value { name: "blank", data_type: "boolean", range_candidate_guide: "Describe the perception problem (Illusion, Auditory hallucination, Visual hallucination, Olfactory hallucination, Gustatory hallucination, Depersonalization, Derealization, Déjà vu, Jamais vu). If none, enter None." })
CREATE (perception)-[:IS]->(blank_perception)

CREATE (thought_process:Subcategory { name: "thought process" })
CREATE (mse)-[:HAS_SUBCATEGORY]->(thought_process)
CREATE (blank_thought_process:Value { name: "blank", data_type: "boolean", range_candidate_guide: "Describe the thought process (Loosening of association, flight of idea, circumstantiality, tangentiality, Word salad or incoherence, Neologism, logicality, relevancy). If normal, enter Normal." })
CREATE (thought_process)-[:IS]->(blank_thought_process)

CREATE (thought_content:Subcategory { name: "thought content" })
CREATE (mse)-[:HAS_SUBCATEGORY]->(thought_content)
CREATE (blank_thought_content:Value { name: "blank", data_type: "boolean", range_candidate_guide: "Describe the Thought content (preoccupation, overvalued idea, idea of referecne, grandiosity, obsession, compulsion, rumination, delusion, phobia). If normal, enter Normal." })
CREATE (thought_content)-[:IS]->(blank_thought_content)

CREATE (sensorium_and_cognition:Subcategory { name: "sensorium and cognition" })
CREATE (mse)-[:HAS_SUBCATEGORY]->(sensorium_and_cognition)

CREATE (mental_status:Attribute { name: "mental status" })
CREATE (blank_mental_status:Value { name: "blank", data_type: "string", range_candidate_guide: "alert/drowsy/stupor/coma" })
CREATE (sensorium_and_cognition)-[:HAS_ATTRIBUTE]->(mental_status)-[:IS]->(blank_mental_status)

CREATE (time_orientation:Attribute { name: "time_orientation" })
CREATE (blank_time_orientation:Value { name: "blank", data_type: "boolean (normal/impaired)", range_candidate_guide: "None" })
CREATE (sensorium_and_cognition)-[:HAS_ATTRIBUTE]->(time_orientation)-[:IS]->(blank_time_orientation)

CREATE (place_orientation:Attribute { name: "place_orientation" })
CREATE (blank_place_orientation:Value { name: "blank", data_type: "boolean (normal/impaired)", range_candidate_guide: "None" })
CREATE (sensorium_and_cognition)-[:HAS_ATTRIBUTE]->(place_orientation)-[:IS]->(blank_place_orientation)

CREATE (person_orientation:Attribute { name: "person_orientation" })
CREATE (blank_person_orientation:Value { name: "blank", data_type: "boolean (normal/impaired)", range_candidate_guide: "None" })
CREATE (sensorium_and_cognition)-[:HAS_ATTRIBUTE]->(person_orientation)-[:IS]->(blank_person_orientation)

CREATE (immediate_memory:Attribute { name: "immediate_memory" })
CREATE (blank_immediate_memory:Value { name: "blank", data_type: "boolean (normal/impaired)", range_candidate_guide: "None" })
CREATE (sensorium_and_cognition)-[:HAS_ATTRIBUTE]->(immediate_memory)-[:IS]->(blank_immediate_memory)

CREATE (recent_memory:Attribute { name: "recent_memory" })
CREATE (blank_recent_memory:Value { name: "blank", data_type: "boolean (normal/impaired)", range_candidate_guide: "None" })
CREATE (sensorium_and_cognition)-[:HAS_ATTRIBUTE]->(recent_memory)-[:IS]->(blank_recent_memory)

CREATE (remote_memory:Attribute { name: "remote_memory" })
CREATE (blank_remote_memory:Value { name: "blank", data_type: "boolean (normal/impaired)", range_candidate_guide: "None" })
CREATE (sensorium_and_cognition)-[:HAS_ATTRIBUTE]->(remote_memory)-[:IS]->(blank_remote_memory)

CREATE (concentration_and_calculation:Attribute { name: "problem in concentration and calculation(7 serial test)" })
CREATE (blank_concentration_and_calculation:Value { name: "blank", data_type: "boolean (normal/impaired)", range_candidate_guide: "None" })
CREATE (sensorium_and_cognition)-[:HAS_ATTRIBUTE]->(concentration_and_calculation)-[:IS]->(blank_concentration_and_calculation)

CREATE (general_information:Attribute { name: "abnormality in general information(past five presidents/capitals of 5 country)" })
CREATE (blank_general_information:Value { name: "blank", data_type: "boolean (normal/impaired)", range_candidate_guide: "None" })
CREATE (sensorium_and_cognition)-[:HAS_ATTRIBUTE]->(general_information)-[:IS]->(blank_general_information)

CREATE (abstract_thinking:Attribute { name: "abstract thinking(understanding of idioms)" })
CREATE (blank_abstract_thinking:Value { name: "blank", data_type: "boolean (normal/impaired)", range_candidate_guide: "None" })
CREATE (sensorium_and_cognition)-[:HAS_ATTRIBUTE]->(abstract_thinking)-[:IS]->(blank_abstract_thinking)

CREATE (impulsivity_suicide_risk:Attribute { name: "impulsivity-suicde risk" })
CREATE (blank_impulsivity_suicide_risk:Value { name: "blank", data_type: "string", range_candidate_guide: "high/moderate/low" })
CREATE (sensorium_and_cognition)-[:HAS_ATTRIBUTE]->(impulsivity_suicide_risk)-[:IS]->(blank_impulsivity_suicide_risk)

CREATE (impulsivity_self_mutilating:Attribute { name: "impulsivity-self mutilating behavior risk" })
CREATE (blank_impulsivity_self_mutilating:Value { name: "blank", data_type: "string", range_candidate_guide: "None" })
CREATE (sensorium_and_cognition)-[:HAS_ATTRIBUTE]->(impulsivity_self_mutilating)-[:IS]->(blank_impulsivity_self_mutilating)

CREATE (suicidal_ideation:Attribute { name: "suicidal ideation" })
CREATE (blank_suicidal_ideation:Value { name: "blank", data_type: "boolean", range_candidate_guide: "None" })
CREATE (sensorium_and_cognition)-[:HAS_ATTRIBUTE]->(suicidal_ideation)-[:IS]->(blank_suicidal_ideation)

CREATE (suicidal_plan:Attribute { name: "suicidal plan" })
CREATE (blank_suicidal_plan:Value { name: "blank", data_type: "boolean", range_candidate_guide: "None" })
CREATE (sensorium_and_cognition)-[:HAS_ATTRIBUTE]->(suicidal_plan)-[:IS]->(blank_suicidal_plan)

CREATE (suicidal_attempt:Attribute { name: "suicidal attempt" })
CREATE (blank_suicidal_attempt:Value { name: "blank", data_type: "boolean", range_candidate_guide: "None" })
CREATE (sensorium_and_cognition)-[:HAS_ATTRIBUTE]->(suicidal_attempt)-[:IS]->(blank_suicidal_attempt)

CREATE (impulsivity_homicide:Attribute { name: "impulsivity-homicide" })
CREATE (blank_impulsivity_homicide:Value { name: "blank", data_type: "string", range_candidate_guide: "high/moderate/low" })
CREATE (sensorium_and_cognition)-[:HAS_ATTRIBUTE]->(impulsivity_homicide)-[:IS]->(blank_impulsivity_homicide)

CREATE (social_judgement:Attribute { name: "social judgement" })
CREATE (blank_social_judgement:Value { name: "blank", data_type: "boolean (normal/impaired)", range_candidate_guide: "None" })
CREATE (sensorium_and_cognition)-[:HAS_ATTRIBUTE]->(social_judgement)-[:IS]->(blank_social_judgement)

CREATE (insight:Attribute { name: "insight" })
CREATE (blank_insight:Value { name: "blank", data_type: "string", range_candidate_guide: "Complete denial of illness/Slight awareness of being sick and needing help, but denying it at the same time/Awareness of being sick but blaming it on others, external events/Intellectual insight./True emotional insight." })
CREATE (sensorium_and_cognition)-[:HAS_ATTRIBUTE]->(insight)-[:IS]->(blank_insight)

CREATE (reliability:Attribute { name: "reliability" })
CREATE (blank_reliability:Value { name: "blank", data_type: "boolean", range_candidate_guide: "" })
CREATE (sensorium_and_cognition)-[:HAS_ATTRIBUTE]->(reliability)-[:IS]->(blank_reliability)

// Create the Patient node
CREATE (pat:Person { name: "Patient" })

// Use WITH to pass the patient node to the next part of the query
WITH pat

// Match all nodes with the Category label and create a relationship to the Patient node
MATCH (cat:Category)
CREATE (pat)-[:HAS_CATEGORY]->(cat)

// Use WITH again to pass all variables to the final MATCH
WITH pat, cat

// Return the Patient node and its relationships for verification
MATCH (pat)-[r:HAS_CATEGORY]->(cat)
RETURN pat, r, cat
