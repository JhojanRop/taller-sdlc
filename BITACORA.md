
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

---

## Implementación Shift-Left (quality gates + releases automáticos)

### 6. `pre-commit` con calidad y seguridad
**Qué se hizo:**
- `uv add --dev pre-commit` → `.pre-commit-config.yaml` versionado por etapas.
- Hooks: sanitización (`trailing-whitespace`, `end-of-file-fixer`, `check-toml`, `check-merge-conflict`, `debug-statements`), `detect-private-key`, `gitleaks v8.30.1` (secrets en el diff), `ruff check --fix` + `ruff format` (misma config del proyecto).
- Primer `pre-commit run --all-files` → commit de normalización mecánica (`style: normalize existing files`).

**Importancia:**
- **Shift-Left de verdad**: los issues se detectan *antes* del commit, no en revisión/CI.
- **Secrets nunca llegan al repo**: gitleaks bloquea en el momento del `git commit`; más barato que rotar credenciales filtradas.
- **Format/lint homogéneos**: reutiliza el `ruff` ya configurado (line-length 100, select E/F/I/UP/W).

**Notas de implementación (límites encontrados):**
- `sh -c '...' arg1 arg2...`: el primer arg se convierte en `$0` — los chequeos posicionales deben iterar `$@`.
- Pre-commit 4.x entrega el contexto del push en **env vars**, no args posicionales: `PRE_COMMIT_REMOTE_BRANCH`, `PRE_COMMIT_LOCAL_BRANCH`, etc.
- `git push --dry-run` **no invoca** el hook `pre-push` con refs → para probar el bloqueo se usa un remoto bare de juguete (`git init --bare` + `git push scratch dev:main`).
- `AKIAIOSFODNN7EXAMPLE` (la key de ejemplo de AWS) está en el **allowlist** de gitleaks: para pruebas usar seudos-secretos con formato real (ej. `github-pat`).

### 7. Protección de `main` (client-side + server-side)
**Qué se hizo:**
- Hooks locales: `block-commit-on-main` (stage `pre-commit`) y `block-push-to-main` (stage `pre-push`, lee `PRE_COMMIT_REMOTE_BRANCH`).
- Mensajes didácticos: ambos sugieren "crea rama y abre PR".
- Server-side: ruleset de GitHub para `main` (PR obligatorio, sin force-push, sin delete) creado con `gh api`. Es la única capa que **no** se salta con `--no-verify`.

**Importancia:**
- El CI (`ci.yml`) corre en PRs y en push a `main` → cualquier bypass de hooks locales (`--no-verify`, commits desde la UI) termina atrapado.

### 8. `commitlint` — Conventional Commits obligatorios
**Qué se hizo:**
- `commitlint.config.mjs` (`@commitlint/config-conventional`) ejecutado en stage `commit-msg` vía hook local pre-commit (`language: node`, sin `package.json`/`node_modules` en el repo).

**Importancia:**
- No es solo orden estético: **alimenta el versionado automático** (`feat`→minor, `fix`→patch, `!`→major) del release-please.

### 9. `release-please` — releases automáticos
**Qué se hizo:**
- `.github/workflows/release-please.yml` (action `googleapis/release-please-action@v4`, modo manifest) + `release-please-config.json` (`release-type: python` → hace bump de `pyproject.toml`) + `.release-please-manifest.json` (`0.1.0`).
- Smoke test que verifica la sincronía manifest ↔ pyproject.

**Decisión: `uv.lock` NO se versiona** (a diferencia del proyecto anterior):
- Consecuencia: el job `sync-lockfile` del workflow original quedó **desactivado** (comentado en el propio workflow) porque sin `uv.lock` trackeado no tendría efecto.
- Si algún día se versiona, reactivarlo con los fixes ya anotados: condicionar a `releases_created == 'true'` (no `if: always()`), quitar `UV_EXTRA_INDEX_URL`/`SAFETY_INDEX_URL` (secret inexistente en este repo), y bump de actions (`checkout@v5`, `setup-uv@v8`).
- Uso de `GITHUB_TOKEN` (limitación conocida): recursos creados con él **no disparan** otros workflows → el CI no corre sobre los Release PRs del bot. Suficiente para este lab; si se necesita, usar un PAT como `token`.

### 10. CI + smoke tests base
**Qué se hizo:**
- `.github/workflows/ci.yml`: checkout → `setup-uv` → `uv sync` → `pre-commit run --all-files` → `uv run pytest` (concurrency-group para cancelar runs obsoletos).
- `tests/test_smoke.py`: config cargable, manifest↔pyproject sincrónicos, presencia de archivos shift-left. Se agregó `pythonpath = ["."]` a `[tool.pytest.ini_options]` para que los tests importen módulos raíz.

### Pendientes
- `bandit` (SAST): activarlo en CI con supresiones `# nosec` **marcando** las vulnerabilidades intencionales del lab (SQLi/XSS/IDOR/uploads). No en pre-commit local, porque gritaría en cada commit.
- Red de seguridad para releases en cambios de `config.json` de release-please (revisión manual en PR).
- `agents.md` + git-flow (discusión futura): reglas para agentes de IA y flujo de ramas — postergado a decisión explícita.
