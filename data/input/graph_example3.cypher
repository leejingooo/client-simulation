// Identifying data
CREATE (idf:Category { name: "Identifying data" })
CREATE (patient_name:Subcategory { name: "patient name" })
CREATE (idf)-[:HAS_SUBCATEGORY]->(patient_name)
CREATE (patient_name_value:Value { name: "blank", data_type: "string", range_candidate_guide: "None" })
CREATE (patient_name)-[:IS]->(patient_name_value);

CREATE (age:Subcategory { name: "age" })
CREATE (idf)-[:HAS_SUBCATEGORY]->(age)
CREATE (age_value:Value { name: "blank", data_type: "number", range_candidate_guide: "19-64" })
CREATE (age)-[:IS]->(age_value);

CREATE (sex:Subcategory { name: "sex" })
CREATE (idf)-[:HAS_SUBCATEGORY]->(sex)
CREATE (sex_value:Value { name: "blank", data_type: "string", range_candidate_guide: "male/female" })
CREATE (sex)-[:IS]->(sex_value);

CREATE (marital_status:Subcategory { name: "marital status" })
CREATE (idf)-[:HAS_SUBCATEGORY]->(marital_status)
CREATE (marital_status_value:Value { name: "blank", data_type: "string", range_candidate_guide: "single/married/divorced/widowed" })
CREATE (marital_status)-[:IS]->(marital_status_value);

CREATE (occupation:Subcategory { name: "occupation" })
CREATE (idf)-[:HAS_SUBCATEGORY]->(occupation)
CREATE (occupation_value:Value { name: "blank", data_type: "string", range_candidate_guide: "None" })
CREATE (occupation)-[:IS]->(occupation_value);

// Chief complaint
CREATE (cc:Category { name: "Chief complaint" })
CREATE (cc_description:Subcategory { name: "cc_description" })
CREATE (cc)-[:HAS_SUBCATEGORY]->(cc_description)
CREATE (cc_description_value:Value { name: "blank", data_type: "string", range_candidate_guide: "Describe in the patient's words" })
CREATE (cc_description)-[:IS]->(cc_description_value);

// Present illness
CREATE (pi:Category { name: "Present illness" })
CREATE (pi_symptom:Subcategory { name: "pi_symptom_{n}" })
CREATE (pi)-[:HAS_SUBCATEGORY]->(pi_symptom)
CREATE (description:Attribute { name: "description" })
CREATE (pi_symptom)-[:HAS_ATTRIBUTE]->(description)
CREATE (description_value:Value { name: "blank", data_type: "string", range_candidate_guide: "Describe the patient's psychiatric symptoms (e.g. depression, anxiety, psychosis...)." })
CREATE (description)-[:IS]->(description_value);

CREATE (length:Attribute { name: "length" })
CREATE (pi_symptom)-[:HAS_ATTRIBUTE]->(length)
CREATE (length_value:Value { name: "blank", data_type: "number", range_candidate_guide: "0-24 (Unit: week, over 24 is represented as 24)" })
CREATE (length)-[:IS]->(length_value);

CREATE (alleviating_factor:Attribute { name: "alleviating factor" })
CREATE (pi_symptom)-[:HAS_ATTRIBUTE]->(alleviating_factor)
CREATE (alleviating_factor_value:Value { name: "blank", data_type: "string", range_candidate_guide: "None" })
CREATE (alleviating_factor)-[:IS]->(alleviating_factor_value);

CREATE (exacerbating_factor:Attribute { name: "exacerbating factor" })
CREATE (pi_symptom)-[:HAS_ATTRIBUTE]->(exacerbating_factor)
CREATE (exacerbating_factor_value:Value { name: "blank", data_type: "string", range_candidate_guide: "None" })
CREATE (exacerbating_factor)-[:IS]->(exacerbating_factor_value);

CREATE (triggering_factor:Subcategory { name: "triggering factor" })
CREATE (pi)-[:HAS_SUBCATEGORY]->(triggering_factor)
CREATE (triggering_factor_value:Value { name: "blank", data_type: "string", range_candidate_guide: "The reason patient came to the hospital at this time" })
CREATE (triggering_factor)-[:IS]->(triggering_factor_value);

