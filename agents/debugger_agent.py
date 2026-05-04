"""
LocalForge — Debugger Agent
Test hatalarını analiz eder, LLM ile düzeltir, tekrar test eder.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator

from core.llm_client import LLMClient
from core.context_manager import ContextManager
from core.test_runner import TestResult, TestFailure, run_tests
from core.file_writer import parse_llm_output, write_files

MAX_FIX_RETRIES = 3


@dataclass
class DebugSession:
    total_failures: int = 0
    fixed: int = 0
    unfixed: int = 0
    rounds: int = 0
    final_result: TestResult = None


def _load_prompt() -> str:
    prompt_path = Path(__file__).parent.parent / "prompts" / "debugger.md"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    return _DEFAULT_PROMPT


_DEFAULT_PROMPT = """Sen bir Python hata ayıklayıcısısın.
Sana bir test hatası ve ilgili kaynak kodu verilecek.
Hatayı düzelt ve dosyanın tamamını # Dosya: yol formatında ver.
Başka hiçbir şey yazma, sadece düzeltilmiş kodu ver."""


class DebuggerAgent:
    def __init__(
        self,
        client: LLMClient,
        context_manager: ContextManager,
        project_path: str | Path,
    ):
        self.client = client
        self.ctx = context_manager
        self.project_path = Path(project_path)
        self.system_prompt = _load_prompt()

    def run(self) -> Generator[dict, None, None]:
        """
        Test döngüsü:
        1. Testleri çalıştır
        2. Hatalar varsa LLM ile düzelt
        3. Tekrar test et (max 3 tur)
        """
        session = DebugSession()

        for round_no in range(1, MAX_FIX_RETRIES + 1):
            session.rounds = round_no

            yield {"type": "test_start", "data": {"round": round_no}}

            # Testleri çalıştır
            result = run_tests(self.project_path)
            session.final_result = result

            # Kurulum çıktısı
            if result.install_output:
                yield {
                    "type": "install_output",
                    "data": {"output": result.install_output},
                }

            # Test çıktısı
            yield {
                "type": "test_output",
                "data": {
                    "output": result.output,
                    "passed": result.passed,
                    "failed": result.failed,
                    "errors": result.errors,
                },
            }

            if result.success:
                yield {
                    "type": "all_passed",
                    "data": {
                        "passed": result.passed,
                        "rounds": round_no,
                    },
                }
                return

            if not result.failures:
                # Hata var ama parse edilemedi — ham çıktıyı göster
                yield {"type": "parse_failed", "data": {"output": result.output}}
                return

            session.total_failures = len(result.failures)
            yield {
                "type": "failures_found",
                "data": {
                    "count": len(result.failures),
                    "round": round_no,
                },
            }

            # Her hatayı düzelt
            for failure in result.failures:
                yield {
                    "type": "fixing",
                    "data": {
                        "file": failure.source_file,
                        "error": failure.error_msg,
                        "test": failure.test_name,
                    },
                }

                fix_result = yield from self._fix_failure(failure)

                if fix_result:
                    session.fixed += 1
                    yield {
                        "type": "fix_applied",
                        "data": {
                            "file": failure.source_file,
                        },
                    }
                    # MEMORY.md'ye kaydet
                    self.ctx.append_to_memory(
                        "Kullanıcı Manuel Değişiklikleri",
                        f"Debugger: {failure.source_file} → {failure.error_type} düzeltildi",
                    )
                else:
                    session.unfixed += 1
                    yield {
                        "type": "fix_failed",
                        "data": {
                            "file": failure.source_file,
                            "error": failure.error_msg,
                        },
                    }

        # Max tur aşıldı
        yield {
            "type": "max_retries",
            "data": {
                "fixed": session.fixed,
                "unfixed": session.unfixed,
                "rounds": session.rounds,
            },
        }

    def _fix_missing_database_import(
        self, failure: TestFailure
    ) -> Generator[dict, None, bool]:
        """
        'No module named src.database' hatasını çözer.
        models.py'daki SQLAlchemy importlarını temizler, saf Python sınıfına dönüştürür.
        """
        yield {
            "type": "fix_token",
            "data": {"token": "ORM importlari temizleniyor...\n"},
        }

        # Hangi dosyada hata var?
        source_path = self.project_path / failure.source_file
        if not source_path.exists():
            # models.py'ı ara
            matches = list(self.project_path.rglob("models.py"))
            if matches:
                source_path = matches[0]
            else:
                return False

        try:
            content = source_path.read_text(encoding="utf-8")
        except Exception:
            return False

        rel_path = str(source_path.relative_to(self.project_path))
        memory = self.ctx.read_file("MEMORY.md")

        user_message = f"""Bu dosyada SQLAlchemy/database import hatası var.
