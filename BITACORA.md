
# Bitácora del Laboratorio de Seguridad (S-SDLC)

> Registro de decisiones, configuraciones y avances del proyecto.

---
## Inicialización y configuración base
### 1. Estandarización del proyecto y dependencias con **uv**
**Qué se hizo:**
-  `uv init` → estructura mínima (`pyproject.toml`, `.python-version`, `README.md`, `main.py`)
-  `uv add flask flask-sqlalchemy flask-login werkzeug` → dependencias de producción
-  `uv add --dev pytest pytest-cov ruff` → dependencias de desarrollo
- Eliminado boilerplate (`main.py`, README mínimo)

**Importancia:**
-  **Reproducibilidad**: `uv.lock` garantiza que todos los desarrolladores y CI usen **exactamente las mismas versiones** de dependencias transitivas.
-  **Velocidad**: `uv` es 10-100x más rápido que `pip`/`poetry` para resolver e instalar.
-  **Aislamiento**: `.venv` local evita contaminar el Python del sistema.
-  **Estándar moderno**: `pyproject.toml` (PEP 621) es el formato oficial de empaquetado Python; `uv` lo soporta nativamente.

---
### 2. `.gitignore` robusto y planificado para el proyecto
**Qué se hizo:**
Creado `.gitignore` con secciones categorizadas:
- Python/UV (`__pycache__`, `.venv/`, `uv.lock`*)
- Base de datos SQLite (`*.db`, `*.sqlite*`)
-  **Uploads** (`uploads/`) — crítico por la vulnerabilidad 4
- Secrets/Env (`.env*`, `.env.*.local`)
- IDE, OS, Logs, Testing, Dist, Type checking

> *Nota: `uv.lock` se mantuvo ignorado inicialmente; luego se versionó para builds reproducibles.

**Importancia:**
-  **Primera capa contra exposición de secretos**: Evita commitear `.env`, `*.db` con credenciales, `uploads/` con shells subidos, `.venv/` con binarios.
-  **Hygiene de repo**: Mantiene el historial limpio (sin `__pycache__`, `.DS_Store`, `.pytest_cache`).
-  **Seguridad específica del lab**: `uploads/` está ignorado porque la vulnerabilidad 4 permite subir **cualquier archivo** (`.php`, `.py`, shells); si se commiteara, el repo distribuiría malware accidental.
-  **Colaboración**: Cualquier clon del repo arranca limpio sin basura local de otros.

---
### 3. Importación de dependencias que servirán más adelante
**Qué se hizo:**
Agregadas a `pyproject.toml` → `dependencies`:
| Paquete | Versión | Propósito futuro |
|--|--|--|
| `flask-sqlalchemy`  | ≥3.1 | ORM + queries parametrizadas → **mitiga SQLi** |
| `flask-login` | ≥0.6 | Gestión de sesiones/autenticación → base para **arreglar IDOR y login** |
| `werkzeug` | ≥3.0 | `generate_password_hash`/`check_password_hash` → **hash de contraseñas** (no plaintext) |

**Importancia:**
-  **Defensa en profundidad**: Cada dependencia ataca una vulnerabilidad del lab:
- SQLAlchemy ORM → elimina concatenación de strings en SQL (vuln 1)
- Flask-Login → `login_required`, `current_user` → base para autorización (vuln 3)
- Werkzeug security → `pbkdf2:sha256` hash → elimina passwords en texto plano (BD actual)
-  **Instalación temprana**: Evita "dependency hell" después; el lockfile fija versiones compatibles desde día 1.
-  **Desarrollo guiado por tests**: `pytest`, `ruff` en dev-deps permiten TDD y lint desde el primer commit.

---
### 4. Archivo de configuración basado en entornos (`config.py`)
**Qué se hizo:**

`config.py` con patrón **Factory/Strategy**:

```python
class  Config: # Base común
class  DevelopmentConfig(Config): # DEBUG=True, cookies inseguras
class  ProductionConfig(Config): # DEBUG=False, SESSION_COOKIE_SECURE=True
class  TestingConfig(Config): # BD en memoria, CSRF off

config = {"development": ..., "production": ..., "testing": ..., "default": ...}
```

`app.py` carga con:
```python
app.config.from_object(config[os.getenv("FLASK_ENV", "default")])
```

**Importancia:**
-  **Despliegue sin cambios de código**: Para ir a producción basta `export FLASK_ENV=production` — **ningún archivo se modifica**.
-  **Seguridad por defecto**: `DevelopmentConfig` usa cookies inseguras (HTTP, `Secure=False`) para que funcione en `localhost`; `ProductionConfig` fuerza `Secure=True`, `HttpOnly=True`, `SameSite=Lax` — evita robo de sesión en HTTPS real.
-  **Tests aislados**: `TestingConfig` usa `sqlite:///:memory:` → tests corren en BD efímera, sin tocar `academia.db` ni requerir setup/teardown complejo.
-  **12-Factor App**: Config en entorno (`.env`/`env vars`), no en código. `SECRET_KEY`, `DATABASE_URL` vienen de `os.environ.get()`.
-  **Auditoría**: Un diff de `config.py` muestra **exactamente** qué cambia entre entornos (no hay "magic values" esparcidos en `app.py`).

---
### 5. Configuración de host y puerto externalizada (`HOST`, `PORT`)
**Qué se hizo:**
- Agregados `HOST` y `PORT` a la clase base `Config` en `config.py` con valores por defecto `127.0.0.1` y `5000`, leídos desde variables de entorno.
- Actualizado `app.py` para usar `app.config["HOST"]` y `app.config["PORT"]` en el bloque `if __name__ == "__main__"`.
- Agregadas variables `HOST` y `PORT` al archivo `.env`.

**Importancia:**
-  **12-Factor App**: Configuración mediante variables de entorno, no hardcodeada. Permite cambiar host/puerto sin tocar código.
-  **Docker/Cloud ready**: En contenedores se usa `HOST=0.0.0.0` y `PORT=8000` (o el que asigne la plataforma) sin rebuild de imagen.
-  **Desarrollo flexible**: Diferentes desarrolladores pueden usar puertos distintos (`PORT=5001`, `PORT=3000`) solo editando su `.env` local.
-  **Separación de responsabilidades**: El bloque `if __name__ == "__main__"` es solo para desarrollo local; producción usa Gunicorn que ignora este bloque y lee su propia config (`-b 0.0.0.0:8000`).