CREATE (stressor:Subcategory { name: "stressor" })
CREATE (pi)-[:HAS_SUBCATEGORY]->(stressor)
CREATE (stressor_value:Value { name: "blank", data_type: "string", range_candidate_guide: "(multiple answers available) home/work/school/legal issue/medical comorbidity/interpersonal difficulty/none" })
CREATE (stressor)-[:IS]->(stressor_value);

// Past psychiatric history
CREATE (pph:Category { name: "Past psychiatric history" })
CREATE (pph)-[:HAS_SUBCATEGORY]->(pph_presence:Subcategory { name: "presence" })
CREATE (pph_presence)-[:IS]->(pph_presence_value:Value { name: "blank", data_type: "boolean", range_candidate_guide: "Randomize(50%) the presence or absence of past psychiatric history. If 'false', then remove all children of 'pph' except this 'presence' which has 'false' as a child." });

CREATE (pph)-[:HAS_SUBCATEGORY]->(pph_diagnosis:Subcategory { name: "pph_diagnosis_{n}" })
CREATE (pph_diagnosis)-[:HAS_ATTRIBUTE]->(pph_diagnosis_desc:Attribute { name: "description" })
CREATE (pph_diagnosis_desc)-[:IS]->(pph_diagnosis_desc_value:Value { name: "blank", data_type: "string", range_candidate_guide: "" });

CREATE (pph_diagnosis)-[:HAS_ATTRIBUTE]->(pph_diagnosis_when:Attribute { name: "when" })
CREATE (pph_diagnosis_when)-[:IS]->(pph_diagnosis_when_value:Value { name: "blank", data_type: "number", range_candidate_guide: "Enter the patient's age at the time of the event, not the date" });

CREATE (pph_diagnosis)-[:HAS_ATTRIBUTE]->(pph_diagnosis_length:Attribute { name: "length" })
CREATE (pph_diagnosis_length)-[:IS]->(pph_diagnosis_length_value:Value { name: "blank", data_type: "number", range_candidate_guide: "0-24 (Unit: week, over 24 is represented as 24)" });

CREATE (pph_diagnosis)-[:HAS_ATTRIBUTE]->(pph_diagnosis_frequency:Attribute { name: "frequency" })
CREATE (pph_diagnosis_frequency)-[:IS]->(pph_diagnosis_frequency_value:Value { name: "blank", data_type: "number", range_candidate_guide: "number of episodes" });

CREATE (pph_diagnosis)-[:HAS_ATTRIBUTE]->(pph_diagnosis_severity:Attribute { name: "severity" })
CREATE (pph_diagnosis_severity)-[:IS]->(pph_diagnosis_severity_value:Value { name: "blank", data_type: "string", range_candidate_guide: "mild/moderate/severe" });

CREATE (pph)-[:HAS_SUBCATEGORY]->(treatment_history:Subcategory { name: "treatment_history_encounter_{n}" })
CREATE (pph_diagnosis)-[:CAUSE_OF]->(treatment_history)
CREATE (treatment_history)-[:HAS_ATTRIBUTE]->(encounter_type:Attribute { name: "ecounter_type" })
CREATE (encounter_type)-[:IS]->(encounter_type_value:Value { name: "blank", data_type: "string", range_candidate_guide: "outpatient clinic/day hospital/inpatient/vocational training" });

CREATE (treatment_history)-[:HAS_ATTRIBUTE]->(modality:Attribute { name: "modality" })
CREATE (modality)-[:IS]->(modality_value:Value { name: "blank", data_type: "string", range_candidate_guide: "medication/CBT/psychotherapy/light therapy/biofeedback/ECT/group therapy/other" });

CREATE (treatment_history)-[:HAS_ATTRIBUTE]->(effect:Attribute { name: "effect" })
CREATE (effect)-[:IS]->(effect_value:Value { name: "blank", data_type: "string", range_candidate_guide: "effective/partially effective/non-effective" });

CREATE (treatment_history)-[:HAS_ATTRIBUTE]->(side_effect:Attribute { name: "side effect" })
CREATE (side_effect)-[:IS]->(side_effect_value:Value { name: "blank", data_type: "string", range_candidate_guide: "If there was a side effect, fill in this node. Otherwise, leave it as \"None\"." });

