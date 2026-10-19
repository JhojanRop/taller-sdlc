
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

### 11. Estreno end-to-end y ajustes del primer ciclo
**Acontecimiento:** primer ciclo completo dev → PR → CI → merge → `v0.2.0` → fix (release `v0.2.1`). Aprendizajes aplicados en caliente:
- `astral-sh/setup-uv` no resolvió como action (infra del runner) → CI instala `uv` con el instalador oficial (`curl astral.sh/uv/install.sh`) y ejecuta pre-commit desde el propio venv (`uv run pre-commit`).
- El hook `block-commit-on-main` abortaba el CI que corre sobre `main` → skip cuando `GITHUB_ACTIONS` está seteado (el ruleset server-side es la autoridad en ese entorno).
- El repo necesitaba **"Allow GitHub Actions to create and approve pull requests"** para que release-please abriera su PR (el PATCH de la API devolvía 404; se activó manual por UI).
- Tras el merge de un Release PR, `dev` queda con SHAs viejos (rebase del bot) → resolver con `git rebase origin/main` (los patches duplicados se descartan solos).
- Los PR-triggered runs sobre ramas `release-please--**` fallaban sin log; el job de CI ahora se excluye para ese head (`!startsWith(github.head_ref, 'release-please--')`) — el push de esos PRs a `main` valida el contenido igual.
### 12. Git-flow reducido + `AGENTS.md`
**Qué se hizo:**
- Diseño del flujo de ramas y documentación operativa para agentes de código:
  - `main` = trunk versionado (asume el rol de `release/*` del git-flow clásico): PR obligatorio, nunca commits directos.
  - `dev` = integración de desarrollo (local).
  - Ramas `feat/*|fix/*|docs/*|chore/*|ci/*|refactor/*|test/*|perf/*` → integración **local** a `dev` con **`git merge --no-ff`** (conserva el merge commit como registro de origen), se eliminan después.
  - `dev → main` via PR = el momento "release" (dispara release-please). Sin rama `release/*`.
  - Hotfix: `fix/*` nace desde `main`, PR a `main` y **sync inmediato** a `dev` (el merge `origin/main` evita divergencia). Sin `hotfix/*`.
- `AGENTS.md` en raíz: guía operativa para agentes (formato agents.md del estándar abierto, ~60k repos y soportado nativamente por OpenCode, Codex, Cursor, Gemini CLI, etc.). Contenido basado en las lecciones de los análisis de ~2,500 AGENTS.md (GitHub) y el spec: comandos ejecutables primero, límites explícitos ("no arregles las 4 vulnerabilidades del lab"), invariantes que fallan silenciosamente, referencia a BITACORA como fuente de verdad de decisiones. Sin reglas redundantes con la maquinaria (hooks) ni rutas volátiles.
- Enforcement adicional: hook `check-branch-naming` (se excluye en CI; `main`/`dev`/ramas del bot exentas).

**Importancia:**
- **`--no-ff` vs `--ff`**: el merge no-rápido crea un merge commit que dice de qué rama vino el cambio (la "opción de merge" que registra el origen); con ff el historial queda plano y sin trazabilidad de branch.
- **Hotfix desde `main`** y no desde `dev`: si `dev` tiene features sin liberar, un fix desde ahí saldría acoplado a trabajo a medio cocinar; nacer de `main` lo aísla y el sync inmediato a `dev` evita divergencia en el próximo release.
- **Compliance de agentes**: la investigación mostró que las instrucciones en Markdown logran 25-40% de cumplimiento en agentes, pero los hooks ~95% → lo crítico se reforza con hooks (naming) y lo contextual vive en `AGENTS.md`.
- **Limitación conocida**: commitlint ignora por defecto los mensajes `Merge ...` (config-conventional), así que los merge commits del `--no-ff` no requieren tipado convencional. Verificado empíricamente en el primer merge `--no-ff` real del proyecto.

### 13. Flujo establecido (referencia rápida de ops)
- Para desarrollar: `git switch dev && git switch -c feat/<algo>` → commits → `git checkout dev && git merge --no-ff feat/<algo>` → `git branch -d feat/<algo>` → `git push origin dev`.
- Para liberar: PR `dev→main` → CI verde → merge (rebase recomendado para conservar mensajes convencionales) → release-please abre `chore(main): release vX.Y.[Z]` → mergear ese PR → tag + release automáticos → `git merge origin/main` en `dev` local.

### Pendientes
- `bandit` (SAST): activarlo en CI con supresiones `# nosec` **marcando** las vulnerabilidades intencionales del lab (SQLi/XSS/IDOR/uploads). No en pre-commit local, porque gritaría en cada commit.
- Red de seguridad para releases en cambios de `config.json` de release-please (revisión manual en PR).
