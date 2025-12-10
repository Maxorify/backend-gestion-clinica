"""
Script para investigar el problema de liberación de bloques al cancelar citas
"""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERROR: Variables de entorno no configuradas")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def investigar_cita_cancelada():
    print("\n" + "=" * 80)
    print("🔍 INVESTIGANDO CITAS CANCELADAS Y BLOQUES")
    print("=" * 80)
    
    # Buscar la cita de las 17:30 (5:30 PM) del 9 de diciembre con Nicolas
    fecha_busqueda = "2025-12-09"
    
    # Buscar citas del día
    citas_response = supabase.from_("cita_medica").select("""
        id,
        fecha_atencion,
        horario_id,
        doctor_id,
        paciente:paciente_id(nombre, apellido_paterno, apellido_materno),
        doctor:doctor_id(id, nombre, apellido_paterno, apellido_materno)
    """).gte("fecha_atencion", f"{fecha_busqueda}T00:00:00").lte("fecha_atencion", f"{fecha_busqueda}T23:59:59").execute()
    
    print(f"\n📋 Citas encontradas del {fecha_busqueda}: {len(citas_response.data)}\n")
    
    citas_canceladas = []
    
    for cita in citas_response.data:
        # Obtener estado actual
        estado_response = supabase.from_("estado").select("id, estado, cita_medica_id").eq("cita_medica_id", cita["id"]).order("id", desc=True).limit(1).execute()
        
        estado_actual = estado_response.data[0]["estado"] if estado_response.data else "Sin estado"
        
        fecha_cita = datetime.fromisoformat(cita['fecha_atencion'].replace('Z', '+00:00'))
        
        paciente_nombre = f"{cita['paciente']['nombre']} {cita['paciente']['apellido_paterno']}" if cita.get('paciente') else "N/A"
        doctor_nombre = f"{cita['doctor']['nombre']} {cita['doctor']['apellido_paterno']}" if cita.get('doctor') else "N/A"
        
        print(f"📅 Cita ID {cita['id']}:")
        print(f"   ├─ Fecha/Hora: {fecha_cita.strftime('%Y-%m-%d %H:%M')}")
        print(f"   ├─ Paciente: {paciente_nombre}")
        print(f"   ├─ Doctor: {doctor_nombre}")
        print(f"   ├─ Estado: {estado_actual}")
        print(f"   └─ Horario ID: {cita.get('horario_id', 'N/A')}")
        
        if estado_actual == "Cancelada":
            citas_canceladas.append(cita)
            print(f"      🔴 CITA CANCELADA - Debería liberar el bloque")
        print()
    
    if not citas_canceladas:
        print("⚠️  No se encontraron citas canceladas en esta fecha")
        return
    
    print("\n" + "=" * 80)
    print("🔧 PROBANDO ENDPOINT /horarios-disponibles")
    print("=" * 80)
    
    # Tomar la primera cita cancelada
    cita_cancelada = citas_canceladas[0]
    doctor_id = cita_cancelada.get('doctor_id')
    
    if not doctor_id:
        print("❌ No se pudo obtener el ID del doctor")
        return
    
    # Simular la consulta del endpoint
    fecha_inicio = f"{fecha_busqueda}T00:00:00"
    fecha_fin = f"{fecha_busqueda}T23:59:59"
    
    fecha_inicio_dt = datetime.fromisoformat(fecha_inicio.replace('Z', '+00:00'))
    fecha_fin_dt = datetime.fromisoformat(fecha_fin.replace('Z', '+00:00'))
    
    # Obtener horarios del doctor
    horarios = supabase.from_("horarios_personal").select(
        "id, inicio_bloque, finalizacion_bloque, usuario_sistema_id"
    ).eq("usuario_sistema_id", doctor_id).lte(
        "inicio_bloque", fecha_fin_dt.isoformat()
    ).gte("finalizacion_bloque", fecha_inicio_dt.isoformat()).order("inicio_bloque", desc=False).execute()
    
    print(f"\n📊 Horarios del doctor ID {doctor_id}: {len(horarios.data)}")
    
    # Obtener citas del doctor
    citas_doctor = supabase.from_("cita_medica").select(
        "id, fecha_atencion, doctor_id, horario_id"
    ).eq("doctor_id", doctor_id).gte(
        "fecha_atencion", fecha_inicio_dt.isoformat()
    ).lte("fecha_atencion", fecha_fin_dt.isoformat()).execute()
    
    print(f"📊 Citas del doctor: {len(citas_doctor.data)}\n")
    
    # Verificar estados de las citas
    print("🔍 ANÁLISIS DEL PROBLEMA:\n")
    
    for cita in citas_doctor.data:
        # Obtener estado
        estado_response = supabase.from_("estado").select("estado").eq("cita_medica_id", cita["id"]).order("id", desc=True).limit(1).execute()
        
        estado_actual = estado_response.data[0]["estado"] if estado_response.data else "Sin estado"
        
        fecha_cita = datetime.fromisoformat(cita['fecha_atencion'].replace('Z', '+00:00'))
        
        print(f"   Cita ID {cita['id']}: {fecha_cita.strftime('%H:%M')} - Estado: {estado_actual}")
        
        if estado_actual == "Cancelada":
            print(f"      ✅ Esta cita DEBERÍA ser ignorada al calcular bloques ocupados")
        else:
            print(f"      ⚠️  Esta cita OCUPA un bloque")
    
    # Ahora simular el endpoint con la lógica actual
    print("\n" + "=" * 80)
    print("🧪 SIMULANDO LÓGICA DEL ENDPOINT (CON EL PROBLEMA)")
    print("=" * 80)
    
    # Verificar cómo se consultan los estados en el endpoint
    citas_con_estado = supabase.from_("cita_medica").select(
        "id, fecha_atencion, doctor_id, estado(estado)"
    ).eq("doctor_id", doctor_id).gte(
        "fecha_atencion", fecha_inicio_dt.isoformat()
    ).lte("fecha_atencion", fecha_fin_dt.isoformat()).execute()
    
    print(f"\n📊 Resultado de la consulta con JOIN a 'estado':")
    print(f"Total citas: {len(citas_con_estado.data)}\n")
    
    for cita in citas_con_estado.data:
        fecha_cita = datetime.fromisoformat(cita['fecha_atencion'].replace('Z', '+00:00'))
        
        print(f"Cita ID {cita['id']}: {fecha_cita.strftime('%H:%M')}")
        print(f"   Datos de 'estado': {cita.get('estado')}")
        
        estado_list = cita.get("estado", [])
        if estado_list:
            if isinstance(estado_list, list):
                print(f"   ⚠️  Es una LISTA con {len(estado_list)} elementos")
                for i, est in enumerate(estado_list):
                    print(f"      [{i}] {est}")
                estado_actual = estado_list[0].get("estado") if estado_list else None
            else:
                print(f"   ✅ Es un OBJETO: {estado_list}")
                estado_actual = estado_list.get("estado")
            
            print(f"   Estado extraído: {estado_actual}")
            
            if estado_actual == "Cancelada":
                print(f"   ✅ DEBERÍA SER IGNORADA")
            else:
                print(f"   ⚠️  OCUPA UN BLOQUE")
        else:
            print(f"   ❌ Sin datos de estado")
        print()
    
    print("\n" + "=" * 80)
    print("💡 DIAGNÓSTICO")
    print("=" * 80)
    print("""
El problema está en cómo Supabase retorna el JOIN con la tabla 'estado'.

Cuando hacemos:
    .select("id, fecha_atencion, doctor_id, estado(estado)")
    
Supabase retorna TODOS los registros de la tabla 'estado' para cada cita,
no solo el más reciente.

SOLUCIÓN:
En lugar de hacer el JOIN, debemos consultar el estado de cada cita
individualmente usando una query separada con .order("id", desc=True).limit(1)
para obtener solo el estado más reciente.
    """)

if __name__ == "__main__":
    investigar_cita_cancelada()