CREATE (treatment_history)-[:HAS_ATTRIBUTE]->(reason_discontinuing:Attribute { name: "reason for discontinuing" })
CREATE (reason_discontinuing)-[:IS]->(reason_discontinuing_value:Value { name: "blank", data_type: "string", range_candidate_guide: "non-effective/financial problem/moving to new town/None (If there was discontinuing, fill in this node. Otherwise, leave it as \"None\".)" });

CREATE (treatment_history)-[:HAS_ATTRIBUTE]->(compliance:Attribute { name: "compliance" })
CREATE (compliance)-[:IS]->(compliance_value:Value { name: "blank", data_type: "string", range_candidate_guide: "good/bad" });

// Past medical history
CREATE (pmh:Category { name: "Past medical history" })
CREATE (pmh)-[:HAS_SUBCATEGORY]->(pmh_presence:Subcategory { name: "presence" })
CREATE (pmh_presence)-[:IS]->(pmh_presence_value:Value { name: "blank", data_type: "boolean", range_candidate_guide: "Randomize(50%) the presence or absence of past medical history. If 'false', then remove all children of 'pmh' except this 'presence' which has 'false' as a child." });

CREATE (pmh)-[:HAS_SUBCATEGORY]->(pmh_history:Subcategory { name: "pmh_history_{n}" })
CREATE (pmh_history)-[:IS]->(pmh_history_value:Value { name: "blank", data_type: "string", range_candidate_guide: "Describe a past medical history" });

CREATE (pmh)-[:HAS_SUBCATEGORY]->(current_medication:Subcategory { name: "current medication" })
CREATE (current_medication)-[:HAS_ATTRIBUTE]->(med_duration:Attribute { name: "duration" })
CREATE (med_duration)-[:IS]->(med_duration_value:Value { name: "blank", data_type: "number", range_candidate_guide: "Unit: week" });

CREATE (current_medication)-[:HAS_ATTRIBUTE]->(med_compliance:Attribute { name: "compliance" })
CREATE (med_compliance)-[:IS]->(med_compliance_value:Value { name: "blank", data_type: "string", range_candidate_guide: "good/bad" });

CREATE (current_medication)-[:HAS_ATTRIBUTE]->(med_effect:Attribute { name: "effect" })
CREATE (med_effect)-[:IS]->(med_effect_value:Value { name: "blank", data_type: "string", range_candidate_guide: "effective/partially effective/non-effective" });

CREATE (current_medication)-[:HAS_ATTRIBUTE]->(med_side_effect:Attribute { name: "side effect" })
CREATE (med_side_effect)-[:IS]->(med_side_effect_value:Value { name: "blank", data_type: "string", range_candidate_guide: "If there was a side effect, fill in this node. Otherwise, leave it as \"None\"." });

// Family history
CREATE (fh:Category { name: "Family history" })
CREATE (fh)-[:HAS_SUBCATEGORY]->(fh_presence:Subcategory { name: "presence" })
CREATE (fh_presence)-[:IS]->(fh_presence_value:Value { name: "blank", data_type: "boolean", range_candidate_guide: "Randomize(50%) the presence or absence of family history. If 'false', then remove all children of 'fh' except this 'presence' which has 'false' as a child." });

CREATE (fh)-[:HAS_SUBCATEGORY]->(fh_diagnosis:Subcategory { name: "fh_diagnosis" })
CREATE (fh_diagnosis)-[:IS]->(fh_diagnosis_value:Value { name: "blank", data_type: "string", range_candidate_guide: "Describe a psychiatric family history" });

CREATE (fh)-[:HAS_SUBCATEGORY]->(fh_substance_use:Subcategory { name: "fh_substance_use" })
CREATE (fh_substance_use)-[:IS]->(fh_substance_use_value:Value { name: "blank", data_type: "string", range_candidate_guide: "Describe a family history of substance use (alcohol, drugs, etc.)." });

// Developmental/Social history
CREATE (dsh:Category { name: "Developmental/Social history" })
CREATE (dsh)-[:HAS_SUBCATEGORY]->(abnormality:Subcategory { name: "abnormality in prenatal/birthing history" })
CREATE (abnormality)-[:IS]->(abnormality_value:Value { name: "blank", data_type: "string", range_candidate_guide: "Randomize presence/absence (50%). If yes, write a description; otherwise, enter None." });

