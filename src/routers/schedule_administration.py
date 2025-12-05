from fastapi import APIRouter, HTTPException
from src.utils.supabase import supabase_client
from src.models.horarios import HorarioBloque, CrearHorarioSemanal, ActualizarHorario
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Optional

schedule_router = APIRouter(tags=["Gestión de Horarios"], prefix="/Horarios")

@schedule_router.post("/crear-bloque")
async def crear_bloque_horario(horario: HorarioBloque):
    """
    Crea un bloque de horario individual para un doctor.
    """
    try:
        # Validar que el usuario existe y es doctor
        usuario = supabase_client.table("usuario_sistema").select("id, rol_id").eq("id", horario.usuario_sistema_id).execute()
        if not usuario.data:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        if usuario.data[0]["rol_id"] != 2:
            raise HTTPException(status_code=400, detail="El usuario no es un doctor")
        
        # Validar que no haya solapamiento de horarios
        solapamiento = supabase_client.table("horarios_personal").select("id").eq("usuario_sistema_id", horario.usuario_sistema_id).or_(
            f"and(inicio_bloque.lte.{horario.finalizacion_bloque.isoformat()},finalizacion_bloque.gte.{horario.inicio_bloque.isoformat()})"
        ).execute()
        
        if solapamiento.data:
            raise HTTPException(status_code=409, detail="Ya existe un horario en ese rango de tiempo")
        
        # Crear el bloque
        nuevo = supabase_client.table("horarios_personal").insert({
            "inicio_bloque": horario.inicio_bloque.isoformat(),
            "finalizacion_bloque": horario.finalizacion_bloque.isoformat(),
            "usuario_sistema_id": horario.usuario_sistema_id
        }).execute()
        
        if not nuevo.data:
            raise HTTPException(status_code=500, detail="No se pudo crear el bloque de horario")
        
        return {"mensaje": "Bloque de horario creado correctamente", "horario": nuevo.data[0]}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@schedule_router.post("/crear-horario-semanal")
