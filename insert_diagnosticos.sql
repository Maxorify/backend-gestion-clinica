-- Script para insertar diagnósticos/enfermedades en la tabla diagnosticos
-- Ejecutar en Supabase SQL Editor

-- ENFERMEDADES RESPIRATORIAS
INSERT INTO diagnosticos (nombre_enfermedad) VALUES
('Gripe (Influenza)'),
('Resfriado común'),
('Bronquitis aguda'),
('Bronquitis crónica'),
('Neumonía'),
('Asma bronquial'),
('Faringitis aguda'),
('Amigdalitis'),
('Sinusitis aguda'),
('Sinusitis crónica'),
('Rinitis alérgica'),
('Laringitis'),
('COVID-19'),
('Enfermedad Pulmonar Obstructiva Crónica (EPOC)'),
('Tuberculosis pulmonar'),
('Bronquiectasia'),
('Apnea del sueño'),
('Pleuritis'),
('Neumotórax'),
('Embolia pulmonar');

-- ENFERMEDADES CARDIOVASCULARES
INSERT INTO diagnosticos (nombre_enfermedad) VALUES
('Hipertensión arterial'),
('Hipotensión arterial'),
('Arritmia cardíaca'),
('Fibrilación auricular'),
('Angina de pecho'),
('Infarto agudo de miocardio'),
('Insuficiencia cardíaca'),
('Miocardiopatía'),
('Pericarditis'),
('Endocarditis'),
('Valvulopatía cardíaca'),
('Arterioesclerosis'),
('Trombosis venosa profunda'),
('Varices'),
('Aneurisma aórtico'),
('Cardiopatía congénita'),
('Bradicardia'),
('Taquicardia');

-- ENFERMEDADES DIGESTIVAS
INSERT INTO diagnosticos (nombre_enfermedad) VALUES
('Gastritis aguda'),
('Gastritis crónica'),
('Úlcera gástrica'),
('Úlcera duodenal'),
('Reflujo gastroesofágico (ERGE)'),
('Enfermedad de Crohn'),
('Colitis ulcerosa'),
('Síndrome de intestino irritable'),
('Apendicitis'),
('Diverticulitis'),
('Colecistitis'),
('Colelitiasis (piedras en la vesícula)'),
('Pancreatitis aguda'),
('Pancreatitis crónica'),
('Hepatitis A'),
('Hepatitis B'),
('Hepatitis C'),
('Cirrosis hepática'),
('Hígado graso (esteatosis hepática)'),
('Estreñimiento crónico'),
('Diarrea aguda'),
('Diarrea crónica'),
('Hemorroides'),
('Fisura anal'),
('Hernia hiatal'),
('Hernia inguinal'),
('Enfermedad celíaca'),
('Intoxicación alimentaria'),
('Parásitos intestinales');

-- ENFERMEDADES ENDOCRINAS Y METABÓLICAS
INSERT INTO diagnosticos (nombre_enfermedad) VALUES
('Diabetes mellitus tipo 1'),
('Diabetes mellitus tipo 2'),
('Prediabetes'),
('Hipoglucemia'),
('Hipertiroidismo'),
('Hipotiroidismo'),
('Tiroiditis'),
('Bocio'),
('Obesidad'),
('Síndrome metabólico'),
('Hipercolesterolemia'),
('Hipertrigliceridemia'),
('Gota'),
('Osteoporosis'),
('Hipercalcemia'),
('Hipocalcemia'),
('Insuficiencia suprarrenal'),
('Síndrome de Cushing'),
('Acromegalia');