CREATE (dsh)-[:HAS_SUBCATEGORY]->(delay:Subcategory { name: "delay in developmental milestone" })
CREATE (delay)-[:IS]->(delay_value:Value { name: "blank", data_type: "string", range_candidate_guide: "Randomize presence/absence (50%). If yes, write a description; otherwise, enter None." });

CREATE (dsh)-[:HAS_SUBCATEGORY]->(childhood_history:Subcategory { name: "childhood history" })
CREATE (childhood_history)-[:HAS_ATTRIBUTE]->(home_env:Attribute { name: "home environment" })
CREATE (home_env)-[:IS]->(home_env_value:Value { name: "blank", data_type: "string", range_candidate_guide: "" });

CREATE (childhood_history)-[:HAS_ATTRIBUTE]->(family_members:Attribute { name: "members of family" })
CREATE (family_members)-[:IS]->(family_members_value:Value { name: "blank", data_type: "string", range_candidate_guide: "" });

CREATE (childhood_history)-[:HAS_ATTRIBUTE]->(social_env:Attribute { name: "social environment" })
CREATE (social_env)-[:IS]->(social_env_value:Value { name: "blank", data_type: "string", range_candidate_guide: "Describe things like number and quality of friends." });

CREATE (dsh)-[:HAS_SUBCATEGORY]->(school_history:Subcategory { name: "school hisotry" })
CREATE (school_history)-[:IS]->(school_history_value:Value { name: "blank", data_type: "string", range_candidate_guide: "special education/learning disorder/behavioral problem/low academic performance/problem in extracurricular activity" });

CREATE (dsh)-[:HAS_SUBCATEGORY]->(work_history:Subcategory { name: "work history" })
CREATE (work_history)-[:IS]->(work_history_value:Value { name: "blank", data_type: "string", range_candidate_guide: "Describe things like job, performance, reason for switching jobs, relationship with supervisor, coworker, etc." });

// Marriage/relationship history
CREATE (mrh:Category { name: "Marriage/relationship hisotry" })
CREATE (mrh)-[:HAS_SUBCATEGORY]->(family_structure:Subcategory { name: "current family structure" })
CREATE (family_structure)-[:IS]->(family_structure_value:Value { name: "blank", data_type: "string", range_candidate_guide: "" });

// Mental Status Examination
CREATE (mse:Category { name: "Mental Status Examination" })
CREATE (mse)-[:HAS_SUBCATEGORY]->(general_attitude:Subcategory { name: "General attitude" })
CREATE (general_attitude)-[:IS]->(general_attitude_value:Value { name: "blank", data_type: "string", range_candidate_guide: "" });

CREATE (mse)-[:HAS_SUBCATEGORY]->(appearance:Subcategory { name: "Apperance" })
CREATE (appearance)-[:IS]->(appearance_value:Value { name: "blank", data_type: "string", range_candidate_guide: "" });

CREATE (mse)-[:HAS_SUBCATEGORY]->(behavior:Subcategory { name: "Behavior" })
CREATE (behavior)-[:IS]->(behavior_value:Value { name: "blank", data_type: "string", range_candidate_guide: "" });

CREATE (mse)-[:HAS_SUBCATEGORY]->(mood:Subcategory { name: "mood" })
CREATE (mood)-[:IS]->(mood_value:Value { name: "blank", data_type: "string", range_candidate_guide: "euphoric/elated/euthymic/dysphoric/depressed" });

CREATE (mse)-[:HAS_SUBCATEGORY]->(affect:Subcategory { name: "affect" })
CREATE (affect)-[:IS]->(affect_value:Value { name: "blank", data_type: "string", range_candidate_guide: "broad/restricted/blunt/flat/labile/anxious/tense/shallow/inadequate/inappropriate" });

CREATE (mse)-[:HAS_SUBCATEGORY]->(speech_characteristic:Subcategory { name: "speech characteristic" })
CREATE (speech_characteristic)-[:HAS_ATTRIBUTE]->(spontaneity:Attribute { name: "Spontaneity" })
CREATE (spontaneity)-[:IS]->(spontaneity_value:Value { name: "blank", data_type: "boolean", range_candidate_guide: "" });

