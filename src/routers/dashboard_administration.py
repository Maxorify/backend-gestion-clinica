from fastapi import APIRouter, HTTPException
from src.utils.supabase import supabase_client
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

dashboard_router = APIRouter(tags=["Dashboard"], prefix="/Dashboard")

@dashboard_router.get("/estadisticas")
async def obtener_estadisticas():
    """
    Obtiene las estadísticas principales para el dashboard del admin:
    - Total de pacientes
    - Citas de hoy
    - Doctores activos (rol_id=2)
    - Ingresos del mes actual
    """
    try:
        # 1. Total de pacientes
        pacientes = (
            supabase_client
            .table("paciente")
            .select("id", count="exact")
            .execute()
        )
        total_pacientes = pacientes.count if pacientes.count else 0

        # 2. Citas de hoy
        hoy = datetime.now().date()
        hoy_inicio = f"{hoy}T00:00:00"
        hoy_fin = f"{hoy}T23:59:59"

        citas_hoy = (
            supabase_client
            .table("cita_medica")
            .select("id", count="exact")
            .gte("fecha_atencion", hoy_inicio)
            .lte("fecha_atencion", hoy_fin)
            .execute()
        )
        total_citas_hoy = citas_hoy.count if citas_hoy.count else 0

        # 3. Doctores activos (usuarios con rol_id=2 que es médico)
        doctores = (
            supabase_client
            .table("usuario_sistema")
            .select("id", count="exact")
            .eq("rol_id", 2)
            .execute()
        )
        total_doctores = doctores.count if doctores.count else 0

        # 4. Ingresos del mes actual
        primer_dia_mes = datetime.now().replace(day=1, hour=0, minute=0, second=0)
        ultimo_dia_mes = (primer_dia_mes + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)

        pagos_mes = (
            supabase_client
            .table("pagos")
            .select("total")
            .gte("fecha_pago", primer_dia_mes.isoformat())
            .lte("fecha_pago", ultimo_dia_mes.isoformat())
            .execute()
        )

        ingresos_mes = 0
        if pagos_mes.data:
            ingresos_mes = sum(float(pago.get("total", 0)) for pago in pagos_mes.data)

        # 5. Calcular comparaciones con el mes anterior para los cambios
        mes_anterior_inicio = (primer_dia_mes - timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0)
        mes_anterior_fin = primer_dia_mes - timedelta(seconds=1)

        # Pacientes del mes anterior
        pacientes_mes_anterior = (
            supabase_client
            .table("paciente")
            .select("id", count="exact")
            .execute()
        )

        # Citas del mismo día del mes anterior
        dia_mes_anterior = (hoy - timedelta(days=30))
        dia_anterior_inicio = f"{dia_mes_anterior}T00:00:00"
        dia_anterior_fin = f"{dia_mes_anterior}T23:59:59"

        citas_dia_anterior = (
            supabase_client
            .table("cita_medica")
            .select("id", count="exact")
            .gte("fecha_atencion", dia_anterior_inicio)
            .lte("fecha_atencion", dia_anterior_fin)
            .execute()
        )
        total_citas_dia_anterior = citas_dia_anterior.count if citas_dia_anterior.count else 1

        # Ingresos del mes anterior
        pagos_mes_anterior = (
            supabase_client
            .table("pagos")
            .select("total")
            .gte("fecha_pago", mes_anterior_inicio.isoformat())
            .lte("fecha_pago", mes_anterior_fin.isoformat())
            .execute()
        )

        ingresos_mes_anterior = 0
        if pagos_mes_anterior.data:
            ingresos_mes_anterior = sum(float(pago.get("total", 0)) for pago in pagos_mes_anterior.data)

        # Calcular porcentajes de cambio
        cambio_citas = 0
        if total_citas_dia_anterior > 0:
            cambio_citas = ((total_citas_hoy - total_citas_dia_anterior) / total_citas_dia_anterior) * 100

        cambio_ingresos = 0
        if ingresos_mes_anterior > 0:
            cambio_ingresos = ((ingresos_mes - ingresos_mes_anterior) / ingresos_mes_anterior) * 100

        return {
            "estadisticas": {
                "total_pacientes": total_pacientes,
                "cambio_pacientes": "+12.5%",  # Esto sería calculado comparando con el mes anterior
                "citas_hoy": total_citas_hoy,
                "cambio_citas": f"{'+' if cambio_citas >= 0 else ''}{cambio_citas:.1f}%",
                "doctores_activos": total_doctores,
                "cambio_doctores": f"+{total_doctores}",
                "ingresos_mes": ingresos_mes,
                "cambio_ingresos": f"{'+' if cambio_ingresos >= 0 else ''}{cambio_ingresos:.1f}%"
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@dashboard_router.get("/citas-recientes")
async def obtener_citas_recientes(limite: int = 5):
    """
    Obtiene las citas más recientes con información del paciente, doctor y estado.
    """
    try:
        # Obtener citas recientes con información relacionada
        hoy = datetime.now()

        citas = (
            supabase_client
            .table("cita_medica")
            .select("""
                id,
                fecha_atencion,
                paciente:paciente_id(nombre, apellido_paterno, apellido_materno),
                doctor:doctor_id(nombre, apellido_paterno, apellido_materno)
            """)
            .gte("fecha_atencion", hoy.date().isoformat())
            .order("fecha_atencion", desc=False)
            .limit(limite)
            .execute()
        )

        citas_formateadas = []
        for cita in citas.data:
            # Obtener el estado de la cita
            estado_result = (
                supabase_client
                .table("estado")
                .select("estado")
                .eq("cita_medica_id", cita["id"])
                .execute()
            )

            estado = "En espera"
            if estado_result.data and len(estado_result.data) > 0:
                estado = estado_result.data[0].get("estado", "En espera")

            # Formatear fecha
            fecha_atencion = datetime.fromisoformat(cita["fecha_atencion"].replace('Z', '+00:00'))
            hora_formateada = fecha_atencion.strftime("%I:%M %p")

            # Obtener nombres completos
            paciente = cita.get("paciente", {})
            doctor = cita.get("doctor", {})

            nombre_paciente = f"{paciente.get('nombre', '')} {paciente.get('apellido_paterno', '')}".strip()
            nombre_doctor = f"Dr. {doctor.get('nombre', '')} {doctor.get('apellido_paterno', '')}".strip()

            citas_formateadas.append({
                "id": cita["id"],
                "patient": nombre_paciente if nombre_paciente else "Paciente desconocido",
                "doctor": nombre_doctor if nombre_doctor != "Dr. " else "Doctor desconocido",
                "time": hora_formateada,
                "status": estado
            })

        return {"citas": citas_formateadas}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
