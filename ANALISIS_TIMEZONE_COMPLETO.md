# 📊 ANÁLISIS EXHAUSTIVO: Lógica de Timezone en Frontend

## 🎯 OBJETIVO
Alinear TODOS los archivos con la lógica definida en `asistencia.jsx`

---

## 📘 LÓGICA MAESTRA: asistencia.jsx

### 🔧 Función parseUTCDate()
```javascript
const parseUTCDate = (dateString) => {
  if (!dateString) return null;

  try {
    const utcDate = new Date(dateString);
    
    if (isNaN(utcDate.getTime())) {
      console.error("❌ Fecha inválida parseada:", dateString);
      return null;
    }

    // CLAVE: Extrae componentes UTC y crea fecha LOCAL con esos valores
    return new Date(
      utcDate.getUTCFullYear(),
      utcDate.getUTCMonth(),
      utcDate.getUTCDate(),
      utcDate.getUTCHours(),      // ← HORA UTC LITERAL
      utcDate.getUTCMinutes(),    // ← MINUTO UTC LITERAL
      utcDate.getUTCSeconds()
    );
  } catch (error) {
    console.error("❌ Error al parsear fecha:", dateString, error);
    return null;
  }
};
```

### 📌 Funciones de Formateo
```javascript
// 1. formatDateTime - Fecha y hora completas
const formatDateTime = (dateTimeString) => {
  if (!dateTimeString) return "-";
  const date = parseUTCDate(dateTimeString);
  if (!date) return "-";
  return date.toLocaleString("es-CL", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

// 2. formatTime - Solo hora
const formatTime = (dateTimeString) => {
  if (!dateTimeString) return "-";
  const date = parseUTCDate(dateTimeString);
  if (!date) return "-";
  return date.toLocaleTimeString("es-CL", {
    hour: "2-digit",
    minute: "2-digit",
  });
};

// 3. formatDate - Solo fecha
const formatDate = (dateTimeString) => {
  if (!dateTimeString) return "-";
  const date = parseUTCDate(dateTimeString);
  if (!date) return "-";
  return date.toLocaleDateString("es-CL", {
    day: "2-digit",
    month: "2-digit",
  });
};

// 4. calcularHorasTrabajadas - Diferencia entre fechas
const calcularHorasTrabajadas = (inicio, fin) => {
  if (!inicio || !fin) return 0;
  const inicioDate = parseUTCDate(inicio);
  const finDate = parseUTCDate(fin);
  if (!inicioDate || !finDate) return 0;
  return (finDate - inicioDate) / 1000 / 60 / 60;
};
```

---

## 🔍 ANÁLISIS ARCHIVO POR ARCHIVO

### 1️⃣ CitasDoctor.jsx

#### ✅ TIENE parseUTCDate() (CORRECTO)
```javascript
const parseUTCDate = (dateString) => {
  if (!dateString) return null;
  try {
    const utcDate = new Date(dateString);
    if (isNaN(utcDate.getTime())) {
      console.error("❌ Fecha inválida:", dateString);
      return null;
    }
    return new Date(
      utcDate.getUTCFullYear(),
      utcDate.getUTCMonth(),
      utcDate.getUTCDate(),
      utcDate.getUTCHours(),
      utcDate.getUTCMinutes(),
      utcDate.getUTCSeconds()
    );
  } catch (error) {
    console.error("❌ Error al parsear fecha:", dateString, error);
    return null;
  }
};
```

#### ❌ FALTA: Funciones de formateo
- NO tiene `formatDateTime()`
- NO tiene `formatTime()` 
- NO tiene `formatDate()`

#### ❌ USO DIRECTO EN JSX
Usa `parseUTCDate()` directamente en el JSX:
```javascript
{parseUTCDate(consulta.fecha_atencion)?.toLocaleDateString("es-CL", {...})}
{parseUTCDate(cita.fecha_atencion)?.toLocaleTimeString("es-CL", {...})}
```

#### 🎯 SOLUCIÓN REQUERIDA:
1. Agregar funciones `formatDateTime()`, `formatTime()`, `formatDate()`
2. Reemplazar todos los usos directos con las funciones helper

---

### 2️⃣ DashboardDoctor.jsx

#### ❌ parseUTCDate() INCORRECTO
```javascript
const parseUTCDate = (dateString) => {
  if (!dateString) return null;
  return new Date(dateString);  // ← ¡INCORRECTO! No extrae componentes UTC
};
```