Proje veritabanı kullanmıyor — saf Python sınıfına dönüştür.

HATA: {failure.error_msg}

MEVCUT DOSYA ({rel_path}):
```python
{content}
```

YAPILACAKLAR:
1. 'from src.database import Base' satırını SİL
2. SQLAlchemy Column, Integer vb. importları SİL  
3. class'ı Base yerine object'ten türet: class MyClass:
4. Column tanımlarını normal attribute'a çevir: self.field = None
5. Dosyanın tamamını # Dosya: {rel_path} formatında ver

ÖRNEK:
# Dosya: src/text_utils/models.py
```python
class Text:
    def __init__(self, content: str = ""):
        self.content = content
        self.word_count = 0
```"""

        full_response = ""
        for token in self.client.stream(
            system_prompt=self.system_prompt,
            user_message=user_message,
            max_tokens=1024,
            temperature=0.1,
        ):
            full_response += token
            yield {"type": "fix_token", "data": {"token": token}}

        from core.file_writer import parse_llm_output, write_files

        parsed = parse_llm_output(full_response)
        if not parsed:
            return False

        session = write_files(parsed, self.project_path)
        return session.success_count > 0

    def _fix_missing_function(
        self, failure: TestFailure
    ) -> Generator[dict, None, bool]:
        """
        'cannot import name X from Y' hatasini cozer.
        Kaynak dosyaya eksik fonksiyonu/sinifi ekler.
        """
        import re

        yield {
            "type": "fix_token",
            "data": {"token": "Eksik fonksiyonlar ekleniyor...\n"},
        }

        # Hata mesajindan eksik ismi cikart: cannot import name 'word_count'
        name_match = re.search(r"cannot import name '([^']+)'", failure.error_msg)
        missing_name = name_match.group(1) if name_match else ""

        # Hata mesajindan kaynak modulu cikart: from 'src.utils.text_utils'
        module_match = re.search(r"from '([^']+)'", failure.error_msg)
        module_path = module_match.group(1) if module_match else ""

        # Modulu dosya yoluna cevir: src.utils.text_utils -> src/utils/text_utils.py
        if module_path:
            source_file = module_path.replace(".", "/") + ".py"
            source_path = self.project_path / source_file
        else:
            source_path = self.project_path / failure.source_file

        if not source_path.exists():
            matches = list(self.project_path.rglob("*.py"))
            matches = [m for m in matches if "test" not in m.name.lower()]
            if matches:
                source_path = matches[0]
            else:
                return False

        try:
            source_content = source_path.read_text(encoding="utf-8")
        except Exception:
            return False

        # Test dosyasini oku - hangi fonksiyonlarin gerektigini anlamak icin
        test_path = self.project_path / failure.file
        test_content = ""
        if test_path.exists():
            try:
                test_content = test_path.read_text(encoding="utf-8")
            except Exception:
                pass

        rel_path = str(source_path.relative_to(self.project_path))

        user_message = f"""Test dosyasi kaynak dosyadan olmayan bir isim import etmeye calisiyor.

HATA: {failure.error_msg}