CREATE (speech_characteristic)-[:HAS_ATTRIBUTE]->(verbal_productivity:Attribute { name: "Verbal productivity" })
CREATE (verbal_productivity)-[:IS]->(verbal_productivity_value:Value { name: "blank", data_type: "string", range_candidate_guide: "increased/moderate/decreased" });

CREATE (speech_characteristic)-[:HAS_ATTRIBUTE]->(tone_of_voice:Attribute { name: "Tone of voice" })
CREATE (tone_of_voice)-[:IS]->(tone_of_voice_value:Value { name: "blank", data_type: "string", range_candidate_guide: "increased/moderate/decreased" });

CREATE (mse)-[:HAS_SUBCATEGORY]->(perception:Subcategory { name: "perception" })
CREATE (perception)-[:IS]->(perception_value:Value { name: "blank", data_type: "boolean", range_candidate_guide: "Describe the perception problem (Illusion, Auditory hallucination, Visual hallucination, Olfactory hallucination, Gustatory hallucination, Depersonalization, Derealization, Déjà vu, Jamais vu). If none, enter None." });

CREATE (mse)-[:HAS_SUBCATEGORY]->(thought_process:Subcategory { name: "thought process" })
CREATE (thought_process)-[:IS]->(thought_process_value:Value { name: "blank", data_type: "boolean", range_candidate_guide: "Describe the thought process (Loosening of association, flight of idea, circumstantiality, tangentiality, Word salad or incoherence, Neologism, logicality, relevancy). If normal, enter Normal." });

CREATE (mse)-[:HAS_SUBCATEGORY]->(thought_content:Subcategory { name: "thought content" })
CREATE (thought_content)-[:IS]->(thought_content_value:Value { name: "blank", data_type: "boolean", range_candidate_guide: "Describe the Thought content (preoccupation, overvalued idea, idea of referecne, grandiosity, obsession, compulsion, rumination, delusion, phobia). If normal, enter Normal." });

CREATE (mse)-[:HAS_SUBCATEGORY]->(sensorium_cognition:Subcategory { name: "sensorium and cognition" })
CREATE (sensorium_cognition)-[:HAS_ATTRIBUTE]->(mental_status:Attribute { name: "mental status" })
CREATE (mental_status)-[:IS]->(mental_status_value:Value { name: "blank", data_type: "string", range_candidate_guide: "alert/drowsy/stupor/coma" });

CREATE (sensorium_cognition)-[:HAS_ATTRIBUTE]->(time_orientation:Attribute { name: "time_orientation" })
CREATE (time_orientation)-[:IS]->(time_orientation_value:Value { name: "blank", data_type: "boolean (normal/impaired)", range_candidate_guide: "" });

CREATE (sensorium_cognition)-[:HAS_ATTRIBUTE]->(place_orientation:Attribute { name: "place_orientation" })
CREATE (place_orientation)-[:IS]->(place_orientation_value:Value { name: "blank", data_type: "boolean (normal/impaired)", range_candidate_guide: "" });

CREATE (sensorium_cognition)-[:HAS_ATTRIBUTE]->(person_orientation:Attribute { name: "person_orientation" })
CREATE (person_orientation)-[:IS]->(person_orientation_value:Value { name: "blank", data_type: "boolean (normal/impaired)", range_candidate_guide: "" });

CREATE (sensorium_cognition)-[:HAS_ATTRIBUTE]->(immediate_memory:Attribute { name: "immediate_memory" })
CREATE (immediate_memory)-[:IS]->(immediate_memory_value:Value { name: "blank", data_type: "boolean (normal/impaired)", range_candidate_guide: "" });

CREATE (sensorium_cognition)-[:HAS_ATTRIBUTE]->(recent_memory:Attribute { name: "recent_memory" })
CREATE (recent_memory)-[:IS]->(recent_memory_value:Value { name: "blank", data_type: "boolean (normal/impaired)", range_candidate_guide: "" });

