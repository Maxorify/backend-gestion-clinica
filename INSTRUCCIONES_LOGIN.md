# Sistema de Login - Instrucciones

## Resumen de cambios

El sistema de autenticación ahora usa la tabla `contraseñas` de la base de datos PostgreSQL en lugar de Supabase Auth.

## Estructura de la Base de Datos

### Tabla `usuario_sistema`
Contiene la información básica del usuario:
- email (único)
- nombre, apellido_paterno, apellido_materno
- rut, celular, dirección
- rol_id (FK a tabla `rol`)

### Tabla `contraseñas`
Contiene las contraseñas de los usuarios:
- id_profesional_salud (FK a `usuario_sistema.id`)
- contraseña (puede ser texto plano o hasheada con bcrypt)
- contraseña_temporal (opcional, para recuperación)

### Tabla `rol`
Define los roles del sistema:
- id
- nombre (debe ser: "medico", "admin", o "secretaria" en minúsculas)
- descripcion

## Configuración del Backend

### Puerto
El backend debe ejecutarse en el puerto **5000**:

```bash
cd backend-gestion-clinica
uvicorn src.main:app --reload --port 5000
```

### Endpoints disponibles

#### POST /auth/login
Autentica un usuario y retorna sus datos con la URL de redirección.

**Request:**
```json
{
  "email": "usuario@ejemplo.com",
  "password": "contraseña123"
}
```

**Response exitosa:**
```json
{
  "success": true,
  "message": "Bienvenido/a Juan Pérez",
  "data": {
    "id": 1,
    "nombre": "Juan",
    "apellido_paterno": "Pérez",
    "apellido_materno": "García",
    "email": "juan@ejemplo.com",
    "rut": "12345678-9",
    "rol_id": 1,
    "rol_nombre": "medico",
    "especialidad_id": 2,
    "especialidad_nombre": "Cardiología",
    "auth_token": "token_aleatorio_generado"
  },
  "redirect_url": "/doctor/dashboard"
}
```

**Errores posibles:**
- 401: Email o contraseña incorrectos
- 403: Usuario sin rol asignado o rol no autorizado
- 500: Error del servidor

#### POST /auth/logout
Cierra la sesión del usuario.

## Redirecciones según rol

| Rol | URL de redirección |
|-----|-------------------|
| medico | /doctor/dashboard |
| admin | /admin/dashboard |
| secretaria | /secretaria/dashboard |

## Seguridad

### Soporte para contraseñas hasheadas
El sistema soporta tanto contraseñas en texto plano como hasheadas con bcrypt:

- **Contraseñas hasheadas** (RECOMENDADO): Empiezan con `$2b$` o `$2a$`
- **Texto plano** (NO RECOMENDADO): Se validan con comparación directa

### Cómo hashear contraseñas

Para crear una contraseña hasheada:

```python
import bcrypt

password = "mi_contraseña_segura"
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
print(hashed.decode('utf-8'))
# Resultado: $2b$12$...
```

### Ejemplo de inserción de usuario con contraseña hasheada

```sql
-- 1. Insertar usuario
INSERT INTO usuario_sistema (nombre, apellido_paterno, apellido_materno, email, rut, rol_id)
VALUES ('Juan', 'Pérez', 'García', 'juan@ejemplo.com', '12345678-9', 1);

-- 2. Insertar contraseña hasheada (el hash debe generarse con bcrypt)
INSERT INTO contraseñas (id_profesional_salud, contraseña)
VALUES (1, '$2b$12$KIXxLVZ5yJYn7ZqhF6y8O.qN8vK9L5X3Z4R2Y8W9Q7K6N5M4L3J2I1');
```

## Protección de rutas en el Frontend

### Componente ProtectedRoute
Ubicación: `front-clinica/src/components/ProtectedRoute.jsx`

Funciones:
- Verifica que exista un usuario en localStorage
- Valida que el token de autenticación esté presente
- Comprueba que el rol del usuario esté permitido para la ruta
- Redirige a `/` (login) si no está autenticado
- Redirige al dashboard correspondiente si no tiene permiso

### Rutas protegidas
Todas las rutas de admin, doctor y secretaria están protegidas:

```jsx
// Solo usuarios con rol "admin"
<Route element={<ProtectedRoute allowedRoles={['admin']}><Layout/></ProtectedRoute>}>
  <Route path="/admin/dashboard" element={<Dashboard />} />
  ...
</Route>

// Solo usuarios con rol "medico"
<Route element={<ProtectedRoute allowedRoles={['medico']}><LayoutDoctor/></ProtectedRoute>}>
  <Route path="/doctor/dashboard" element={<DashboardDoctor />} />
  ...
</Route>

// Solo usuarios con rol "secretaria"
<Route element={<ProtectedRoute allowedRoles={['secretaria']}><LayoutSecretaria/></ProtectedRoute>}>
  <Route path="/secretaria/dashboard" element={<DashboardSecretaria />} />
  ...
</Route>
```

## Configuración inicial de la Base de Datos

### 1. Crear roles
```sql
INSERT INTO rol (nombre, descripcion) VALUES
('admin', 'Administrador del sistema'),
('medico', 'Médico profesional'),
('secretaria', 'Secretaria administrativa');
```

### 2. Crear un usuario de prueba (Admin)
```sql
-- Insertar usuario
INSERT INTO usuario_sistema (nombre, apellido_paterno, apellido_materno, email, rut, rol_id)
VALUES ('Admin', 'Sistema', 'Test', 'admin@clinica.com', '11111111-1',
  (SELECT id FROM rol WHERE nombre = 'admin'));

-- Insertar contraseña (para pruebas, texto plano: "admin123")
-- En producción, usa contraseñas hasheadas
INSERT INTO contraseñas (id_profesional_salud, contraseña)
VALUES (
  (SELECT id FROM usuario_sistema WHERE email = 'admin@clinica.com'),
  'admin123'
);
```

### 3. Crear un médico de prueba
```sql
-- Insertar especialidad (si no existe)
INSERT INTO especialidad (nombre, descripcion)
VALUES ('Medicina General', 'Especialidad en medicina general');

-- Insertar usuario médico
INSERT INTO usuario_sistema (nombre, apellido_paterno, apellido_materno, email, rut, rol_id)
VALUES ('Dr. Carlos', 'Ramírez', 'López', 'doctor@clinica.com', '22222222-2',
  (SELECT id FROM rol WHERE nombre = 'medico'));

-- Insertar contraseña (texto plano: "doctor123")
INSERT INTO contraseñas (id_profesional_salud, contraseña)
VALUES (
  (SELECT id FROM usuario_sistema WHERE email = 'doctor@clinica.com'),
  'doctor123'
);

-- Asignar especialidad al médico
INSERT INTO especialidades_doctor (usuario_sistema_id, especialidad_id)
VALUES (
  (SELECT id FROM usuario_sistema WHERE email = 'doctor@clinica.com'),
  (SELECT id FROM especialidad WHERE nombre = 'Medicina General')
);
```

## Testing

### Prueba de login desde el frontend
1. Iniciar backend: `uvicorn src.main:app --reload --port 5000`
2. Iniciar frontend: `npm run dev`
3. Ir a `http://localhost:5173`
4. Usar credenciales de prueba:
   - Email: `admin@clinica.com`
   - Password: `admin123`

### Prueba con cURL
```bash
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@clinica.com","password":"admin123"}'
```

## Notas importantes

1. **Nombres de roles**: Deben ser exactamente "medico", "admin" o "secretaria" en minúsculas
2. **Puerto del backend**: Debe ser 5000 (configurado en Login.jsx línea 43)
3. **CORS**: El backend acepta requests desde cualquier origen (configurado en main.py)
4. **Seguridad**: Se recomienda usar contraseñas hasheadas en producción
5. **Token**: Actualmente es un token aleatorio simple. Para producción, considera usar JWT

## Mejoras futuras recomendadas

1. Implementar JWT (JSON Web Tokens) para tokens más seguros
2. Agregar refresh tokens para renovar sesiones
3. Implementar rate limiting en el endpoint de login
4. Agregar logs de intentos de login
5. Implementar recuperación de contraseña
6. Agregar autenticación de dos factores (2FA)