async def crear_horario_semanal(horario: CrearHorarioSemanal):
    """
    Crea bloques de horario automáticamente para un día específico de la semana.
    Genera bloques desde fecha_inicio hasta fecha_fin (o 3 meses si no se especifica).
    OPTIMIZADO: Usa bulk insert en vez de inserts individuales.
    """
    try:
        # 🔍 DEBUG: Ver qué recibe el backend
        print(f"🔍 CREAR HORARIO SEMANAL - Datos recibidos:")
        print(f"   usuario_sistema_id: {horario.usuario_sistema_id}")
        print(f"   dia_semana: {horario.dia_semana}")
        print(f"   hora_inicio: {horario.hora_inicio}")
        print(f"   hora_fin: {horario.hora_fin}")
        print(f"   duracion_bloque_minutos: {horario.duracion_bloque_minutos}")
        print(f"   fecha_inicio: {horario.fecha_inicio}")
        print(f"   fecha_fin: {horario.fecha_fin}")
        
        # Validar que el usuario existe y es doctor (UNA SOLA VEZ)
        usuario = supabase_client.table("usuario_sistema").select("id, rol_id").eq("id", horario.usuario_sistema_id).execute()
        if not usuario.data:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        if usuario.data[0]["rol_id"] != 2:
            raise HTTPException(status_code=400, detail="El usuario no es un doctor")
        
        # Parsear fechas
        fecha_inicio = datetime.strptime(horario.fecha_inicio, "%Y-%m-%d").date()
        if horario.fecha_fin:
            fecha_fin = datetime.strptime(horario.fecha_fin, "%Y-%m-%d").date()
        else:
            fecha_fin = fecha_inicio + timedelta(days=90)  # 3 meses por defecto
        
        # Timezone de Chile para conversión correcta
        chile_tz = ZoneInfo("America/Santiago")
        
        # FASE 1: Generar TODOS los bloques en memoria (rápido)
        bloques_a_crear = []
        fecha_actual = fecha_inicio
        
        while fecha_actual <= fecha_fin:
            # Verificar si es el día de la semana correcto (0=Lunes, 6=Domingo)
            if fecha_actual.weekday() == horario.dia_semana:
                # Crear bloques en hora Chile y convertir a UTC para guardar
                hora_bloque_chile = datetime.combine(
                    fecha_actual,
                    datetime.strptime(horario.hora_inicio, "%H:%M").time(),
                    tzinfo=chile_tz
                )
                hora_fin_dia_chile = datetime.combine(
                    fecha_actual,
                    datetime.strptime(horario.hora_fin, "%H:%M").time(),
                    tzinfo=chile_tz
                )
                
                # Generar bloques del día
                while hora_bloque_chile < hora_fin_dia_chile:
                    fin_bloque_chile = hora_bloque_chile + timedelta(minutes=horario.duracion_bloque_minutos)
                    
                    if fin_bloque_chile > hora_fin_dia_chile:
                        break
                    
                    # Convertir a UTC para guardar en PostgreSQL
                    inicio_utc = hora_bloque_chile.astimezone(timezone.utc)
                    fin_utc = fin_bloque_chile.astimezone(timezone.utc)
                    
                    bloques_a_crear.append({
                        "inicio_bloque": inicio_utc.isoformat(),
                        "finalizacion_bloque": fin_utc.isoformat(),
                        "usuario_sistema_id": horario.usuario_sistema_id
                    })
                    
                    hora_bloque_chile = fin_bloque_chile
            
            fecha_actual += timedelta(days=1)
        
        # Si no hay bloques para crear, retornar
        if not bloques_a_crear:
            return {
                "mensaje": "No se generaron bloques para el rango especificado",
                "bloques_creados": 0
            }
        
        # FASE 2: Consultar solapamientos existentes (UNA SOLA QUERY)
        # Obtener rango completo de fechas
        primer_bloque = bloques_a_crear[0]
        ultimo_bloque = bloques_a_crear[-1]
        
        horarios_existentes = supabase_client.table("horarios_personal").select(
            "inicio_bloque, finalizacion_bloque"
        ).eq(
            "usuario_sistema_id", horario.usuario_sistema_id
        ).gte(
            "inicio_bloque", primer_bloque["inicio_bloque"]
        ).lte(
            "finalizacion_bloque", ultimo_bloque["finalizacion_bloque"]
        ).execute()
        
        # FASE 3: Filtrar bloques que NO se solapan (en memoria, rápido)
        bloques_validos = []
        
        if horarios_existentes.data:
            # Convertir a sets para comparación rápida
            rangos_existentes = set()
            for h in horarios_existentes.data:
                rangos_existentes.add((h["inicio_bloque"], h["finalizacion_bloque"]))
            
            # Filtrar bloques que no existen
            for bloque in bloques_a_crear:
                if (bloque["inicio_bloque"], bloque["finalizacion_bloque"]) not in rangos_existentes:
                    bloques_validos.append(bloque)
        else:
            # No hay solapamientos, todos son válidos
            bloques_validos = bloques_a_crear
        
        # FASE 4: Bulk insert (UNA SOLA TRANSACCIÓN)
        if bloques_validos:
            # Supabase permite insertar hasta 1000 registros por batch
            # Si hay más, dividir en chunks
            BATCH_SIZE = 1000
            total_insertados = 0
            
            for i in range(0, len(bloques_validos), BATCH_SIZE):
                batch = bloques_validos[i:i + BATCH_SIZE]
                resultado = supabase_client.table("horarios_personal").insert(batch).execute()
                
                if resultado.data:
                    total_insertados += len(resultado.data)
            
            return {
                "mensaje": f"Se crearon {total_insertados} bloques de horario",
                "bloques_creados": total_insertados,
                "bloques_generados": len(bloques_a_crear),
                "bloques_saltados": len(bloques_a_crear) - total_insertados
            }
        else:
            return {
                "mensaje": "Todos los bloques ya existen",
                "bloques_creados": 0,
                "bloques_generados": len(bloques_a_crear),
                "bloques_saltados": len(bloques_a_crear)
            }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@schedule_router.get("/listar-horarios")
