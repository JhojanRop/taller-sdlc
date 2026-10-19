# AGENTS.md

Guía operativa para agentes de código. Complementa el `README.md` (humano) y
la `BITACORA.md` (registro de decisiones). Última actualización: 2026-10-19.

## Qué es este proyecto

**Laboratorio intencionalmente vulnerable** (Flask + SQLite) para enseñar
S-SDLC. Contiene **4 vulnerabilidades a propósito**, documentadas en los
comentarios del código y en `BITACORA.md`: SQLi, XSS almacenado, IDOR y
carga de archivos sin restricción.

> ⛔ **NO arregles las vulnerabilidades intencionales** salvo que la
> tarea lo pida explícitamente (la tarea dirá qué alumno debe explorar).
> Un "refactor de seguridad" no solicitado destruye el material del curso.

## Comandos (ejecutables)

```bash
uv sync                                   # dependencias (uv; no uses pip)
uv run pytest -q                          # tests (6 smoke tests)
uv run ruff check --fix                   # lint (reutiliza config del proyecto)
uv run ruff format                        # formato
uv run pre-commit run --all-files         # todos los gates
uv run python database.py && uv run python app.py   # arrancar el lab
```

## Entorno

- Gestor de dependencias: **uv** (no pip). Lockfile: `uv.lock` está
  **deliberadamente sin trackear** (decisión en `BITACORA`); no lo fuerces a
  commitear.
- Python de desarrollo: `3.13` (`.python-version`). Piso soportado:
  `>=3.11` en `pyproject.toml` — **no lo cambies** (decisión documentada).

## Git workflow (es el flujo aprobado del repo)

- **`main`**: trunk versionado (rol de branch `release` incluido).
  Nunca se commitea ni push directo; **solo via PR** (el ruleset de GitHub
  lo bloquea de hecho).
- **`dev`**: integración de desarrollo.
- **Ramas de trabajo**: `feat/*`, `fix/*`, `docs/*`, `chore/*`, `ci/*`,
  `refactor/*`, `test/*`, `perf/*` — desde `dev`. Un hook local lo
  verifica en cada commit.
- **Features → dev**: merge **local** sin PR, siempre con `--no-ff`
  (`git merge --no-ff feat/x`) para que quede registro del origen. Borrar
  la rama después del merge.
- **Cambios pequeños de un solo commit**: van **directo en `dev`**, sin
  rama ni merge `--no-ff` (solo si tocan más de un asunto o son series de
  commits, usa rama con naming valido).
- **`main` / pushes / PRs**: **solo bajo instrucción explícita del
  usuario**. Los agentes NO hacen `push`, no abren PRs ni los mergear;
  dejan el trabajo commiteado en `dev` local e informan qué falta
  ejecutar. El push directo a `main` además lo bloquean los hooks y el
  ruleset.
- **dev → main**: PR (dispara release-please). El título y body del PR
  deben explicar qué versiones generará.
- **Hotfix/fix**: rama `fix/*` desde `main`, PR a `main`, y **sync
  inmediato a `dev`** (`git merge origin/main`). No existe `hotfix/*`: un
  hotfix usa el mismo naming `fix/*` y nunca "es urgente" como para
  saltarse el PR.
- **Jamás `--no-verify`** en un commit/push.

## Conventional Commits

Obligatorio (lo valida `commitlint`). Tipos válidos: `feat`, `fix`, `docs`,
`chore`, `ci`, `refactor`, `test`, `perf`, `build`, `revert`. Los `feat:`
disparan bump minor automático; los `fix:`, patch.

## Releases

`release-please` genera los tags y el `CHANGELOG.md` y ajusta **la versión
en `pyproject.toml`** y `.release-please-manifest.json`. **No edites a
mano** esos dos valores: se manejan via Release PRs del bot. Hay un smoke
test que verifica la sincronía (`test_version_manifest_coincide_con_pyproject`).

## Reglas duras

- *Nunca* commitear secrets reales: `gitleaks` bloquea en staging. Para
  testear el bloqueo usa seudósticos con formato real (ej. `github-pat`
  tipo `ghp_`), nunca credenciales de verdad.
- `__pycache__/`, `*.db`, `uploads/`, `.env*` están ignorados y contienen
  datos del lab: no fuerces su commit.
- Si cambias convenciones, actualiza este `AGENTS.md` **en el mismo PR**
  que la introduce.
