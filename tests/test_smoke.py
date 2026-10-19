# Smoke tests base del laboratorio.
# No prueban vulnerabilidades (eso es tema del lab), solo sostienen el CI:
# verifican que los modulos cargan y que la configuracion es coherente.
import re
from pathlib import Path

import pytest


def test_config_registrada_como_default():
    from config import config

    assert "default" in config
    assert "testing" in config


def test_config_testing_usa_sqlite_en_memoria():
    from config import TestingConfig

    assert TestingConfig.SQLALCHEMY_DATABASE_URI == "sqlite:///:memory:"


def test_version_manifest_coincide_con_pyproject():
    """release-please requiere que .release-please-manifest.json y
    pyproject.toml declaren la misma version."""
    manifest = Path(".release-please-manifest.json")
    pyproject = Path("pyproject.toml")
    assert manifest.exists(), "falta .release-please-manifest.json"
    assert pyproject.exists(), "falta pyproject.toml"

    import json

    version_manifest = json.loads(manifest.read_text())["."]
    match = re.search(r'^version = "([^"]+)"', pyproject.read_text(), re.M)
    assert match, "pyproject.toml no declara version estatica"
    assert manifest.exists() and match.group(1) == version_manifest


@pytest.mark.parametrize(
    "filename",
    [
        ".github/workflows/ci.yml",
        ".github/workflows/release-please.yml",
        ".pre-commit-config.yaml",
    ],
)
def test_archivos_shift_left_presentes(filename):
    assert Path(filename).exists(), f"falta {filename}"