async def listar_horarios(
    usuario_sistema_id: Optional[int] = None,
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None
):
    """
    Lista los horarios de los doctores.
    Puede filtrar por doctor y rango de fechas (en hora Chile, no UTC).
    """
    try:
        chile_tz = ZoneInfo("America/Santiago")
        
        query = supabase_client.table("horarios_personal").select(
            "id, inicio_bloque, finalizacion_bloque, usuario_sistema_id, usuario_sistema(nombre, apellido_paterno, apellido_materno)"
        )
        
        if usuario_sistema_id:
            query = query.eq("usuario_sistema_id", usuario_sistema_id)
        
        # Si hay filtros de fecha, ampliar el rango para cubrir conversiones de timezone
        # Ampliar -1 día antes y +1 día después para no perder bloques en bordes
        if fecha_inicio:
            dt_inicio = datetime.fromisoformat(fecha_inicio.replace('Z', '+00:00'))
            dt_inicio_ampliado = dt_inicio - timedelta(days=1)
            query = query.gte("inicio_bloque", dt_inicio_ampliado.isoformat())
        
        if fecha_fin:
            dt_fin = datetime.fromisoformat(fecha_fin.replace('Z', '+00:00'))
            dt_fin_ampliado = dt_fin + timedelta(days=1)
            query = query.lte("finalizacion_bloque", dt_fin_ampliado.isoformat())
        
        query = query.order("inicio_bloque", desc=False)
        
        result = query.execute()
        
        # Filtrar bloques basándonos en fecha LOCAL Chile
        horarios_filtrados = result.data or []
        
        if (fecha_inicio or fecha_fin) and horarios_filtrados:
            horarios_finales = []
            
            for horario in horarios_filtrados:
                # Convertir inicio_bloque a hora Chile
                inicio_utc = datetime.fromisoformat(horario["inicio_bloque"].replace('Z', '+00:00'))
                inicio_chile = inicio_utc.astimezone(chile_tz)
                fecha_chile = inicio_chile.date()
                
                # Verificar si la fecha local está en el rango solicitado
                incluir = True
                
                if fecha_inicio:
                    fecha_inicio_dt = datetime.fromisoformat(fecha_inicio.replace('Z', '+00:00')).astimezone(chile_tz).date()
                    if fecha_chile < fecha_inicio_dt:
                        incluir = False
                
                if fecha_fin and incluir:
                    fecha_fin_dt = datetime.fromisoformat(fecha_fin.replace('Z', '+00:00')).astimezone(chile_tz).date()
                    if fecha_chile > fecha_fin_dt:
                        incluir = False
                
                if incluir:
                    horarios_finales.append(horario)
            
            return {"horarios": horarios_finales}
        
        return {"horarios": horarios_filtrados}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@schedule_router.get("/horario/{horario_id}")
async def obtener_horario(horario_id: int):
    """
    Obtiene los detalles de un bloque de horario específico.
    """
    try:
        horario = supabase_client.table("horarios_personal").select(
            "id, inicio_bloque, finalizacion_bloque, usuario_sistema_id, usuario_sistema(nombre, apellido_paterno, apellido_materno)"
        ).eq("id", horario_id).execute()
        
        if not horario.data:
            raise HTTPException(status_code=404, detail="Horario no encontrado")
        
        return {"horario": horario.data[0]}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@schedule_router.put("/modificar-horario/{horario_id}")
