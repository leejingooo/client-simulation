// Start
CREATE(patient: Patient { name: 'Patient' })

// Category
CREATE(iden: Category { name: 'Identification' })
CREATE(cc: Category { name: 'Chief Complaint' })
CREATE(pi: Category { name: 'Present Illness' })
CREATE(pph: Category { name: 'Past Psychiatric History' })
CREATE(mse: Category { name: 'Mental Status Examination' })

// Personal Information
CREATE(name: pers_info { name: 'Name' })
CREATE(age: pers_info { name: 'Age' })
CREATE(sex: pers_info { name: 'Sex' })
CREATE(mari_stat: pers_info { name: 'Marital Status' })

// Characteristic
CREATE(sym: Characteristic { name: 'Symptom' })
CREATE(leng: Characteristic { name: 'Duration' })
CREATE(frequency: Characteristic { name: 'Frequency' })
CREATE(allev_fac: Characteristic { name: 'Alleviating Factor' })
CREATE(exac_fac: Characteristic { name: 'Exacerbating Factor' })

// 관계
CREATE(patient)-[:HAS] -> (iden)
CREATE(patient)-[:HAS] -> (cc)
CREATE(patient)-[:HAS] -> (pi)
CREATE(patient)-[:HAS] -> (pph)
CREATE(patient)-[:HAS] -> (mse)

CREATE(iden)-[:HAS_ATTRIBUTE] -> (name)
CREATE(iden)-[:HAS_ATTRIBUTE] -> (age)
CREATE(iden)-[:HAS_ATTRIBUTE] -> (sex)
CREATE(iden)-[:HAS_ATTRIBUTE] -> (mari_stat)

// Create and connect the appropriate nodes. The parts that need to be connected are shown below and instructions are given after → Show. The guide shows the data_type of the node name and the range/candidate/guide.
CREATE(name)-[:IS] -> data_type: string
CREATE(age)-[:IS] -> data_type: number; range: 19-64
CREATE(sex)-[:IS] -> data_type: number; candidate: male/female
CREATE(mari_stat)-[:IS] -> data_type: string; candidate: single/married/divorced/widowed

CREATE(cc)-[:IS] ->

CREATE(pi)-[:HAS_ATTRIBUTE] -> (sym)

// Edge 종류
HAS
HAS_ATTRIBUTE
IS
