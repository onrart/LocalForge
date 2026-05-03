"""
LocalForge — Syntax Validator
Üretilen kodun syntax doğruluğunu kontrol eder.
Hata varsa LLM'e geri gönderilmek üzere hata mesajı döner.
"""

import ast
import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ValidationResult:
    valid: bool
    language: str
    error: str = ""
    error_line: int = 0
    fix_hint: str = ""  # LLM'e gönderilecek düzeltme ipucu


# Desteklenen dil → dosya uzantısı eşleşmesi
LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".json": "json",
    ".html": "html",
    ".css": "css",
}


def validate(file_path: str, content: str) -> ValidationResult:
    """
    Dosya uzantısına göre uygun doğrulayıcıyı seçer ve çalıştırır.
    """
    ext = Path(file_path).suffix.lower()
    language = LANGUAGE_MAP.get(ext, "unknown")

    if language == "python":
        return _validate_python(content)
    elif language in ("javascript", "typescript"):
        return _validate_js_ts(content, file_path, language)
    elif language == "json":
        return _validate_json(content)
    else:
        # Desteklenmeyen dil → geç, hata verme
        return ValidationResult(valid=True, language=language)


def _validate_python(content: str) -> ValidationResult:
    """ast.parse ile Python syntax kontrolü — sıfır bağımlılık."""
    try:
        ast.parse(content)
        return ValidationResult(valid=True, language="python")
    except SyntaxError as e:
        hint = (
            f"Python syntax hatası satır {e.lineno}: {e.msg}\n"
            f"Sorunlu satır: {e.text.strip() if e.text else 'bilinmiyor'}\n"
            f"Sadece bu hatayı düzelt ve dosyanın tamamını tekrar yaz."
        )
        return ValidationResult(
            valid=False,
            language="python",
            error=f"SyntaxError: {e.msg} (satır {e.lineno})",
            error_line=e.lineno or 0,
            fix_hint=hint,
        )
    except Exception as e:
        return ValidationResult(
            valid=False,
            language="python",
            error=str(e),
            fix_hint=f"Python parse hatası: {e}\nDosyayı düzelt ve tekrar yaz.",
        )


def _validate_js_ts(content: str, file_path: str, language: str) -> ValidationResult:
    """
    node --check ile JS syntax kontrolü.
    TypeScript için tsc varsa kullanır, yoksa node fallback.
    Node kurulu değilse geçer (uyarı verir).
    """
    # Node.js mevcut mu?
    if not _command_exists("node"):
        return ValidationResult(
            valid=True,
            language=language,
            error="",
            fix_hint="node kurulu olmadığı için JS/TS doğrulaması atlandı.",
        )

    ext = ".ts" if language == "typescript" else ".js"

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=ext, delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        if language == "typescript" and _command_exists("tsc"):
            result = subprocess.run(
                ["tsc", "--noEmit", "--allowJs", tmp_path],
                capture_output=True,
                text=True,
                timeout=15,
            )
        else:
            result = subprocess.run(
                ["node", "--check", tmp_path],
                capture_output=True,
                text=True,
                timeout=10,
            )

        Path(tmp_path).unlink(missing_ok=True)

        if result.returncode == 0:
            return ValidationResult(valid=True, language=language)

        error_output = (result.stderr or result.stdout).strip()
        # Geçici dosya yolunu temizle
        error_clean = error_output.replace(tmp_path, file_path)

        hint = (
            f"{language.upper()} syntax hatası:\n{error_clean}\n"
            f"Sadece bu hatayı düzelt ve dosyanın tamamını tekrar yaz."
        )
        return ValidationResult(
            valid=False,
            language=language,
            error=error_clean,
            fix_hint=hint,
        )

    except subprocess.TimeoutExpired:
        Path(tmp_path).unlink(missing_ok=True)
        return ValidationResult(valid=True, language=language)  # Timeout → geç
    except Exception as e:
        Path(tmp_path).unlink(missing_ok=True)
        return ValidationResult(valid=True, language=language)


def _validate_json(content: str) -> ValidationResult:
    """json.loads ile JSON doğrulama — sıfır bağımlılık."""
    try:
        json.loads(content)
        return ValidationResult(valid=True, language="json")
    except json.JSONDecodeError as e:
        hint = (
            f"JSON syntax hatası satır {e.lineno}, sütun {e.colno}: {e.msg}\n"
            f"JSON'u düzelt ve tekrar yaz."
        )
        return ValidationResult(
            valid=False,
            language="json",
            error=f"JSONDecodeError: {e.msg} (satır {e.lineno})",
            error_line=e.lineno,
            fix_hint=hint,
        )


def _command_exists(cmd: str) -> bool:
    """Komutun PATH'te olup olmadığını kontrol eder."""
    try:
        subprocess.run([cmd, "--version"], capture_output=True, timeout=3)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def build_fix_prompt(
    original_prompt: str,
    generated_code: str,
    validation_result: ValidationResult,
) -> str:
    """
    Syntax hatası için LLM'e gönderilecek düzeltme promptu üretir.
    Coder agent tarafından retry döngüsünde kullanılır.
    """
    return f"""Aşağıdaki kodda syntax hatası var. SADECE hatayı düzelt, başka değişiklik yapma.

HATA:
{validation_result.fix_hint}

ÜRETİLEN KOD:
{generated_code}

Düzeltilmiş kodun tamamını aynı formatta (# Dosya: ... bloğu içinde) yaz."""
