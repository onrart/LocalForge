"""
LocalForge — Template Manager
Şablon iskeletini projeye kopyalar, placeholder'ları doldurur.
"""

import json
import re
import shutil
from pathlib import Path


REGISTRY_PATH = Path(__file__).parent.parent / "templates" / "_registry.json"


def load_registry() -> dict:
    """_registry.json'ı okur."""
    if REGISTRY_PATH.exists():
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return {}


def detect_template(stack: str) -> str:
    """
    Stack string'inden şablon adını tespit eder.
    Eşleşme yoksa boş string döner.
    """
    registry = load_registry()
    stack_lower = stack.lower()
    for template_name, info in registry.items():
        if any(kw in stack_lower for kw in info["keywords"]):
            return template_name
    return ""


def get_template_info(template_name: str) -> dict:
    """Şablon bilgisini döner."""
    registry = load_registry()
    return registry.get(template_name, {})


def apply_template(
    template_name: str,
    project_path: str | Path,
    placeholders: dict,
) -> list[str]:
    """
    Şablonu proje klasörüne kopyalar ve placeholder'ları doldurur.

    placeholders örneği:
    {
        "project_name": "TaskManager",
        "project_name_kebab": "task-manager",
        "project_description": "Görev yönetim uygulaması",
    }

    Returns: Kopyalanan dosyaların göreli yol listesi
    """
    registry = load_registry()
    if template_name not in registry:
        return []

    template_info = registry[template_name]
    templates_base = Path(__file__).parent.parent / "templates"
    template_dir = templates_base / template_name
    project_path = Path(project_path)

    if not template_dir.exists():
        return []

    copied = []

    for src_file in template_dir.rglob("*"):
        if src_file.is_file():
            rel = src_file.relative_to(template_dir)
            dst = project_path / rel

            # Hedef zaten varsa atla (kullanıcının dosyasını ezme)
            if dst.exists():
                continue

            dst.parent.mkdir(parents=True, exist_ok=True)

            # İçeriği oku ve placeholder'ları doldur
            try:
                content = src_file.read_text(encoding="utf-8")
                content = _fill_placeholders(content, placeholders)
                dst.write_text(content, encoding="utf-8")
                copied.append(str(rel))
            except UnicodeDecodeError:
                # Binary dosyaysa direkt kopyala
                shutil.copy2(src_file, dst)
                copied.append(str(rel))

    return copied


def _fill_placeholders(content: str, placeholders: dict) -> str:
    """
    İçerikteki {placeholder} ifadelerini doldurur.
    Bilinmeyen placeholder'ları olduğu gibi bırakır.
    """
    for key, value in placeholders.items():
        content = content.replace(f"{{{key}}}", value)
    return content


def build_placeholders(project_name: str, project_description: str = "") -> dict:
    """
    Proje adından tüm placeholder varyantlarını üretir.
    """
    # kebab-case: "Task Manager" → "task-manager"
    kebab = re.sub(r"[^a-z0-9]+", "-", project_name.lower()).strip("-")

    # snake_case: "Task Manager" → "task_manager"
    snake = re.sub(r"[^a-z0-9]+", "_", project_name.lower()).strip("_")

    # PascalCase: "task manager" → "TaskManager"
    pascal = "".join(w.capitalize() for w in project_name.split())

    return {
        "project_name": project_name,
        "project_name_kebab": kebab,
        "project_name_snake": snake,
        "project_name_pascal": pascal,
        "project_description": project_description or f"{project_name} uygulaması",
    }


if __name__ == "__main__":
    import tempfile

    # Test
    with tempfile.TemporaryDirectory() as tmp:
        placeholders = build_placeholders("Task Manager API", "Görev yönetim REST API")
        copied = apply_template("fastapi", tmp, placeholders)
        print(f"Kopyalanan dosyalar ({len(copied)}):")
        for f in copied:
            print(f"  {f}")

        # İçerik kontrolü
        main_py = Path(tmp) / "main.py"
        if main_py.exists():
            print(f"\nmain.py ilk satır: {main_py.read_text().splitlines()[0]}")
