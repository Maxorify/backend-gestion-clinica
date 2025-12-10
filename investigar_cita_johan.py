"""
Script para investigar el problema de la cita de Johan Kurtis Gonzales
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

def investigar_problema():
    print("\n" + "=" * 80)
    print("🔍 INVESTIGANDO PROBLEMA DE CITA DE JOHAN")
    print("=" * 80)
    
    # 1. Buscar al paciente Johan
    print("\n1️⃣ BUSCANDO PACIENTE...")
    paciente_response = supabase.from_("paciente").select("*").ilike("nombre", "%johan%").execute()
    
    if not paciente_response.data:
        print("❌ No se encontró al paciente Johan")
        return
    
    paciente = paciente_response.data[0]
    print(f"✅ Paciente encontrado:")
    print(f"   ID: {paciente['id']}")
    print(f"   Nombre: {paciente['nombre']} {paciente.get('apellido_paterno', '')} {paciente.get('apellido_materno', '')}")
    print(f"   RUT: {paciente.get('rut', 'N/A')}")
    
    # 2. Buscar doctores Jose Perez y Juanito Perez
    print("\n2️⃣ BUSCANDO DOCTORES...")
    doctores_response = supabase.from_("usuario_sistema").select("*").or_("nombre.ilike.%jose%,nombre.ilike.%juanito%").eq("rol_id", 2).execute()
    
    print(f"\n✅ Doctores encontrados: {len(doctores_response.data)}")
    doctores_dict = {}
    for doc in doctores_response.data:
        nombre_completo = f"{doc['nombre']} {doc.get('apellido_paterno', '')} {doc.get('apellido_materno', '')}".strip()
        print(f"   - ID {doc['id']}: {nombre_completo}")
        doctores_dict[doc['id']] = nombre_completo
    
    # 3. Buscar TODAS las citas de Johan
    print(f"\n3️⃣ BUSCANDO TODAS LAS CITAS DE JOHAN (ID: {paciente['id']})...")
    citas_response = supabase.from_("cita_medica").select("""
        id,
        fecha_atencion,
        doctor_id,
        paciente_id,
        especialidad_id,
        horario_id,
        doctor:doctor_id(id, nombre, apellido_paterno, apellido_materno),
        especialidad:especialidad_id(nombre)
    """).eq("paciente_id", paciente['id']).order("fecha_atencion", desc=True).execute()
    
    if not citas_response.data:
        print("❌ No se encontraron citas para Johan")
        return
    
    print(f"\n✅ Citas encontradas: {len(citas_response.data)}\n")
    
    citas_por_doctor = {}
    
    for cita in citas_response.data:
        # Obtener estado
        estado_response = supabase.from_("estado").select("estado").eq("cita_medica_id", cita["id"]).order("id", desc=True).limit(1).execute()
        estado_actual = estado_response.data[0]["estado"] if estado_response.data else "Sin estado"
        
        fecha_cita = datetime.fromisoformat(cita['fecha_atencion'].replace('Z', '+00:00'))
        doctor_nombre = f"{cita['doctor']['nombre']} {cita['doctor']['apellido_paterno']}" if cita.get('doctor') else "N/A"
        especialidad_nombre = cita['especialidad']['nombre'] if cita.get('especialidad') else "N/A"
        
        print(f"📅 Cita ID {cita['id']}:")
        print(f"   ├─ Fecha: {fecha_cita.strftime('%Y-%m-%d %H:%M')}")
        print(f"   ├─ Doctor ID: {cita['doctor_id']} - {doctor_nombre}")
        print(f"   ├─ Especialidad: {especialidad_nombre}")
        print(f"   ├─ Estado: {estado_actual}")
        print(f"   └─ Horario ID: {cita.get('horario_id', 'N/A')}")
        print()
        
        # Agrupar por doctor
        if cita['doctor_id'] not in citas_por_doctor:
            citas_por_doctor[cita['doctor_id']] = []
        citas_por_doctor[cita['doctor_id']].append({
            'cita': cita,
            'estado': estado_actual
        })
    
    # 4. Verificar endpoint /doctor/{doctor_id}/citas
    print("\n4️⃣ SIMULANDO ENDPOINT /doctor/{doctor_id}/citas")
    print("=" * 80)
    
    fecha_hoy = "2025-12-09"
    
    for doctor_id, nombre_doctor in doctores_dict.items():
        print(f"\n🔍 Doctor ID {doctor_id}: {nombre_doctor}")
        
        # Simular query del endpoint
        citas_doctor = supabase.from_("cita_medica").select("""
            id,
            fecha_atencion,
            paciente_id,
            doctor_id,
            especialidad_id,
            paciente:paciente_id(id, nombre, apellido_paterno, apellido_materno, rut, telefono),
            especialidad:especialidad_id(id, nombre)
        """).eq("doctor_id", doctor_id).gte(
            "fecha_atencion", f"{fecha_hoy}T00:00:00"
        ).lte(
            "fecha_atencion", f"{fecha_hoy}T23:59:59"
        ).execute()
        
        print(f"   Citas encontradas en {fecha_hoy}: {len(citas_doctor.data or [])}")
        
        # Filtrar por Johan
        citas_johan = [c for c in (citas_doctor.data or []) if c['paciente_id'] == paciente['id']]
        
        if citas_johan:
            print(f"   ✅ Citas de Johan: {len(citas_johan)}")
            for cita in citas_johan:
                # Obtener estado
                estado_response = supabase.from_("estado").select("estado").eq("cita_medica_id", cita["id"]).order("id", desc=True).limit(1).execute()
                estado_actual = estado_response.data[0]["estado"] if estado_response.data else "Sin estado"
                
                fecha = datetime.fromisoformat(cita['fecha_atencion'].replace('Z', '+00:00'))
                print(f"      - Cita ID {cita['id']}: {fecha.strftime('%H:%M')} - Estado: {estado_actual}")
        else:
            print(f"   ⚠️  NO HAY CITAS de Johan para este doctor hoy")
    
    # 5. Verificar filtros del endpoint
    print("\n5️⃣ VERIFICANDO FILTROS DEL ENDPOINT")
    print("=" * 80)
    
    # El endpoint tiene este filtro:
    # estados=Pendiente,Confirmada,En Consulta,Completada
    
    estados_validos = ["Pendiente", "Confirmada", "En Consulta", "Completada"]
    
    print(f"\nEstados que MUESTRA el endpoint: {', '.join(estados_validos)}")
    print(f"Estados que NO MUESTRA: Cancelada\n")
    
    for doctor_id, citas_list in citas_por_doctor.items():
        doctor_nombre = doctores_dict.get(doctor_id, f"Doctor ID {doctor_id}")
        print(f"\n🔍 Citas de Johan con {doctor_nombre}:")
        
        for item in citas_list:
            cita = item['cita']
            estado = item['estado']
            fecha = datetime.fromisoformat(cita['fecha_atencion'].replace('Z', '+00:00'))
            
            mostrar = "✅ SE MUESTRA" if estado in estados_validos else "❌ NO SE MUESTRA (filtrada)"
            
            print(f"   - Cita ID {cita['id']}: {fecha.strftime('%Y-%m-%d %H:%M')} - Estado: {estado} - {mostrar}")
    
    print("\n" + "=" * 80)
    print("💡 DIAGNÓSTICO")
    print("=" * 80)
    print("""
Posibles causas por las que no aparece la cita:

1. ❌ La cita está CANCELADA → El endpoint filtra estados y solo muestra:
   - Pendiente, Confirmada, En Consulta, Completada

2. ❌ La fecha de la cita NO es HOY (2025-12-09) → El endpoint filtra por fecha

3. ❌ El doctor_id de la cita NO coincide con el doctor que está logueado

4. ❌ Hay un problema de timezone (la hora UTC no coincide con la hora Chile)

Revisa el output arriba para identificar cuál es el problema específico.
    """)

if __name__ == "__main__":
    investigar_problema()
