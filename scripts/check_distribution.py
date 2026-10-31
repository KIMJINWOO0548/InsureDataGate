"""Build self-check using an already-installed setuptools; no package publication."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile


def main() -> None:
    from setuptools import build_meta

    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    output = root / "dist"
    output.mkdir(exist_ok=True)
    sdist = output / build_meta.build_sdist(str(output))
    wheel = output / build_meta.build_wheel(str(output))
    with zipfile.ZipFile(wheel) as archive:
        wheel_names = archive.namelist()
    with tarfile.open(sdist) as archive:
        source_names = ["/".join(item.name.split("/")[1:]) for item in archive.getmembers() if item.isfile()]
    assert {"insuredatagate/validator.py", "insuredatagate/cli.py", "insuredatagate/__main__.py"} <= set(wheel_names)
    assert {"examples/insurance-demo/manifest.json", "docs/CONTRACT.md", "tests/test_cli.py", "scripts/check_distribution.py"} <= set(source_names)
    for name in wheel_names + source_names:
        assert not any(part in {".git", ".venv", ".runtime", "reports", "__pycache__"} for part in name.split("/")), name
    with tempfile.TemporaryDirectory(prefix="insuredatagate-wheel-") as scratch:
        temp = Path(scratch)
        venv.EnvBuilder(with_pip=True).create(temp / "env")
        executables = temp / "env" / ("Scripts" if os.name == "nt" else "bin")
        python = executables / ("python.exe" if os.name == "nt" else "python")
        cli = executables / ("insuredatagate.exe" if os.name == "nt" else "insuredatagate")
        env = dict(os.environ, PYTHONUTF8="1")
        env.pop("PYTHONPATH", None)

        def run(*args, expected=0):
            result = subprocess.run(list(map(str, args)), cwd=temp, env=env, capture_output=True, text=True, encoding="utf-8", timeout=120)
            assert result.returncode == expected, (result.returncode, result.stdout, result.stderr)
            return result

        run(python, "-m", "pip", "install", "--no-index", "--no-deps", wheel)
        assert "0.1.0" in run(cli, "--version").stdout
        manifest = root / "examples" / "insurance-demo" / "manifest.json"
        report = json.loads(run(cli, "check", manifest, "--json").stdout)
        assert report["status"] == "PASS" and report["counts"]["cases"] == 6
        assert json.loads(run(python, "-m", "insuredatagate", "check", manifest, "--json").stdout) == report
        inputs = temp / "inputs.jsonl"
        run(cli, "export-inputs", manifest, "--output", inputs)
        before = inputs.read_bytes()
        rows = [json.loads(line) for line in before.splitlines()]
        assert len(rows) == 6 and all(set(row) == {"case_id", "input", "source_ids"} for row in rows)
        run(cli, "export-inputs", manifest, "--output", inputs, expected=2)
        assert inputs.read_bytes() == before
    print("PASS: wheel/sdist contents, isolated offline wheel install, both entrypoints, demo, gold-free export, output preservation")


if __name__ == "__main__":
    main()
