"""
LocalForge — Context Manager
.agent/ klasöründeki MD dosyalarını yönetir.
Her LLM çağrısı için token-safe bağlam hazırlar.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

# MD Dosya Şablonları
_TEMPLATES = {
    "PROJECT.md": """\
# Proje: {name}

## Teknoloji Stack
{stack}

## Amaç
{goal}

## Platform
{platform}
""",
    "REQUIREMENTS.md": """\
# Gereksinimler

## Proje Açıklaması
{description}

## Özellikler
{features}

## Veritabanı
{database}

## Kimlik Doğrulama
{auth}

## Ek Notlar
{notes}
""",
    "ARCHITECTURE.md": """\
# Mimari

_(Planlama ajanı tarafından doldurulacak)_
""",
    "TASKS.md": """\
# Görev Listesi

_(Planlama ajanı tarafından doldurulacak)_
""",
    "PROGRESS.md": """\
# Tamamlanan İşler

_(Her görev tamamlandığında güncellenir)_
""",
    "CURRENT_TASK.md": """\
# Şu Anki Görev

_(Her görev başlamadan önce güncellenir)_
""",
    "MEMORY.md": """\
# Kritik Kararlar ve Notlar

## Mimari Kararlar
_(Ajan kararlarını buraya kaydeder)_

