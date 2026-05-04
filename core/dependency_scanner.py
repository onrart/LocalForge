"""
LocalForge — Dependency Scanner
Üretilen Python kodundaki import'ları tarar.
Stdlib dışı paketleri tespit edip requirements.txt'e ekler.
"""

import ast
import sys
import re
from pathlib import Path

# Python stdlib modül listesi (3.10+)
STDLIB_MODULES = sys.stdlib_module_names

# Paket adı farklı olan modüller: import adı → pip adı
IMPORT_TO_PACKAGE = {
    "PIL": "Pillow",
    "cv2": "opencv-python",
    "sklearn": "scikit-learn",
    "bs4": "beautifulsoup4",
    "dotenv": "python-dotenv",
    "jose": "python-jose",
    "yaml": "PyYAML",
    "psycopg2": "psycopg2-binary",
    "pymysql": "PyMySQL",
    "dateutil": "python-dateutil",
    "serial": "pyserial",
    "usb": "pyusb",
    "wx": "wxPython",
}

# Yerel modüller — her zaman görmezden gelinir
IGNORE_MODULES = {
    # LocalForge iç modülleri
    "core",
    "agents",
    "ui",
    "prompts",
    "templates",
    "localforge",
    # Proje içi yaygın klasör/modül isimleri
    "src",
    "app",
    "config",
    "database",
    "models",
    "schemas",
    "routes",
    "router",
    "routers",
    "services",
    "utils",
    "helpers",
    "middleware",
    "auth",
    "api",
    "tests",
    "test",
    "migrations",
    "static",
    "templates",
    "views",
    "controllers",
    "handlers",
    "book",
    "user",
    "users",
    "product",
    "order",
    "payment",
    "main",
    "conftest",
    "setup",
    "manage",
    "__future__",
    "__init__",
}


def scan_python_file(content: str) -> set[str]:
    """
    Tek bir Python dosyasındaki import'ları ast ile tarar.
    Stdlib ve yerel modülleri filtreler, üçüncü parti paket adlarını döner.
    """
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return set()

    imports = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                imports.add(root)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root = node.module.split(".")[0]
                imports.add(root)

    return _filter_third_party(imports)


def scan_directory(project_path: str | Path) -> set[str]:
    """
    Proje klasöründeki tüm .py dosyalarını tarar.
    Tüm üçüncü parti bağımlılıkları birleştirir.
    """
    project_path = Path(project_path)
    all_deps = set()

    for py_file in project_path.rglob("*.py"):
        if ".agent" in py_file.parts or "__pycache__" in py_file.parts:
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
            deps = scan_python_file(content)
            all_deps.update(deps)
        except Exception:
            continue

    return all_deps


def _filter_third_party(imports: set[str]) -> set[str]:
    """Stdlib ve yerel modülleri filtreler, sadece üçüncü parti döner."""
    result = set()
    for mod in imports:
        if not mod:
            continue
        if mod in STDLIB_MODULES:
            continue
        if mod in IGNORE_MODULES:
            continue
        if mod.startswith("_"):
            continue
        pip_name = IMPORT_TO_PACKAGE.get(mod, mod)
        result.add(pip_name)
    return result


def read_requirements(req_path: str | Path) -> dict[str, str]:
    """
    requirements.txt'i okur.
    Returns: {paket_adı_lower: orijinal_satır}
    """
    req_path = Path(req_path)
    if not req_path.exists():
        return {}

    packages = {}
    for line in req_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name = re.split(r"[>=<!~\[]", line)[0].strip().lower()
        packages[name] = line

    return packages


def update_requirements(
    req_path: str | Path,
    new_packages: set[str],
) -> list[str]:
    """
    Eksik paketleri requirements.txt'e ekler.
    Returns: Eklenen paketlerin listesi
    """
    req_path = Path(req_path)
    existing = read_requirements(req_path)
    added = []

    for pkg in sorted(new_packages):
        if pkg.lower() not in existing:
            added.append(pkg)

    if not added:
        return []

    current = req_path.read_text(encoding="utf-8") if req_path.exists() else ""
    if current and not current.endswith("\n"):
        current += "\n"

    updated = current + "\n".join(added) + "\n"
    req_path.write_text(updated, encoding="utf-8")

    return added


def scan_and_update(content: str, project_path: str | Path) -> list[str]:
    """
    Tek dosya için tara + requirements.txt güncelle.
    Coder agent her dosya ürettikten sonra bunu çağırır.
    Returns: Eklenen paketler listesi
    """
    project_path = Path(project_path)
    req_path = project_path / "requirements.txt"

    detected = scan_python_file(content)
    if not detected:
        return []

    return update_requirements(req_path, detected)


if __name__ == "__main__":
    sample = """
import os
import fastapi
from sqlalchemy import Column
from pydantic import BaseModel
import requests
from PIL import Image
from core.utils import something
"""
    deps = scan_python_file(sample)
    print("Tespit edilen paketler:", deps)