#### ❌ FALTA TODO:
- parseUTCDate() está MAL implementado (no extrae componentes UTC)
- NO tiene `formatDateTime()`
- NO tiene `formatTime()` 
- NO tiene `formatDate()`
- NO tiene `calcularHorasTrabajadas()`

#### ❌ USO DIRECTO DE new Date()
```javascript
{new Date(cita.fecha_atencion).toLocaleTimeString("es-CL", {...})}
```

#### 🎯 SOLUCIÓN REQUERIDA:
1. REEMPLAZAR parseUTCDate() con la versión correcta de asistencia.jsx
2. Agregar TODAS las funciones de formateo
3. Reemplazar todos los `new Date()` directos con funciones helper

---

### 3️⃣ historiaMedica.jsx

#### ❌ NO TIENE parseUTCDate()
Archivo NO tiene la función parseUTCDate() definida

#### ❌ FALTA TODO:
- NO tiene `parseUTCDate()`
- NO tiene `formatDateTime()`
- NO tiene `formatTime()` 
- NO tiene `formatDate()`

#### ❌ USO DIRECTO DE new Date()
No se ve uso directo en el summary, pero debe estar usando Date en algún lugar

#### 🎯 SOLUCIÓN REQUERIDA:
1. Agregar `parseUTCDate()` completo
2. Agregar TODAS las funciones de formateo
3. Buscar y reemplazar cualquier uso directo de Date

---

### 4️⃣ recepcion.jsx (Secretaria)

#### ❌ NO TIENE parseUTCDate()
Archivo NO tiene la función parseUTCDate() definida

#### ❌ FALTA TODO:
- NO tiene `parseUTCDate()`
- NO tiene `formatDateTime()`
- NO tiene `formatTime()` 
- NO tiene `formatDate()`

#### ✅ TIENE formatearFecha() (PERSONALIZADA)
```javascript
const formatearFecha = (fecha) => {
  // Implementación personalizada
};
```

#### 🎯 SOLUCIÓN REQUERIDA:
1. Agregar `parseUTCDate()` completo
2. Agregar TODAS las funciones de formateo de asistencia.jsx
3. Evaluar si mantener `formatearFecha()` o usar `formatDate()`
4. Buscar y reemplazar cualquier uso directo de Date

---

## 📋 RESUMEN DE INCONSISTENCIAS

### ❌ PROBLEMAS CRÍTICOS ENCONTRADOS:

1. **DashboardDoctor.jsx**: parseUTCDate() MAL IMPLEMENTADO
   - Solo hace `return new Date(dateString)` 
   - NO extrae componentes UTC
   - Causa conversión automática de timezone ❌

2. **CitasDoctor.jsx**: FALTA funciones helper
   - Tiene parseUTCDate() correcto ✅
   - Pero usa parseUTCDate() DIRECTAMENTE en JSX ❌
   - Debería usar formatTime(), formatDate(), etc.

3. **historiaMedica.jsx**: FALTA TODO
   - No tiene parseUTCDate()
   - No tiene funciones de formateo

4. **recepcion.jsx**: FALTA TODO
   - No tiene parseUTCDate()
   - No tiene funciones de formateo
   - Tiene formatearFecha() personalizada (revisar compatibilidad)

---

## ✅ PLAN DE CORRECCIÓN

### 📦 PASO 1: Crear archivo compartido de utilidades (OPCIONAL)
Crear `src/utils/dateHelpers.js` con:
- parseUTCDate()
- formatDateTime()
- formatTime()
- formatDate()
- calcularHorasTrabajadas()

**O** copiar estas funciones en cada archivo (más redundante pero más explícito)

### 🔧 PASO 2: Correcciones por archivo

#### DashboardDoctor.jsx
```javascript
// ❌ REEMPLAZAR
const parseUTCDate = (dateString) => {
  if (!dateString) return null;
  return new Date(dateString);
};

// ✅ POR ESTO
const parseUTCDate = (dateString) => {
  if (!dateString) return null;
  try {
    const utcDate = new Date(dateString);
    if (isNaN(utcDate.getTime())) {
      console.error("❌ Fecha inválida parseada:", dateString);
      return null;
    }
    return new Date(
      utcDate.getUTCFullYear(),
      utcDate.getUTCMonth(),
      utcDate.getUTCDate(),
      utcDate.getUTCHours(),
      utcDate.getUTCMinutes(),
      utcDate.getUTCSeconds()
    );
  } catch (error) {
    console.error("❌ Error al parsear fecha:", dateString, error);
    return null;
  }
};

// ✅ AGREGAR
const formatDateTime = (dateTimeString) => { /* ... */ };
const formatTime = (dateTimeString) => { /* ... */ };
const formatDate = (dateTimeString) => { /* ... */ };
```

