-- Script para insertar especialidades médicas en la base de datos
-- Ejecutar este script en PostgreSQL/Supabase

-- Primero, agregar constraint UNIQUE a la columna nombre si no existe
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'especialidad_nombre_unique'
    ) THEN
        ALTER TABLE public.especialidad ADD CONSTRAINT especialidad_nombre_unique UNIQUE (nombre);
    END IF;
END $$;

INSERT INTO public.especialidad (nombre, descripcion) VALUES
('Cardiología', 'Especialidad médica que se ocupa de las enfermedades del corazón y del aparato circulatorio'),
('Pediatría', 'Rama de la medicina que se especializa en la salud y las enfermedades de los niños'),
('Neurología', 'Especialidad médica que trata los trastornos del sistema nervioso'),
('Dermatología', 'Especialidad médica que se ocupa de las enfermedades de la piel'),
('Ginecología', 'Especialidad médica que trata las enfermedades del sistema reproductor femenino'),
('Obstetricia', 'Rama de la medicina que se ocupa del embarazo, parto y puerperio'),
('Traumatología', 'Especialidad médica que se dedica al estudio de las lesiones del aparato locomotor'),
('Oftalmología', 'Especialidad médica que estudia las enfermedades de ojo y su tratamiento'),
('Otorrinolaringología', 'Especialidad médica que se ocupa de las enfermedades del oído, nariz y garganta'),
('Psiquiatría', 'Especialidad médica dedicada al estudio, diagnóstico y tratamiento de los trastornos mentales'),
('Urología', 'Especialidad médica que se ocupa del estudio, diagnóstico y tratamiento de las enfermedades del aparato urinario'),
('Gastroenterología', 'Especialidad médica que se ocupa de las enfermedades del aparato digestivo'),
('Endocrinología', 'Especialidad médica que estudia las hormonas y las glándulas que las producen'),
('Neumología', 'Especialidad médica que se ocupa de las enfermedades del aparato respiratorio'),
('Oncología', 'Especialidad médica que se dedica al diagnóstico y tratamiento del cáncer'),
('Hematología', 'Especialidad médica que estudia la sangre y sus enfermedades'),
('Reumatología', 'Especialidad médica dedicada a los trastornos médicos del aparato locomotor y del tejido conectivo'),
('Nefrología', 'Especialidad médica que se ocupa del estudio de la estructura y función renal'),
('Infectología', 'Especialidad médica que se dedica al estudio, diagnóstico y tratamiento de las enfermedades infecciosas'),
('Medicina Interna', 'Especialidad médica que se dedica a la atención integral del adulto enfermo'),
('Medicina Familiar', 'Especialidad médica que proporciona atención sanitaria continua e integral al individuo y la familia'),
('Medicina General', 'Atención médica primaria y general para diversas condiciones de salud'),
('Cirugía General', 'Especialidad médica que abarca las operaciones del aparato digestivo y del sistema endocrino'),
('Cirugía Cardiovascular', 'Especialidad quirúrgica que se ocupa del tratamiento de las enfermedades del corazón y grandes vasos'),
('Neurocirugía', 'Especialidad médica que se ocupa del tratamiento quirúrgico de enfermedades del sistema nervioso'),
('Cirugía Plástica', 'Especialidad quirúrgica que se ocupa de la corrección de defectos congénitos o adquiridos'),
('Anestesiología', 'Especialidad médica dedicada a la atención y cuidados especiales de los pacientes durante las intervenciones quirúrgicas'),
('Radiología', 'Especialidad médica que se ocupa de generar imágenes del interior del cuerpo mediante diferentes agentes físicos'),
('Medicina de Urgencias', 'Especialidad médica que actúa sobre procesos agudos que ponen en peligro la vida del paciente'),
('Geriatría', 'Especialidad médica dedicada al estudio de las enfermedades que aquejan a las personas adultas mayores'),
('Alergología', 'Especialidad médica que comprende el conocimiento, diagnóstico y tratamiento de las enfermedades alérgicas'),
('Nutrición', 'Especialidad que se encarga de la prevención, diagnóstico y tratamiento de problemas nutricionales'),
('Medicina Deportiva', 'Especialidad médica que estudia los efectos del ejercicio del deporte y la actividad física'),
('Patología', 'Especialidad médica que estudia las enfermedades en su amplio sentido'),
('Medicina del Trabajo', 'Especialidad médica dedicada a la vigilancia de la salud de los trabajadores')
ON CONFLICT (nombre) DO NOTHING;

-- Verificar cuántas especialidades se insertaron
SELECT COUNT(*) as total_especialidades FROM public.especialidad;

-- Ver todas las especialidades ordenadas alfabéticamente
SELECT id, nombre, descripcion FROM public.especialidad ORDER BY nombre;