async def modificar_horario(horario_id: int, horario: ActualizarHorario):
    """
    Modifica un bloque de horario existente.
    """
    try:
        # Verificar que existe
        existe = supabase_client.table("horarios_personal").select("id, usuario_sistema_id").eq("id", horario_id).execute()
        if not existe.data:
            raise HTTPException(status_code=404, detail="Horario no encontrado")
        
        usuario_id = existe.data[0]["usuario_sistema_id"]
        
        # Validar que no haya solapamiento con otros horarios del mismo doctor
        solapamiento = supabase_client.table("horarios_personal").select("id").eq(
            "usuario_sistema_id", usuario_id
        ).neq("id", horario_id).or_(
            f"and(inicio_bloque.lte.{horario.finalizacion_bloque.isoformat()},finalizacion_bloque.gte.{horario.inicio_bloque.isoformat()})"
        ).execute()
        
        if solapamiento.data:
            raise HTTPException(status_code=409, detail="El nuevo horario se solapa con otro existente")
        
        # Actualizar
        actualizado = supabase_client.table("horarios_personal").update({
            "inicio_bloque": horario.inicio_bloque.isoformat(),
            "finalizacion_bloque": horario.finalizacion_bloque.isoformat()
        }).eq("id", horario_id).execute()
        
        if not actualizado.data:
            raise HTTPException(status_code=500, detail="No se pudo actualizar el horario")
        
        return {"mensaje": "Horario actualizado correctamente", "horario": actualizado.data[0]}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@schedule_router.delete("/eliminar-horario/{horario_id}")