-- ENFERMEDADES NEUROLÓGICAS
INSERT INTO diagnosticos (nombre_enfermedad) VALUES
('Migraña'),
('Cefalea tensional'),
('Cefalea en racimos'),
('Epilepsia'),
('Enfermedad de Parkinson'),
('Enfermedad de Alzheimer'),
('Demencia'),
('Esclerosis múltiple'),
('Accidente cerebrovascular (ACV) isquémico'),
('Accidente cerebrovascular (ACV) hemorrágico'),
('Ataque isquémico transitorio (AIT)'),
('Meningitis'),
('Encefalitis'),
('Neuralgia del trigémino'),
('Neuropatía periférica'),
('Síndrome del túnel carpiano'),
('Vértigo'),
('Enfermedad de Ménière'),
('Parálisis facial (Parálisis de Bell)'),
('Temblor esencial');

-- ENFERMEDADES MUSCULOESQUELÉTICAS
INSERT INTO diagnosticos (nombre_enfermedad) VALUES
('Artritis reumatoide'),
('Artrosis'),
('Osteoartritis'),
('Lumbalgia (dolor lumbar)'),
('Cervicalgia (dolor cervical)'),
('Hernia discal'),
('Ciática'),
('Tendinitis'),
('Bursitis'),
('Fibromialgia'),
('Esguince'),
('Fractura ósea'),
('Luxación'),
('Síndrome del manguito rotador'),
('Epicondilitis (codo de tenista)'),
('Fascitis plantar'),
('Espolón calcáneo'),
('Escoliosis'),
('Contractura muscular'),
('Distensión muscular');

-- ENFERMEDADES RENALES Y URINARIAS
INSERT INTO diagnosticos (nombre_enfermedad) VALUES
('Infección urinaria'),
('Cistitis'),
('Pielonefritis'),
('Cálculos renales (litiasis renal)'),
('Insuficiencia renal aguda'),
('Insuficiencia renal crónica'),
('Glomerulonefritis'),
('Síndrome nefrótico'),
('Incontinencia urinaria'),
('Retención urinaria'),
('Prostatitis'),
('Hiperplasia prostática benigna'),
('Cáncer de próstata'),
('Uretritis');

-- ENFERMEDADES DERMATOLÓGICAS
INSERT INTO diagnosticos (nombre_enfermedad) VALUES
('Dermatitis atópica'),
('Dermatitis de contacto'),
('Dermatitis seborreica'),
('Psoriasis'),
('Acné'),
('Rosácea'),
('Eczema'),
('Urticaria'),
('Herpes simple'),
('Herpes zóster'),
('Impétigo'),
('Celulitis'),
('Hongos en la piel (micosis)'),
('Pie de atleta'),
('Verrugas'),
('Melanoma'),
('Vitiligo'),
('Alopecia areata'),
('Foliculitis'),
('Quemaduras solares');

-- ENFERMEDADES OFTALMOLÓGICAS
INSERT INTO diagnosticos (nombre_enfermedad) VALUES
('Conjuntivitis'),
('Blefaritis'),
('Orzuelo'),
('Chalazión'),
('Ojo seco'),
('Glaucoma'),
('Cataratas'),
('Degeneración macular'),
('Retinopatía diabética'),
('Desprendimiento de retina'),
('Presbicia'),
('Miopía'),
('Hipermetropía'),
('Astigmatismo'),
('Queratitis');

-- ENFERMEDADES OTORRINOLARINGOLÓGICAS
INSERT INTO diagnosticos (nombre_enfermedad) VALUES
('Otitis media'),
('Otitis externa'),
('Hipoacusia (pérdida auditiva)'),
('Tinnitus (zumbido de oídos)'),
('Vértigo posicional paroxístico benigno'),
('Rinitis'),
('Epistaxis (sangrado nasal)'),
('Pólipos nasales'),
('Desviación del tabique nasal');

-- ENFERMEDADES HEMATOLÓGICAS
INSERT INTO diagnosticos (nombre_enfermedad) VALUES
('Anemia ferropénica'),
('Anemia megaloblástica'),
('Anemia hemolítica'),
('Anemia aplásica'),
('Leucemia'),
('Linfoma'),
('Trombocitopenia'),
('Hemofilia'),
('Policitemia'),
('Mieloma múltiple');

