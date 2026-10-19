# laboratorio-seguridad

## Ejecución

```bash
uv sync
uv run python database.py
uv run python app.py
```

Servidor en http://127.0.0.1:5000

## Versiones de Python

- **Piso soportado**: `>=3.11` (`pyproject.toml` decision documentada en `BITACORA.md`).
- **Version de desarrollo**: `3.13` (`.python-version`, la que usa `uv` para crear el `.venv`).
- CI instala Python leyendo `.python-version`.

## Workflow y convenciones (Shift-Left)

### Commits — Conventional Commits (obligatorio)
Validado por `commitlint` en el hook `commit-msg`. Tipos permitidos:
`build`, `chore`, `ci`, `docs`, `feat`, `fix`, `perf`, `refactor`, `revert`, `style`, `test`.
Los tipos alimentan el versionado automatico (`feat` → minor, `fix` → patch, `!`/breaking → major).

### Ramas
- **`main`**: protegida. **No se commitea ni se pushea directo** (hooks locales + ruleset de GitHub) — los cambios llegan solo via **PR**.
- **`dev`**: rama base de desarrollo.
- `feat/*`, `fix/*`, `docs/*`, `chore/*`, etc., ramas cortas desde `dev`.

### Hooks de pre-commit
Config en `.pre-commit-config.yaml`. Activarlos al clonar:

```bash
uv sync
uv run pre-commit install --install-hooks
uv run pre-commit install --hook-type pre-push --hook-type commit-msg
```

| Gate | Que valida |
|--|--|
| `trailing-whitespace`, `end-of-file-fixer`, `check-toml`, `check-merge-conflict`, `debug-statements` | Higiene del repo |
| `detect-private-key` | claves privadas en staging |
| `gitleaks` | secrets en el diff *antes* de commitear |
| `ruff check --fix`, `ruff format` | Lint + estilo (misma config del proyecto) |
| `block-commit-on-main` / `block-push-to-main` | protege `main` (PR obligatorio) |
| `commitlint` | Conventional Commits |

> Nunca uses `--no-verify`: el CI (`.github/workflows/ci.yml`) ejecuta
> `pre-commit run --all-files` + `pytest` y fallara el PR.

### Releases automaticos (release-please)
Al mergear PRs que aporten commits convencionales a `main`, release-please
mantiene un **Release PR** con bump de version (`pyproject.toml`) y
`CHANGELOG.md`. Al mergear ese PR se crea el tag `vX.Y.Z` y el GitHub Release.

- Config: `release-please-config.json` (release-type `python`)
- Version actual: `.release-please-manifest.json` (debe coincidir con `pyproject.toml` — hay un smoke test que lo verifica)

### Decisiones (resumen, detalle en `BITACORA.md`)
- `uv.lock` **no** se versiona en este repo.
- `bandit` (SAST) **pendiente**: los scans marcarian las vulnerabilidades
  intencionales del lab (SQLi/XSS/IDOR/uploads por diseno didactico).