async def eliminar_horario(horario_id: int):
    """
    Elimina un bloque de horario.
    """
    try:
        # Verificar que existe
        existe = supabase_client.table("horarios_personal").select("id").eq("id", horario_id).execute()
        if not existe.data:
            raise HTTPException(status_code=404, detail="Horario no encontrado")
        
        # Eliminar
        eliminado = supabase_client.table("horarios_personal").delete().eq("id", horario_id).execute()
        
        if not eliminado.data:
            raise HTTPException(status_code=500, detail="No se pudo eliminar el horario")
        
        return {"mensaje": "Horario eliminado correctamente"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@schedule_router.delete("/eliminar-horarios-doctor/{usuario_sistema_id}")
async def eliminar_horarios_doctor(
    usuario_sistema_id: int,
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None
):
    """
    Elimina todos los horarios de un doctor en un rango de fechas.
    Si no se especifican fechas, elimina todos los horarios futuros.
    """
    try:
        query = supabase_client.table("horarios_personal").delete().eq("usuario_sistema_id", usuario_sistema_id)
        
        if fecha_inicio:
            query = query.gte("inicio_bloque", fecha_inicio)
        else:
            # Por defecto, solo eliminar horarios futuros
            query = query.gte("inicio_bloque", datetime.now(timezone.utc).isoformat())
        
        if fecha_fin:
            query = query.lte("finalizacion_bloque", fecha_fin)
        
        result = query.execute()
        
        return {"mensaje": f"Horarios eliminados correctamente", "cantidad": len(result.data or [])}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@schedule_router.get("/listar-doctores-con-horarios")
async def listar_doctores_con_horarios():
    """
    Lista todos los doctores que tienen horarios asignados.
    """
    try:
        # Obtener doctores únicos con horarios
        horarios = supabase_client.table("horarios_personal").select(
            "usuario_sistema_id"
        ).execute()
        
        if not horarios.data:
            return {"doctores": []}
        
        # Obtener IDs únicos
        doctor_ids = list(set([h["usuario_sistema_id"] for h in horarios.data]))
        
        # Obtener información de los doctores
        doctores = supabase_client.table("usuario_sistema").select(
            "id, nombre, apellido_paterno, apellido_materno, email"
        ).in_("id", doctor_ids).execute()
        
        return {"doctores": doctores.data or []}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@schedule_router.get("/horarios-disponibles")
async def listar_horarios_disponibles(
    doctor_id: int,
    fecha_inicio: str,
    fecha_fin: str,
    especialidad_id: Optional[int] = None
):
    """
    Lista los horarios disponibles (sin cita asignada) de un doctor en un rango de fechas.
    Verifica tanto horarios con horario_id asignado como citas que se solapan por fecha_atencion.
    """
    try:
        # Parsear las fechas del frontend (vienen en ISO con timezone)
        # y asegurar que estén en UTC para comparar con la BD
        fecha_inicio_dt = datetime.fromisoformat(fecha_inicio.replace('Z', '+00:00'))
        fecha_fin_dt = datetime.fromisoformat(fecha_fin.replace('Z', '+00:00'))

        print(f"DEBUG: Fechas parseadas - Inicio: {fecha_inicio_dt}, Fin: {fecha_fin_dt}")

        # Obtener todos los horarios del doctor que se solapan con el rango
        # Buscar horarios donde inicio_bloque <= fecha_fin Y finalizacion_bloque >= fecha_inicio
        query = supabase_client.table("horarios_personal").select(
            "id, inicio_bloque, finalizacion_bloque, usuario_sistema_id"
        ).eq("usuario_sistema_id", doctor_id).lte(
            "inicio_bloque", fecha_fin_dt.isoformat()
        ).gte("finalizacion_bloque", fecha_inicio_dt.isoformat()).order("inicio_bloque", desc=False)

        horarios = query.execute()

        if not horarios.data:
            print(f"DEBUG: No se encontraron horarios para doctor {doctor_id}")
            return {"horarios_disponibles": []}

        # Obtener TODAS las citas del doctor en el rango de fechas
        citas_doctor = supabase_client.table("cita_medica").select(
            "id, fecha_atencion, doctor_id, estado(estado)"
        ).eq("doctor_id", doctor_id).gte(
            "fecha_atencion", fecha_inicio_dt.isoformat()
        ).lte("fecha_atencion", fecha_fin_dt.isoformat()).execute()

        print(f"DEBUG: Doctor ID: {doctor_id}")
        print(f"DEBUG: Rango de fechas: {fecha_inicio} a {fecha_fin}")
        print(f"DEBUG: Horarios encontrados: {len(horarios.data)}")
        if horarios.data:
            for h in horarios.data:
                print(f"  - Horario {h['id']}: {h['inicio_bloque']} a {h['finalizacion_bloque']}")
        print(f"DEBUG: Citas encontradas: {len(citas_doctor.data or [])}")

        # Crear set de horarios ocupados
        horarios_ocupados = set()

        for cita in (citas_doctor.data or []):
            # Obtener el estado de la cita
            estado_list = cita.get("estado", [])
            if estado_list:
                estado_actual = estado_list[0].get("estado") if isinstance(estado_list, list) else estado_list.get("estado")
                # Ignorar citas canceladas
                if estado_actual == "Cancelada":
                    print(f"DEBUG: Ignorando cita cancelada ID {cita['id']}")
                    continue

            fecha_cita = datetime.fromisoformat(cita["fecha_atencion"].replace('Z', '+00:00'))
            print(f"DEBUG: Procesando cita {cita['id']} con fecha {fecha_cita}")

            # Verificar qué horario ocupa esta cita
            for horario in horarios.data:
                inicio = datetime.fromisoformat(horario["inicio_bloque"].replace('Z', '+00:00'))
                fin = datetime.fromisoformat(horario["finalizacion_bloque"].replace('Z', '+00:00'))

                # Si la cita está dentro del bloque de horario, marcarlo como ocupado
                if inicio <= fecha_cita < fin:
                    print(f"DEBUG: Horario {horario['id']} ocupado por cita {cita['id']}")
                    horarios_ocupados.add(horario["id"])
                    break

        # Filtrar solo horarios disponibles
        horarios_disponibles = [
            h for h in horarios.data
            if h["id"] not in horarios_ocupados
        ]

        print(f"DEBUG: Horarios ocupados: {horarios_ocupados}")
        print(f"DEBUG: Horarios disponibles finales: {len(horarios_disponibles)}")

        return {"horarios_disponibles": horarios_disponibles}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