Buscar todos los usos de:
```javascript
new Date(cita.fecha_atencion).toLocaleTimeString(...)
```

Reemplazar por:
```javascript
formatTime(cita.fecha_atencion)
```

#### CitasDoctor.jsx
```javascript
// ✅ AGREGAR (parseUTCDate ya está correcto)
const formatDateTime = (dateTimeString) => { /* ... */ };
const formatTime = (dateTimeString) => { /* ... */ };
const formatDate = (dateTimeString) => { /* ... */ };
```

Buscar todos los usos de:
```javascript
parseUTCDate(cita.fecha_atencion)?.toLocaleTimeString(...)
parseUTCDate(cita.fecha_atencion)?.toLocaleDateString(...)
```

Reemplazar por:
```javascript
formatTime(cita.fecha_atencion)
formatDate(cita.fecha_atencion)
```

#### historiaMedica.jsx
```javascript
// ✅ AGREGAR TODO
const parseUTCDate = (dateString) => { /* ... */ };
const formatDateTime = (dateTimeString) => { /* ... */ };
const formatTime = (dateTimeString) => { /* ... */ };
const formatDate = (dateTimeString) => { /* ... */ };
```

Buscar y reemplazar usos directos de `new Date()`

#### recepcion.jsx
```javascript
// ✅ AGREGAR TODO
const parseUTCDate = (dateString) => { /* ... */ };
const formatDateTime = (dateTimeString) => { /* ... */ };
const formatTime = (dateTimeString) => { /* ... */ };
const formatDate = (dateTimeString) => { /* ... */ };
```

Evaluar si mantener `formatearFecha()` o migrar a `formatDate()`

---

## 🎯 RESULTADO ESPERADO

Después de las correcciones:

1. ✅ **Consistencia total**: Todos los archivos usan la misma lógica
2. ✅ **Sin conversión automática**: parseUTCDate extrae componentes UTC literales
3. ✅ **Formato uniforme**: Todas las fechas se muestran igual
4. ✅ **Mantenibilidad**: Un solo lugar para cambiar lógica de fechas

---

## ⚠️ NOTA IMPORTANTE: ¿Por qué muestra 00:00 en vez de 21:00?

La lógica de `asistencia.jsx` extrae componentes UTC LITERALES:

```
BD: 2025-12-10T00:00:00Z (UTC)
     ↓ parseUTCDate extrae: hora=0, minuto=0
     ↓ Crea Date local: 2025-12-10 00:00 (local)
     ↓ formatTime muestra: 00:00
```

**Esto es CORRECTO** si el backend está guardando las fechas en hora Chile como UTC.

**Pero si el backend guarda UTC REAL (21:00 Chile = 00:00 UTC siguiente día):**
- parseUTCDate mostrará 00:00 (componente UTC literal)
- Para mostrar 21:00 necesitaríamos RESTAR 3 horas

### 🤔 PREGUNTA CLAVE:
¿Cómo guarda el backend las fechas en asistencia vs citas?

**Asistencia:**
- Entrada a las 08:00 Chile → ¿Guarda 08:00 UTC o 11:00 UTC?

**Citas:**
- Cita a las 21:00 Chile → Guarda 00:00 UTC siguiente día

Si son diferentes, la lógica de parseUTCDate NO puede ser la misma para ambos.

---

## 🔬 VERIFICACIÓN REQUERIDA

Necesito que me confirmes:

1. ¿En `asistencia`, una marca de entrada a las 08:00 AM hora Chile se guarda como?
   - A) `08:00:00 UTC` (sin conversión)
   - B) `11:00:00 UTC` (con conversión UTC+3)

2. ¿En `citas`, una cita a las 21:00 hora Chile se guarda como?
   - A) `21:00:00 UTC` (sin conversión) 
   - B) `00:00:00 UTC día siguiente` (con conversión UTC+3) ← **ESTO es lo que vimos**

Si la respuesta es diferente (A para asistencia, B para citas), entonces:
- **parseUTCDate NO puede ser universal**
- Necesitaríamos DOS lógicas diferentes

Si la respuesta es B para ambos:
- **parseUTCDate debe convertir UTC → Chile**
- Debe RESTAR 3 horas antes de formatear
