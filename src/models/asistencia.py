"""
Modelos Pydantic para el módulo de asistencia de doctores.
Incluye validación, serialización y esquemas de respuesta.
"""
from pydantic import BaseModel, Field, validator
from datetime import datetime, date, time
from typing import Optional, List, Literal
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class TipoMarca(str, Enum):
    """Tipos de marca de asistencia"""
    ENTRADA = "ENTRADA"
    SALIDA = "SALIDA"


class FuenteMarca(str, Enum):
    """Fuente de registro de la marca"""
    WEB = "WEB"
    MANUAL = "MANUAL"
    BIOMETRICO = "BIOMETRICO"
    APP = "APP"


class EstadoAsistencia(str, Enum):
    """Estados posibles de asistencia"""
    PROGRAMADO = "PROGRAMADO"  # Turno programado, aún no llega la hora
    EN_TURNO = "EN_TURNO"      # Marcó entrada, aún no marca salida
    ASISTIO = "ASISTIO"        # Completó turno (entrada + salida)
    ATRASO = "ATRASO"          # Llegó con atraso
    AUSENTE = "AUSENTE"        # No marcó entrada cuando debía
    JUSTIFICADO = "JUSTIFICADO"  # Ausencia justificada
    PARCIAL = "PARCIAL"        # Turno incompleto


class TipoJustificacion(str, Enum):
    """Tipos de justificación de ausencia/atraso"""
    PERMISO_MEDICO = "PERMISO_MEDICO"
    REUNION_INSTITUCIONAL = "REUNION_INSTITUCIONAL"
    EMERGENCIA_FAMILIAR = "EMERGENCIA_FAMILIAR"
    CAPACITACION = "CAPACITACION"
    LICENCIA_MEDICA = "LICENCIA_MEDICA"
    OTRO = "OTRO"


# ============================================================================
# REQUEST MODELS
# ============================================================================

class MarcaAsistenciaCreate(BaseModel):
    """Modelo para crear una marca de asistencia"""
    usuario_sistema_id: int = Field(..., description="ID del doctor")
    horario_id: Optional[int] = Field(None, description="ID del horario asociado")
    tipo_marca: TipoMarca
    fecha_hora_marca: Optional[datetime] = Field(None, description="Hora de la marca, si es None usa NOW()")
    fuente: FuenteMarca = Field(FuenteMarca.WEB, description="Fuente de registro")
    registrado_por: Optional[int] = Field(None, description="ID de quien registró (si es manual)")
    notas: Optional[str] = Field(None, max_length=500)
    origen_ip: Optional[str] = Field(None, max_length=50)

    class Config:
        json_schema_extra = {
            "example": {
                "usuario_sistema_id": 5,
                "tipo_marca": "ENTRADA",
                "fuente": "MANUAL",
                "registrado_por": 2,
                "notas": "Doctor llegó corriendo, reloj biométrico no funcionó"
            }
        }


class JustificacionCreate(BaseModel):
    """Modelo para justificar ausencia o atraso"""
    tipo_justificacion: TipoJustificacion
    justificacion: str = Field(..., min_length=10, max_length=1000)
    justificado_por: int = Field(..., description="ID del admin/RRHH que justifica")

    class Config:
        json_schema_extra = {
            "example": {
                "tipo_justificacion": "PERMISO_MEDICO",
                "justificacion": "Cita médica personal previamente autorizada por dirección",
                "justificado_por": 1
            }
        }


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class MarcaAsistenciaResponse(BaseModel):
    """Respuesta con datos de una marca"""
    id: int
    usuario_sistema_id: int
    horario_id: Optional[int]
    tipo_marca: str
    fecha_hora_marca: datetime
    fuente: str
    registrado_por: Optional[int]
    notas: Optional[str]
    origen_ip: Optional[str]
    created_at: datetime

    # Información adicional enriquecida
    registrado_por_nombre: Optional[str] = None

    class Config:
        from_attributes = True