-- ENFERMEDADES INFECCIOSAS
INSERT INTO diagnosticos (nombre_enfermedad) VALUES
('Dengue'),
('Zika'),
('Chikungunya'),
('Malaria'),
('Fiebre tifoidea'),
('Varicela'),
('Sarampión'),
('Rubéola'),
('Mononucleosis infecciosa'),
('VIH/SIDA'),
('Toxoplasmosis'),
('Sífilis'),
('Gonorrea'),
('Clamidia'),
('Herpes genital'),
('Candidiasis'),
('Escabiosis (sarna)'),
('Pediculosis (piojos)');

-- ENFERMEDADES GINECOLÓGICAS Y OBSTÉTRICAS
INSERT INTO diagnosticos (nombre_enfermedad) VALUES
('Síndrome de ovario poliquístico'),
('Endometriosis'),
('Miomas uterinos'),
('Quistes ováricos'),
('Enfermedad pélvica inflamatoria'),
('Vaginitis'),
('Cervicitis'),
('Amenorrea'),
('Dismenorrea'),
('Síndrome premenstrual'),
('Menopausia'),
('Embarazo'),
('Preeclampsia'),
('Diabetes gestacional'),
('Infertilidad'),
('Aborto espontáneo');

-- ENFERMEDADES PSIQUIÁTRICAS Y MENTALES
INSERT INTO diagnosticos (nombre_enfermedad) VALUES
('Depresión mayor'),
('Trastorno de ansiedad generalizada'),
('Trastorno de pánico'),
('Trastorno obsesivo-compulsivo (TOC)'),
('Trastorno de estrés postraumático (TEPT)'),
('Trastorno bipolar'),
('Esquizofrenia'),
('Trastorno por déficit de atención e hiperactividad (TDAH)'),
('Trastorno del espectro autista'),
('Trastornos de la conducta alimentaria (anorexia)'),
('Trastornos de la conducta alimentaria (bulimia)'),
('Trastorno límite de la personalidad'),
('Insomnio'),
('Síndrome de burnout'),
('Trastorno de adaptación');

-- ENFERMEDADES PEDIÁTRICAS
INSERT INTO diagnosticos (nombre_enfermedad) VALUES
('Cólicos del lactante'),
('Dermatitis del pañal'),
('Bronquiolitis'),
('Crup'),
('Enfermedad de manos, pies y boca'),
('Escarlatina'),
('Paperas'),
('Tos ferina'),
('Reflujo gastroesofágico infantil'),
('Intolerancia a la lactosa');

-- ENFERMEDADES ONCOLÓGICAS
INSERT INTO diagnosticos (nombre_enfermedad) VALUES
('Cáncer de mama'),
('Cáncer de pulmón'),
('Cáncer de colon'),
('Cáncer de estómago'),
('Cáncer de hígado'),
('Cáncer de páncreas'),
('Cáncer de tiroides'),
('Cáncer de piel'),
('Cáncer de ovario'),
('Cáncer de útero'),
('Cáncer de vejiga'),
('Cáncer de riñón'),
('Cáncer de cerebro'),
('Cáncer de esófago');

-- OTROS DIAGNÓSTICOS COMUNES
INSERT INTO diagnosticos (nombre_enfermedad) VALUES
('Fiebre de origen desconocido'),
('Deshidratación'),
('Desnutrición'),
('Fatiga crónica'),
('Dolor crónico'),
('Reacción alérgica'),
('Anafilaxia'),
('Intoxicación por medicamentos'),
('Intoxicación por alcohol'),
('Golpe de calor'),
('Hipotermia'),
('Mareo'),
('Desmayo (síncope)'),
('Sangrado nasal recurrente'),
('Dolor abdominal agudo'),
('Traumatismo craneoencefálico'),
('Lesión deportiva'),
('Mordedura de animal'),
('Picadura de insecto'),
('Quemadura');