## Dosya Konvansiyonları
_(Kullanılan naming pattern'leri)_

## Kullanıcı Manuel Değişiklikleri
_(UI'dan yapılan manuel düzenlemeler)_

## Dikkat: Bilinen Durumlar
_(Önemli uyarılar)_
""",
}


class ContextManager:
    def __init__(self, project_path: str | Path):
        self.project_path = Path(project_path)
        self.agent_dir = self.project_path / ".agent"
        self.checkpoints_dir = self.agent_dir / "checkpoints"

    # ─────────────────────────────────────────
    # Başlatma
    # ─────────────────────────────────────────

    def init(self, project_info: dict):
        """
        .agent/ klasörünü ve MD dosyalarını oluşturur.
        project_info: requirements_collector'dan gelen dict
        """
        self.agent_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)

        # PROJECT.md
        self._write(
            "PROJECT.md",
            _TEMPLATES["PROJECT.md"].format(
                name=project_info.get("name", ""),
                stack=project_info.get("stack", ""),
                goal=project_info.get("goal", ""),
                platform=project_info.get("platform", ""),
            ),
        )

        # REQUIREMENTS.md
        features = "\n".join(f"- [ ] {f}" for f in project_info.get("features", []))
        self._write(
            "REQUIREMENTS.md",
            _TEMPLATES["REQUIREMENTS.md"].format(
                description=project_info.get("description", ""),
                features=features,
                database=project_info.get("database", "Yok"),
                auth=project_info.get("auth", "Yok"),
                notes=project_info.get("notes", "Yok"),
            ),
        )

        # Geri kalan dosyalar (boş şablonlar)
        for filename in [
            "ARCHITECTURE.md",
            "TASKS.md",
            "PROGRESS.md",
            "CURRENT_TASK.md",
            "MEMORY.md",
        ]:
            path = self.agent_dir / filename
            if not path.exists():
                self._write(filename, _TEMPLATES[filename])

    # ─────────────────────────────────────────
    # Bağlam Oluşturma
    # ─────────────────────────────────────────

    def build_context(self, role: str = "coder") -> str:
        """
        Token-safe bağlam string'i oluşturur.
        role: "planner" | "coder" | "editor"

        Yaklaşık token bütçesi:
          PROJECT.md       ~200
          CURRENT_TASK.md  ~300
          MEMORY.md        ~400
          REQUIREMENTS.md  ~300 (sadece planlayıcı için)
        """
        parts = []

        project = self._read("PROJECT.md")
        if project:
            parts.append(f"## PROJE BİLGİSİ\n{project}")

        if role == "planner":
            req = self._read("REQUIREMENTS.md")
            if req:
                parts.append(f"## GEREKSİNİMLER\n{req}")

        current = self._read("CURRENT_TASK.md")
        if current:
            parts.append(f"## ŞU ANKİ GÖREV\n{current}")

        memory = self._read("MEMORY.md")
        if memory:
            parts.append(f"## KRİTİK KARARLAR (MEMORY)\n{memory}")

        if role == "coder":
            progress = self._read("PROGRESS.md")
            if progress:
                parts.append(f"## TAMAMLANAN İŞLER (ÖZET)\n{progress}")

        return "\n\n---\n\n".join(parts)

    def build_file_context(self, file_path: str, max_lines: int = 100) -> str:
        """
        Mevcut bir dosyayı bağlama ekler (max_lines ile sınırlı).
        Editor ajanı için kullanılır.
        """
        path = self.project_path / file_path
        if not path.exists():
            return ""
        lines = path.read_text(encoding="utf-8").splitlines()
        truncated = lines[:max_lines]
        content = "\n".join(truncated)
        note = (
            f"\n... (toplam {len(lines)} satır, ilk {max_lines} gösteriliyor)"
            if len(lines) > max_lines
            else ""
        )
        return f"## MEVCUT DOSYA: {file_path}\n```\n{content}{note}\n```"

    # ─────────────────────────────────────────
    # Görev Yönetimi
    # ─────────────────────────────────────────

    def get_pending_tasks(self) -> list[str]:
        """TASKS.md'den tamamlanmamış görevleri döner."""
        content = self._read("TASKS.md")
        tasks = []
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("- [ ]"):
                task = line[5:].strip().split("#")[0].strip()
                tasks.append(task)
        return tasks

    def get_all_tasks(self) -> list[dict]:
        """Tüm görevleri durum bilgisiyle döner."""
        content = self._read("TASKS.md")
        tasks = []
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("- [x]"):
                name = line[5:].strip().split("#")[0].strip()
                tasks.append({"name": name, "done": True})
            elif line.startswith("- [ ]"):
                name = line[5:].strip().split("#")[0].strip()
                tasks.append({"name": name, "done": False})
        return tasks

    def mark_task_done(self, task_name: str):
        """TASKS.md'de görevi tamamlandı olarak işaretler."""
        content = self._read("TASKS.md")
        updated = content.replace(f"- [ ] {task_name}", f"- [x] {task_name}")
        self._write("TASKS.md", updated)

    def set_current_task(self, task_name: str, details: str):
        """CURRENT_TASK.md'yi günceller."""
        content = f"# Şu Anki Görev: {task_name}\n\n{details}\n"
        self._write("CURRENT_TASK.md", content)

    def append_to_memory(self, section: str, note: str):
        """
        MEMORY.md'ye belirli bir bölüme not ekler.
        section: "Mimari Kararlar" | "Kullanıcı Manuel Değişiklikleri" | vb.
        """
        content = self._read("MEMORY.md")
        timestamp = datetime.now().strftime("%H:%M")
        entry = f"- [{timestamp}] {note}"

        if f"## {section}" in content:
            content = content.replace(f"## {section}", f"## {section}\n{entry}")
        else:
            content += f"\n## {section}\n{entry}\n"

        self._write("MEMORY.md", content)

    def append_to_progress(self, task_name: str, files_created: list[str]):
        """PROGRESS.md'ye tamamlanan görevi ekler."""
        timestamp = datetime.now().strftime("%d.%m %H:%M")
        files_str = ", ".join(files_created) if files_created else "—"
        entry = f"\n### ✅ {task_name} ({timestamp})\n- Dosyalar: {files_str}\n"
        content = self._read("PROGRESS.md")
        self._write("PROGRESS.md", content + entry)

    def write_tasks(self, tasks_md: str):
        """Planlama ajanının ürettiği TASKS.md içeriğini yazar."""
        self._write("TASKS.md", tasks_md)

    def write_architecture(self, arch_md: str):
        """Planlama ajanının ürettiği ARCHITECTURE.md içeriğini yazar."""
        self._write("ARCHITECTURE.md", arch_md)

    def update_requirements(self, content: str):
        """Kullanıcının UI'dan düzenlediği REQUIREMENTS.md'yi günceller."""
        self._write("REQUIREMENTS.md", content)

    # ─────────────────────────────────────────
    # Manuel Değişiklik Takibi
    # ─────────────────────────────────────────

    def record_manual_edit(self, file_path: str, diff_summary: str):
        """
        Kullanıcı UI'dan dosya düzenlediğinde MEMORY.md'ye not düşer.
        Böylece LLM bir sonraki görevde bu dosyayı silip üzerine yazmaz.
        """
        note = f"`{file_path}` kullanıcı tarafından manuel düzenlendi — {diff_summary}"
        self.append_to_memory("Kullanıcı Manuel Değişiklikleri", note)

    def get_manually_edited_files(self) -> list[str]:
        """MEMORY.md'den manuel düzenlenmiş dosyaların listesini çeker."""
        content = self._read("MEMORY.md")
        files = []
        for line in content.splitlines():
            if "manuel düzenlendi" in line and "`" in line:
                # `dosya/yolu` formatından çek
                parts = line.split("`")
                if len(parts) >= 2:
                    files.append(parts[1])
        return files

    # ─────────────────────────────────────────
    # Checkpoint
    # ─────────────────────────────────────────

    def save_checkpoint(self, task_name: str, files: list[str]) -> Path:
        """
        Görev sonrası snapshot alır.
        files: proje içindeki göreli dosya yolları listesi
        """
        import shutil

        checkpoint_dir = self.checkpoints_dir / task_name
        files_dir = checkpoint_dir / "files"
        files_dir.mkdir(parents=True, exist_ok=True)

        # Dosyaları kopyala
        copied = []
        for rel_path in files:
            src = self.project_path / rel_path
            if src.exists():
                dst = files_dir / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                copied.append(rel_path)

        # Metadata
        meta = {
            "task": task_name,
            "timestamp": datetime.now().isoformat(),
            "files_created": copied,
        }
        (checkpoint_dir / "snapshot.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return checkpoint_dir

    def get_checkpoints(self) -> list[dict]:
        """Tüm checkpoint'leri listeler."""
        checkpoints = []
        if not self.checkpoints_dir.exists():
            return []
        for cp_dir in sorted(self.checkpoints_dir.iterdir()):
            meta_file = cp_dir / "snapshot.json"
            if meta_file.exists():
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                checkpoints.append(meta)
        return checkpoints

    def restore_checkpoint(self, task_name: str):
        """Belirtilen checkpoint'e geri döner (dosyaları geri yazar)."""
        import shutil

        checkpoint_dir = self.checkpoints_dir / task_name
        files_dir = checkpoint_dir / "files"
        if not files_dir.exists():
            raise FileNotFoundError(f"Checkpoint bulunamadı: {task_name}")

        for src in files_dir.rglob("*"):
            if src.is_file():
                rel = src.relative_to(files_dir)
                dst = self.project_path / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

    # ─────────────────────────────────────────
    # IO Helpers
    # ─────────────────────────────────────────

    def _read(self, filename: str) -> str:
        path = self.agent_dir / filename
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def _write(self, filename: str, content: str):
        path = self.agent_dir / filename
        path.write_text(content, encoding="utf-8")

    def read_file(self, filename: str) -> str:
        """Genel dosya okuma (agent_dir dışı için)."""
        return self._read(filename)
