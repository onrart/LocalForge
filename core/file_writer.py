"""
LocalForge — File Writer
LLM çıktısından kod bloklarını ayıklar, diske yazar.
Diff üretir, UI'da gösterim için kullanılır.
"""

import re
import difflib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParsedFile:
    path: str  # Örn: "src/auth/router.py"
    content: str  # Dosya içeriği
    language: str  # "python" | "javascript" | vb.


@dataclass
class WriteResult:
    path: str
    success: bool
    was_new: bool  # Yeni mi oluşturuldu, mevcut mu güncellendi
    diff: str = ""  # Unified diff (UI'da gösterim için)
    error: str = ""


@dataclass
class WriteSession:
    files_written: list[WriteResult] = field(default_factory=list)
    files_skipped: list[str] = field(default_factory=list)

    @property
    def success_count(self) -> int:
        return sum(1 for f in self.files_written if f.success)

    @property
    def all_paths(self) -> list[str]:
        return [f.path for f in self.files_written if f.success]


# ─────────────────────────────────────────
# LLM Çıktısı Parse
# ─────────────────────────────────────────

# LLM'in ürettiği format:
# # Dosya: src/auth/router.py
# ```python
# ... kod ...
# ```
_FILE_BLOCK_PATTERN = re.compile(
    r"#\s*Dosya:\s*(.+?)\n```(?:\w+)?\n(.*?)```", re.DOTALL | re.IGNORECASE
)

# Alternatif format (bazı modeller farklı üretebilir):
# ```python
# # src/auth/router.py
# ... kod ...
# ```
_ALT_BLOCK_PATTERN = re.compile(
    r"```(\w+)?\n#\s*([^\n]+\.(?:py|js|ts|jsx|tsx|json|md|txt|yaml|yml|html|css))\n(.*?)```",
    re.DOTALL,
)


def parse_llm_output(response: str) -> list[ParsedFile]:
    """
    LLM yanıtından dosya bloklarını ayıklar.
    İki farklı formatı destekler.
    """
    files = []
    seen_paths = set()

    # Birincil format: # Dosya: path\n```lang\n...\n```
    for match in _FILE_BLOCK_PATTERN.finditer(response):
        path = match.group(1).strip()
        content = match.group(2).rstrip()
        lang = _detect_language(path)

        if path not in seen_paths:
            files.append(ParsedFile(path=path, content=content, language=lang))
            seen_paths.add(path)

    # Alternatif format (birincil bulamazsa)
    if not files:
        for match in _ALT_BLOCK_PATTERN.finditer(response):
            lang_hint = match.group(1) or ""
            path = match.group(2).strip()
            content = match.group(3).rstrip()
            lang = lang_hint or _detect_language(path)

            if path not in seen_paths:
                files.append(ParsedFile(path=path, content=content, language=lang))
                seen_paths.add(path)

    return files


def _detect_language(file_path: str) -> str:
    """Dosya uzantısından dil adını döner."""
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "javascript",
        ".tsx": "typescript",
        ".json": "json",
        ".html": "html",
        ".css": "css",
        ".md": "markdown",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".sh": "bash",
        ".txt": "text",
    }
    ext = Path(file_path).suffix.lower()
    return ext_map.get(ext, "text")


# ─────────────────────────────────────────
# Dosya Yazma
# ─────────────────────────────────────────


def write_file(
    parsed_file: ParsedFile,
    project_path: str | Path,
    manually_edited_files: list[str] | None = None,
) -> WriteResult:
    """
    Tek bir dosyayı diske yazar.
    Manuel düzenlenmiş dosyaları atlar.
    Diff üretir.
    """
    project_path = Path(project_path)
    manually_edited_files = manually_edited_files or []

    # Manuel düzenleme koruması
    if parsed_file.path in manually_edited_files:
        return WriteResult(
            path=parsed_file.path,
            success=False,
            was_new=False,
            error="Manuel düzenlenmiş dosya — atlandı",
        )

    full_path = project_path / parsed_file.path
    was_new = not full_path.exists()

    # Mevcut içeriği al (diff için)
    old_content = ""
    if not was_new:
        try:
            old_content = full_path.read_text(encoding="utf-8")
        except Exception:
            old_content = ""

    # Klasörü oluştur
    try:
        full_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return WriteResult(
            path=parsed_file.path,
            success=False,
            was_new=was_new,
            error=f"Klasör oluşturulamadı: {e}",
        )

    # Atomic yazma: önce .tmp dosyasına, sonra rename
    tmp_path = full_path.with_suffix(full_path.suffix + ".tmp")
    try:
        tmp_path.write_text(parsed_file.content, encoding="utf-8")
        tmp_path.replace(full_path)
    except Exception as e:
        tmp_path.unlink(missing_ok=True)
        return WriteResult(
            path=parsed_file.path,
            success=False,
            was_new=was_new,
            error=f"Yazma hatası: {e}",
        )

    # Diff üret
    diff = _generate_diff(
        old_content,
        parsed_file.content,
        parsed_file.path,
    )

    return WriteResult(
        path=parsed_file.path,
        success=True,
        was_new=was_new,
        diff=diff,
    )


def write_files(
    parsed_files: list[ParsedFile],
    project_path: str | Path,
    manually_edited_files: list[str] | None = None,
) -> WriteSession:
    """
    Birden fazla dosyayı yazar.
    WriteSession döner.
    """
    session = WriteSession()

    for pf in parsed_files:
        result = write_file(pf, project_path, manually_edited_files)
        if result.error == "Manuel düzenlenmiş dosya — atlandı":
            session.files_skipped.append(pf.path)
        else:
            session.files_written.append(result)

    return session


def _generate_diff(old: str, new: str, file_path: str) -> str:
    """
    İki metin arasında unified diff üretir.
    Yeni dosyaysa kısa bir özet döner.
    """
    if not old:
        line_count = len(new.splitlines())
        return f"+ Yeni dosya oluşturuldu ({line_count} satır)"

    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)

    diff = list(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm="",
        )
    )

    if not diff:
        return "~ Değişiklik yok"

    return "".join(diff)


# ─────────────────────────────────────────
# Diff Özetleme (UI için)
# ─────────────────────────────────────────


def summarize_diff(diff: str) -> dict:
    """
    Diff'ten eklenen/silinen satır sayısını çıkarır.
    Streamlit UI'da gösterim için.
    """
    if diff.startswith("+") and "Yeni dosya" in diff:
        return {"added": int(diff.split("(")[1].split(" ")[0]), "removed": 0}
    if diff == "~ Değişiklik yok":
        return {"added": 0, "removed": 0}

    added = sum(
        1
        for line in diff.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    removed = sum(
        1
        for line in diff.splitlines()
        if line.startswith("-") and not line.startswith("---")
    )

    return {"added": added, "removed": removed}