CREATE (sensorium_cognition)-[:HAS_ATTRIBUTE]->(remote_memory:Attribute { name: "remote_memory" })
CREATE (remote_memory)-[:IS]->(remote_memory_value:Value { name: "blank", data_type: "boolean (normal/impaired)", range_candidate_guide: "" });

CREATE (sensorium_cognition)-[:HAS_ATTRIBUTE]->(concentration_calculation:Attribute { name: "problem in concentration and calculation(7 serial test)" })
CREATE (concentration_calculation)-[:IS]->(concentration_calculation_value:Value { name: "blank", data_type: "boolean (normal/impaired)", range_candidate_guide: "" });

CREATE (sensorium_cognition)-[:HAS_ATTRIBUTE]->(general_information:Attribute { name: "abnormality in general information(past five presidents/capitals of 5 country)" })
CREATE (general_information)-[:IS]->(general_information_value:Value { name: "blank", data_type: "boolean (normal/impaired)", range_candidate_guide: "" });

CREATE (sensorium_cognition)-[:HAS_ATTRIBUTE]->(abstract_thinking:Attribute { name: "abstract thinking(understanding of idioms)" })
CREATE (abstract_thinking)-[:IS]->(abstract_thinking_value:Value { name: "blank", data_type: "boolean (normal/impaired)", range_candidate_guide: "" });

CREATE (sensorium_cognition)-[:HAS_ATTRIBUTE]->(impulsivity_suicide:Attribute { name: "impulsivity-suicde risk" })
CREATE (impulsivity_suicide)-[:IS]->(impulsivity_suicide_value:Value { name: "blank", data_type: "string", range_candidate_guide: "high/moderate/low" });

CREATE (sensorium_cognition)-[:HAS_ATTRIBUTE]->(impulsivity_self_mutilating:Attribute { name: "impulsivity-self mutilating behavior risk" })
CREATE (impulsivity_self_mutilating)-[:IS]->(impulsivity_self_mutilating_value:Value { name: "blank", data_type: "string", range_candidate_guide: "" });

CREATE (sensorium_cognition)-[:HAS_ATTRIBUTE]->(suicidal_ideation:Attribute { name: "suicidal ideation" })
CREATE (suicidal_ideation)-[:IS]->(suicidal_ideation_value:Value { name: "blank", data_type: "boolean", range_candidate_guide: "" });

CREATE (sensorium_cognition)-[:HAS_ATTRIBUTE]->(suicidal_plan:Attribute { name: "suicidal plan" })
CREATE (suicidal_plan)-[:IS]->(suicidal_plan_value:Value { name: "blank", data_type: "boolean", range_candidate_guide: "" });

CREATE (sensorium_cognition)-[:HAS_ATTRIBUTE]->(suicidal_attempt:Attribute { name: "suicidal attempt" })
CREATE (suicidal_attempt)-[:IS]->(suicidal_attempt_value:Value { name: "blank", data_type: "boolean", range_candidate_guide: "" });

CREATE (sensorium_cognition)-[:HAS_ATTRIBUTE]->(impulsivity_homicide:Attribute { name: "impulsivity-homicide" })
CREATE (impulsivity_homicide)-[:IS]->(impulsivity_homicide_value:Value { name: "blank", data_type: "string", range_candidate_guide: "high/moderate/low" });

CREATE (sensorium_cognition)-[:HAS_ATTRIBUTE]->(social_judgement:Attribute { name: "social judgement" })
CREATE (social_judgement)-[:IS]->(social_judgement_value:Value { name: "blank", data_type: "boolean (normal/impaired)", range_candidate_guide: "" });

CREATE (sensorium_cognition)-[:HAS_ATTRIBUTE]->(insight:Attribute { name: "insight" })
CREATE (insight)-[:IS]->(insight_value:Value { name: "blank", data_type: "string", range_candidate_guide: "Complete denial of illness/Slight awareness of being sick and needing help, but denying it at the same time/Awareness of being sick but blaming it on others, external events/Intellectual insight./True emotional insight." });

CREATE (sensorium_cognition)-[:HAS_ATTRIBUTE]->(reliability:Attribute { name: "reliability" })
CREATE (reliability)-[:IS]->(reliability_value:Value {name: "blank", data_type: "boolean", range_candidate_guide: ""));
