"""
LocalForge — Test Runner
Proje klasöründe pytest çalıştırır, çıktıyı parse eder.
"""

import subprocess
import sys
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TestFailure:
    file: str  # Hatalı test dosyası
    test_name: str  # Test fonksiyon adı
    error_type: str  # AssertionError, ImportError vb.
    error_msg: str  # Hata mesajı
    source_file: str  # Hatanın kaynaklandığı kaynak dosya (test değil)
    line_no: int = 0


@dataclass
class TestResult:
    success: bool
    passed: int = 0
    failed: int = 0
    errors: int = 0
    output: str = ""
    failures: list[TestFailure] = field(default_factory=list)
    install_output: str = ""


def install_requirements(project_path: str | Path) -> tuple[bool, str]:
    """
    requirements.txt'deki paketleri kurar.
    Returns: (success, output)
    """
    req_path = Path(project_path) / "requirements.txt"
    if not req_path.exists():
        return True, "requirements.txt bulunamadı, atlanıyor."

    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(req_path), "--quiet"],
        capture_output=True,
        text=True,
        cwd=str(project_path),
    )

    output = result.stdout + result.stderr
    return result.returncode == 0, output


def run_tests(project_path: str | Path) -> TestResult:
    """
    Proje klasöründe pytest çalıştırır.
    Önce requirements.txt kurulur, sonra testler çalıştırılır.
    """
    project_path = Path(project_path)

    # Önce bağımlılıkları kur
    install_ok, install_output = install_requirements(project_path)

    # pytest çalıştır
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--tb=short", "-v", "--no-header"],
        capture_output=True,
        text=True,
        cwd=str(project_path),
        env={**__import__("os").environ, "PYTHONPATH": str(project_path)},
    )

    output = result.stdout + result.stderr

    # Sonuçları parse et
    passed, failed, errors = _parse_summary(output)
    failures = _parse_failures(output, project_path)

    success = result.returncode == 0 and failed == 0 and errors == 0

    return TestResult(
        success=success,
        passed=passed,
        failed=failed,
        errors=errors,
        output=output,
        failures=failures,
        install_output=install_output,
    )


def _parse_summary(output: str) -> tuple[int, int, int]:
    """pytest özet satırından passed/failed/error sayılarını çıkarır."""
    passed = failed = errors = 0

    # "5 passed, 2 failed, 1 error" formatı
    summary_match = re.search(r"(\d+) passed|(\d+) failed|(\d+) error", output)

    passed_m = re.search(r"(\d+) passed", output)
    failed_m = re.search(r"(\d+) failed", output)
    error_m = re.search(r"(\d+) error", output)

    if passed_m:
        passed = int(passed_m.group(1))
    if failed_m:
        failed = int(failed_m.group(1))
    if error_m:
        errors = int(error_m.group(1))

    return passed, failed, errors


def _parse_failures(output: str, project_path: Path) -> list[TestFailure]:
    """
    pytest çıktısından hata detaylarını ayıklar.
    ERROR collecting ve FAILED satırlarını işler.
    """
    failures = []
    lines = output.splitlines()

    i = 0
    while i < len(lines):
        line = lines[i]

        # "ERROR collecting src/test" formatı
        error_collect_match = re.match(r"_{5,}\s+ERROR collecting (.+?)\s+_{5,}", line)
        # "FAILED test::func" formatı
        failed_match = line.startswith("FAILED ") or (
            line.startswith("ERROR ") and "::" in line
        )

        if error_collect_match or failed_match:
            if error_collect_match:
                test_file = error_collect_match.group(1).strip()
                test_name = ""
            else:
                parts = line.split(" ", 1)
                test_ref = parts[1].strip() if len(parts) > 1 else ""
                if "::" in test_ref:
                    test_file, test_name = test_ref.split("::", 1)
                else:
                    test_file, test_name = test_ref, ""

            # Hata detaylarını bul
            error_type = ""
            error_msg = ""
            source_file = test_file
            line_no = 0

            j = i + 1
            while j < len(lines) and j < i + 50:
                l = lines[j]

                # "E   NameError: ..." veya "E   sqlalchemy.exc.InvalidRequestError: ..." formatı
                e_match = re.match(r"E\s+(.+Error.*)", l)
                if e_match:
                    full_err = e_match.group(1)
                    # Son Error kelimesini bul
                    err_type_match = re.search(r"(\w+Error)", full_err)
                    if err_type_match:
                        error_type = err_type_match.group(1)
                    error_msg = full_err.strip()

                # "src/task/schemas.py:18" veya "src\task\schemas.py:18" formatı
                src_match = re.search(r"(src[/\\][^\s:]+\.py):(\d+)", l)
                if src_match:
                    candidate = src_match.group(1).replace("\\", "/")
                    fname = candidate.lower()
                    # Test, conftest ve database.py değilse kaynak olarak al
                    # database.py genel altyapı dosyası, hata kaynağı değil
                    skip = ["test", "conftest", "database.py"]
                    if not any(s in fname for s in skip):
                        source_file = candidate
                        line_no = int(src_match.group(2))

                j += 1

            failures.append(
                TestFailure(
                    file=test_file,
                    test_name=test_name,
                    error_type=error_type or "CollectionError",
                    error_msg=error_msg,
                    source_file=source_file,
                    line_no=line_no,
                )
            )

        i += 1

    return failures


def has_tests(project_path: str | Path) -> bool:
    """Projede test dosyası var mı?"""
    project_path = Path(project_path)
    test_files = list(project_path.rglob("test_*.py")) + list(
        project_path.rglob("*_test.py")
    )
    return len(test_files) > 0
