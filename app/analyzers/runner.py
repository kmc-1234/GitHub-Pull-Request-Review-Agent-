import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from app.review.schemas import ReviewFinding, Severity

logger = logging.getLogger(__name__)


class StaticAnalyzerRunner:
    def run(self, files: list[dict[str, Any]]) -> list[ReviewFinding]:
        python_files = [
            item for item in files if item["filename"].endswith(".py") and item.get("patch")
        ]
        if not python_files:
            return []

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for item in python_files:
                path = root / item["filename"]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(_reconstruct_added_file(item.get("patch") or ""), encoding="utf-8")

            findings: list[ReviewFinding] = []
            findings.extend(self._run_ruff(root))
            findings.extend(self._run_bandit(root))
            findings.extend(self._run_semgrep(root))
            return findings

    def _run_ruff(self, root: Path) -> list[ReviewFinding]:
        executable = shutil.which("ruff")
        if not executable:
            logger.info("ruff not installed; skipping")
            return []
        proc = subprocess.run(
            [executable, "check", "--output-format=json", str(root)],
            check=False,
            text=True,
            capture_output=True,
        )
        if not proc.stdout:
            return []
        data = json.loads(proc.stdout)
        findings = []
        for item in data:
            filename = str(Path(item["filename"]).relative_to(root))
            findings.append(
                ReviewFinding(
                    file_path=filename,
                    line=item["location"]["row"],
                    title=item.get("code") or "Ruff finding",
                    description=item.get("message") or "Ruff reported a code-quality issue.",
                    severity=Severity.low,
                    category="quality",
                    suggestion=(item.get("fix") or {}).get("message"),
                    confidence=0.86,
                    source="ruff",
                )
            )
        return findings

    def _run_bandit(self, root: Path) -> list[ReviewFinding]:
        executable = shutil.which("bandit")
        if not executable:
            logger.info("bandit not installed; skipping")
            return []
        proc = subprocess.run(
            [executable, "-r", str(root), "-f", "json", "-q"],
            check=False,
            text=True,
            capture_output=True,
        )
        if not proc.stdout:
            return []
        data = json.loads(proc.stdout)
        severity_map = {"HIGH": Severity.high, "MEDIUM": Severity.medium, "LOW": Severity.low}
        return [
            ReviewFinding(
                file_path=str(Path(item["filename"]).relative_to(root)),
                line=item["line_number"],
                title=item.get("test_name") or item.get("test_id") or "Bandit finding",
                description=item.get("issue_text") or "Bandit reported a security issue.",
                severity=severity_map.get(item.get("issue_severity"), Severity.medium),
                category="security",
                suggestion=None,
                confidence={"HIGH": 0.95, "MEDIUM": 0.8, "LOW": 0.65}.get(
                    item.get("issue_confidence"), 0.75
                ),
                source="bandit",
            )
            for item in data.get("results", [])
        ]

    def _run_semgrep(self, root: Path) -> list[ReviewFinding]:
        executable = shutil.which("semgrep")
        if not executable:
            logger.info("semgrep not installed; skipping")
            return []
        proc = subprocess.run(
            [executable, "--config", "auto", "--json", str(root)],
            check=False,
            text=True,
            capture_output=True,
        )
        if not proc.stdout:
            return []
        data = json.loads(proc.stdout)
        severity_map = {"ERROR": Severity.high, "WARNING": Severity.medium, "INFO": Severity.low}
        findings = []
        for item in data.get("results", []):
            extra = item.get("extra", {})
            path = str(Path(item["path"]).relative_to(root))
            findings.append(
                ReviewFinding(
                    file_path=path,
                    line=item["start"]["line"],
                    title=extra.get("check_id") or item.get("check_id") or "Semgrep finding",
                    description=extra.get("message")
                    or "Semgrep reported a security or correctness issue.",
                    severity=severity_map.get(extra.get("severity"), Severity.medium),
                    category="security",
                    suggestion=extra.get("fix"),
                    confidence=0.82,
                    source="semgrep",
                )
            )
        return findings


def _reconstruct_added_file(patch: str) -> str:
    lines = []
    for raw in patch.splitlines():
        if raw.startswith("@@") or raw.startswith("---") or raw.startswith("+++"):
            continue
        if raw.startswith("+"):
            lines.append(raw[1:])
        elif raw.startswith(" "):
            lines.append(raw[1:])
    return "\n".join(lines) + "\n"