KAYNAK DOSYA ({rel_path}) - EKSIK FONKSIYON BURAYA EKLENECEK:
```python
{source_content}
```

TEST DOSYASI ({failure.file}) - HANGI FONKSIYONLARI BEKLIYOR:
```python
{test_content[:800] if test_content else "Bulunamadi"}
```

YAPILACAKLAR:
1. Test dosyasinin hangi fonksiyonlari/siniflari import ettigini bul
2. Bu fonksiyonlarin hepsini kaynak dosyaya ekle
3. Mevcut kodu SILME, sadece eksik fonksiyonlari EKLE
4. Dosyanin tamamini # Dosya: {rel_path} formatinda ver"""

        full_response = ""
        for token in self.client.stream(
            system_prompt=self.system_prompt,
            user_message=user_message,
            max_tokens=2048,
            temperature=0.1,
        ):
            full_response += token
            yield {"type": "fix_token", "data": {"token": token}}

        from core.file_writer import parse_llm_output, write_files

        parsed = parse_llm_output(full_response)
        if not parsed:
            return False

        session = write_files(parsed, self.project_path)
        return session.success_count > 0

    def _fix_failure(self, failure: TestFailure) -> Generator[dict, None, bool]:
        """Tek bir test hatasını LLM ile düzeltir."""

        # ModuleNotFoundError: src.database gibi olmayan modül → import'u temizle
        if (
            failure.error_type == "ModuleNotFoundError"
            and "src.database" in failure.error_msg
        ):
            result = yield from self._fix_missing_database_import(failure)
            return result

        # ImportError: cannot import name 'func' → kaynak dosyaya eksik fonksiyon ekle
        if (
            failure.error_type == "ImportError"
            and "cannot import name" in failure.error_msg
        ):
            result = yield from self._fix_missing_function(failure)
            return result

        # Hatalı kaynak dosyayı oku
        source_path = self.project_path / failure.source_file
        if not source_path.exists():
            # Göreli yol denemesi
            matches = list(self.project_path.rglob(Path(failure.source_file).name))
            if matches:
                source_path = matches[0]
            else:
                return False

        try:
            source_content = source_path.read_text(encoding="utf-8")
        except Exception:
            return False

        # Test dosyasını da oku (bağlam için)
        test_path = self.project_path / failure.file
        test_content = ""
        if test_path.exists():
            try:
                test_content = test_path.read_text(encoding="utf-8")
            except Exception:
                pass

        # MEMORY.md bağlamı
        memory = self.ctx.read_file("MEMORY.md")
        project = self.ctx.read_file("PROJECT.md")

        rel_path = str(source_path.relative_to(self.project_path))

        user_message = f"""## Proje
{project}

## Hata Bilgisi
- Test: {failure.test_name}
- Hata Türü: {failure.error_type}
- Hata Mesajı: {failure.error_msg}
- Kaynak Dosya: {rel_path} (satır {failure.line_no})

## Hatalı Kaynak Dosya: {rel_path}
```python
{source_content}
```

## İlgili Test Dosyası: {failure.file}
```python
{test_content[:1000] if test_content else 'Bulunamadı'}
```

## Mimari Kararlar (MEMORY)
{memory[:500]}

Yukarıdaki hatayı düzelt. Sadece {rel_path} dosyasını düzelt.
Dosyanın tamamını # Dosya: {rel_path} formatında ver."""

        # Streaming LLM çağrısı
        full_response = ""
        for token in self.client.stream(
            system_prompt=self.system_prompt,
            user_message=user_message,
            max_tokens=2048,
            temperature=0.1,  # Düşük temperature — daha deterministik
        ):
            full_response += token
            yield {"type": "fix_token", "data": {"token": token}}

        # Parse ve yaz
        parsed_files = parse_llm_output(full_response)
        if not parsed_files:
            return False

        session = write_files(parsed_files, self.project_path)
        return session.success_count > 0