class DoctorBasicInfo(BaseModel):
    """Información básica del doctor"""
    id: int
    nombre: str
    apellido_paterno: Optional[str]
    apellido_materno: Optional[str]
    nombre_completo: str
    rut: Optional[str]
    especialidades: List[str] = []
    email: Optional[str] = None
    celular: Optional[str] = None


class EstadoAsistenciaResponse(BaseModel):
    """Estado calculado de asistencia"""
    id: int
    asistencia_id: int
    estado: str
    minutos_atraso: int
    minutos_trabajados: Optional[int]
    porcentaje_asistencia: Optional[float]
    tipo_justificacion: Optional[str]
    justificacion: Optional[str]
    justificado_por: Optional[int]
    fecha_justificacion: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class TurnoAsistenciaDetalle(BaseModel):
    """Detalle completo de un turno con asistencia"""
    # Datos del turno
    id: int
    horario_id: Optional[int]
    inicio_turno: datetime
    finalizacion_turno: Optional[datetime]
    
    # Datos del doctor
    doctor: DoctorBasicInfo
    
    # Estado de asistencia
    estado_asistencia: str
    minutos_atraso: int
    minutos_trabajados: Optional[int]
    porcentaje_asistencia: Optional[float]
    
    # Marcas
    marca_entrada: Optional[datetime]
    marca_salida: Optional[datetime]
    fuente_entrada: Optional[str]
    fuente_salida: Optional[str]
    
    # Justificación
    justificacion: Optional[str]
    tipo_justificacion: Optional[str]
    
    # Productividad
    pacientes_agendados: int = 0
    pacientes_atendidos: int = 0
    
    # Metadata
    created_at: datetime


class ResumenDiarioAsistencia(BaseModel):
    """Resumen de asistencia del día"""
    fecha: date
    total_turnos: int
    en_turno: int
    asistieron: int
    con_atraso: int
    ausentes: int
    justificados: int
    turnos: List[TurnoAsistenciaDetalle]


class EstadisticasAsistenciaDoctor(BaseModel):
    """Estadísticas de asistencia de un doctor en un periodo"""
    doctor_id: int
    doctor_nombre: str
    periodo_inicio: date
    periodo_fin: date
    
    total_turnos: int
    dias_asistio: int
    dias_atraso: int
    dias_ausente: int
    dias_justificado: int
    
    promedio_minutos_atraso: float
    porcentaje_puntualidad: float
    porcentaje_asistencia: float
    
    total_minutos_trabajados: int
    total_pacientes_atendidos: int


class ParametroAsistencia(BaseModel):
    """Parámetro configurable del módulo"""
    id: int
    parametro: str
    valor_numerico: Optional[int]
    valor_texto: Optional[str]
    descripcion: Optional[str]
    activo: bool

    class Config:
        from_attributes = True


class ParametroAsistenciaUpdate(BaseModel):
    """Actualización de parámetro"""
    valor_numerico: Optional[int] = None
    valor_texto: Optional[str] = None
    activo: Optional[bool] = None


# ============================================================================
# UTILITY MODELS
# ============================================================================

class FiltrosAsistencia(BaseModel):
    """Filtros para consultas de asistencia"""
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    doctor_id: Optional[int] = None
    estado: Optional[EstadoAsistencia] = None
    con_atraso: Optional[bool] = None
    solo_ausentes: Optional[bool] = None


class EstadoCalculado(BaseModel):
    """Resultado del cálculo de estado"""
    estado: str
    minutos_atraso: int
    minutos_trabajados: int
    porcentaje: float


# ============================================================================
# MODELOS LEGACY (mantener compatibilidad)
# ============================================================================

class RegistroAsistencia(BaseModel):
    """LEGACY: Mantener para compatibilidad con código existente"""
    usuario_sistema_id: int
    inicio_turno: datetime
    finalizacion_turno: Optional[datetime] = None


class ActualizarAsistencia(BaseModel):
    """LEGACY: Mantener para compatibilidad con código existente"""
    inicio_turno: Optional[datetime] = None
    finalizacion_turno: Optional[datetime] = None
