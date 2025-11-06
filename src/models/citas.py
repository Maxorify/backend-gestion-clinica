from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CitaMedica(BaseModel):
    """Modelo para crear/actualizar una cita médica"""
    fecha_atencion: datetime = Field(..., description="Fecha y hora de la cita")
    paciente_id: int = Field(..., description="ID del paciente")
    doctor_id: int = Field(..., description="ID del doctor")


class InformacionCita(BaseModel):
    """Modelo para la información detallada de una cita"""
    motivo_consulta: Optional[str] = Field(None, description="Motivo de la consulta")
    antecedentes: Optional[str] = Field(None, description="Antecedentes médicos")
    dolores_sintomas: Optional[str] = Field(None, description="Dolores y síntomas")
    atenciones_quirurgicas: Optional[str] = Field(None, description="Atenciones quirúrgicas previas")
    evaluacion_doctor: Optional[str] = Field(None, description="Evaluación del doctor")
    tratamiento: Optional[str] = Field(None, description="Tratamiento prescrito")
    diagnostico_id: Optional[int] = Field(None, description="ID del diagnóstico")


class CrearCitaCompleta(BaseModel):
    """Modelo para crear una cita completa con su información"""
    cita: CitaMedica
    informacion: InformacionCita
    estado_inicial: str = Field(default="Pendiente", description="Estado inicial de la cita")


class ActualizarCita(BaseModel):
    """Modelo para actualizar una cita existente"""
    fecha_atencion: Optional[datetime] = Field(None, description="Nueva fecha y hora")
    paciente_id: Optional[int] = Field(None, description="Nuevo ID del paciente")
    doctor_id: Optional[int] = Field(None, description="Nuevo ID del doctor")


class ActualizarInformacionCita(BaseModel):
    """Modelo para actualizar información de una cita"""
    motivo_consulta: Optional[str] = None
    antecedentes: Optional[str] = None
    dolores_sintomas: Optional[str] = None
    atenciones_quirurgicas: Optional[str] = None
    evaluacion_doctor: Optional[str] = None
    tratamiento: Optional[str] = None
    diagnostico_id: Optional[int] = None


class CambiarEstado(BaseModel):
    """Modelo para cambiar el estado de una cita"""
    estado: str = Field(..., description="Nuevo estado: Pendiente, Confirmada, En Consulta, Completada, Cancelada")


class CrearPago(BaseModel):
    """Modelo para procesar un pago de cita"""
    cita_medica_id: int = Field(..., description="ID de la cita médica")
    tipo_pago: str = Field(..., description="Método de pago: Efectivo, Tarjeta de Débito, Tarjeta de Crédito, Transferencia")
    total: float = Field(..., description="Monto total del pago")
    descuento_aseguradora: Optional[float] = Field(None, description="Porcentaje de descuento (0-100)")
    detalle_descuento: Optional[str] = Field(None, description="Motivo del descuento si aplica")
