"""
Script para verificar el historial médico de Aaron
"""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime, timedelta

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERROR: Variables de entorno no configuradas")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def buscar_aaron():
    print("\n" + "=" * 80)
    print("🔍 BUSCANDO PACIENTE AARON")
    print("=" * 80)
    
    # Buscar paciente Aaron
    response = supabase.from_("paciente").select("*").ilike("nombre", "%aaron%").execute()
    
    if not response.data:
        print("❌ No se encontró al paciente Aaron")
        return None
    
    paciente = response.data[0]
    print(f"\n✅ Paciente encontrado:")
    print(f"   ID: {paciente['id']}")
    print(f"   Nombre: {paciente['nombre']} {paciente.get('apellido_paterno', '')} {paciente.get('apellido_materno', '')}")
    print(f"   RUT: {paciente.get('rut', 'N/A')}")
    
    return paciente

def verificar_citas(paciente_id):
    print("\n" + "=" * 80)
    print("📋 VERIFICANDO CITAS DEL PACIENTE")
    print("=" * 80)
    
    # Buscar citas
    citas_response = supabase.from_("cita_medica").select("""
        id,
        fecha_atencion,
        doctor:doctor_id(nombre, apellido_paterno, apellido_materno),
        especialidad:especialidad_id(nombre)
    """).eq("paciente_id", paciente_id).order("fecha_atencion", desc=True).execute()
    
    if not citas_response.data:
        print("❌ No se encontraron citas para este paciente")
        return []
    
    print(f"\n✅ Total de citas encontradas: {len(citas_response.data)}\n")
    
    citas_con_estado = []
    for cita in citas_response.data:
        # Obtener estado
        estado_response = supabase.from_("estado").select("estado").eq("cita_medica_id", cita["id"]).order("id", desc=True).limit(1).execute()
        estado = estado_response.data[0]["estado"] if estado_response.data else "Sin estado"
        
        fecha_atencion = datetime.fromisoformat(cita['fecha_atencion'].replace('Z', '+00:00'))
        
        doctor_nombre = f"{cita['doctor']['nombre']} {cita['doctor']['apellido_paterno']}" if cita.get('doctor') else "N/A"
        especialidad_nombre = cita['especialidad']['nombre'] if cita.get('especialidad') else "N/A"
        
        print(f"📅 Cita ID {cita['id']}:")
        print(f"   ├─ Fecha: {fecha_atencion.strftime('%Y-%m-%d %H:%M')}")
        print(f"   ├─ Doctor: {doctor_nombre}")
        print(f"   ├─ Especialidad: {especialidad_nombre}")
        print(f"   └─ Estado: {estado}")
        
        # Verificar información de consulta
        info_response = supabase.from_("informacion_cita").select("*").eq("cita_medica_id", cita["id"]).execute()
        if info_response.data:
            print(f"      └─ ✅ Tiene información de consulta")
        else:
            print(f"      └─ ⚠️  Sin información de consulta")
        print()
        
        citas_con_estado.append({
            'cita': cita,
            'estado': estado,
            'tiene_info': bool(info_response.data)
        })
    
    return citas_con_estado

def verificar_historial_endpoint(paciente_id):
    print("\n" + "=" * 80)
    print("🔧 SIMULANDO ENDPOINT /paciente/{paciente_id}/historial-medico")
    print("=" * 80)
    
    # Obtener citas
    citas_response = supabase.from_("cita_medica").select("""
        id,
        fecha_atencion,
        doctor_id,
        especialidad_id,
        doctor:doctor_id(id, nombre, apellido_paterno, apellido_materno),
        especialidad:especialidad_id(id, nombre)
    """).eq("paciente_id", paciente_id).order("fecha_atencion", desc=True).execute()
    
    if not citas_response.data:
        print("❌ No se encontraron citas")
        return []
    
    historial = []
    
    for cita in citas_response.data:
        # Obtener estado
        estado_response = supabase.from_("estado").select("estado").eq("cita_medica_id", cita["id"]).order("id", desc=True).limit(1).execute()
        estado_actual = estado_response.data[0]["estado"] if estado_response.data else "Sin estado"
        
        print(f"\n📋 Procesando Cita ID {cita['id']} - Estado: {estado_actual}")
        
        # Solo incluir citas completadas
        if estado_actual != "Completada":
            print(f"   ⏭️  Omitida (no completada)")
            continue
        
        # Obtener información de consulta
        info_consulta_response = supabase.from_("informacion_cita").select("*").eq("cita_medica_id", cita["id"]).execute()
        
        if not info_consulta_response.data:
            print(f"   ⚠️  Sin información de consulta")
            continue
        
        info_consulta = info_consulta_response.data[0]
        print(f"   ✅ Tiene información de consulta (ID: {info_consulta['id']})")
        
        # Obtener diagnóstico
        diagnostico = None
        if info_consulta.get("diagnostico_id"):
            diag_response = supabase.from_("diagnosticos").select("id, nombre_enfermedad").eq("id", info_consulta["diagnostico_id"]).execute()
            if diag_response.data:
                diagnostico = diag_response.data[0]
                print(f"   └─ Diagnóstico: {diagnostico['nombre_enfermedad']}")
        
        # Obtener recetas
        recetas_response = supabase.from_("receta").select("*").eq("informacion_cita_id", info_consulta["id"]).execute()
        recetas = recetas_response.data if recetas_response.data else []
        print(f"   └─ Recetas: {len(recetas)}")
        
        historial.append({
            'cita_id': cita['id'],
            'fecha': cita['fecha_atencion'],
            'doctor': cita.get('doctor'),
            'especialidad': cita.get('especialidad'),
            'tiene_consulta': True,
            'tiene_diagnostico': diagnostico is not None,
            'num_recetas': len(recetas)
        })
    
    print(f"\n📊 RESUMEN:")
    print(f"   ├─ Total citas: {len(citas_response.data)}")
    print(f"   ├─ Citas completadas: {len(historial)}")
    print(f"   └─ Citas en historial: {len(historial)}")
    
    return historial

if __name__ == "__main__":
    paciente = buscar_aaron()
    
    if paciente:
        citas = verificar_citas(paciente['id'])
        historial = verificar_historial_endpoint(paciente['id'])
        
        print("\n" + "=" * 80)
        print("✅ VERIFICACIÓN COMPLETADA")
        print("=" * 80)
        
        if len(historial) == 0:
            print("\n⚠️  PROBLEMA DETECTADO:")
            print("   El paciente tiene citas pero ninguna está 'Completada' o no tienen información de consulta")
            print("\n💡 SOLUCIÓN:")
            print("   1. Asegúrate de que las citas tengan estado 'Completada'")
            print("   2. Verifica que las citas completadas tengan información en la tabla 'informacion_cita'")
