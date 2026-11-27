"""Create a portable x64 Windows package for the offline checker."""

import argparse
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'desktop/InsureDataGate.Desktop/InsureDataGate.Desktop.csproj'
NET_RUNTIME = '10.0.12'


def bundle_checker(payload):
    base = Path(sys.base_prefix)
    runtime = payload / 'python'
    runtime.mkdir()
    for name in ('python.exe', 'python3.dll', 'python312.dll', 'vcruntime140.dll',
                 'vcruntime140_1.dll', 'LICENSE.txt'):
        shutil.copy2(base / name, runtime / name)
    shutil.copytree(base / 'DLLs', runtime / 'DLLs', ignore=shutil.ignore_patterns('_tkinter.pyd', '*.ico'))
    shutil.copytree(base / 'Lib', runtime / 'Lib', ignore=shutil.ignore_patterns(
        'site-packages', '__pycache__', '*.pyc', 'test', 'tests', 'idlelib', 'tkinter', 'turtledemo', 'ensurepip'))
    packages = runtime / 'Lib/site-packages'
    packages.mkdir()
    shutil.copytree(ROOT / 'src/insuredatagate', packages / 'insuredatagate',
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--nuget-source', type=Path, default=Path.home() / '.nuget/packages')
    args = parser.parse_args()
    if sys.platform != 'win32' or sys.version_info[:2] != (3, 12) or sys.maxsize <= 2**32:
        parser.error('Build with x64 Python 3.12 on Windows')
    output = args.output.resolve()
    if output.suffix.lower() != '.zip' or output.exists() or not output.parent.is_dir():
        parser.error('Choose a new ZIP in an existing output folder')
    nuget = args.nuget_source.resolve()
    properties = [f'-p:RuntimeFrameworkVersion={NET_RUNTIME}', '-p:NuGetAudit=false']
    with TemporaryDirectory(prefix='insuredatagate-build-') as temporary:
        staging = Path(temporary)
        payload = staging / 'InsureDataGate'
        subprocess.run(['dotnet', 'restore', str(PROJECT), '-r', 'win-x64',
                        '--source', str(nuget), '-p:SelfContained=true', *properties], check=True)
        subprocess.run(['dotnet', 'publish', str(PROJECT), '-c', 'Release', '-r', 'win-x64',
                        '--self-contained', 'true', '--no-restore', '-o', str(payload),
                        '-p:DebugType=None', '-p:DebugSymbols=false', *properties], check=True)
        bundle_checker(payload)
        for source, name in (
            (ROOT / 'LICENSE', 'LICENSE.txt'),
            (ROOT / 'docs/windows-app.md', '사용법.md'),
            (nuget / 'microsoft.netcore.app.runtime.win-x64' / NET_RUNTIME / 'LICENSE.TXT', 'DOTNET-LICENSE.txt'),
            (nuget / 'microsoft.netcore.app.runtime.win-x64' / NET_RUNTIME / 'THIRD-PARTY-NOTICES.TXT', 'DOTNET-NOTICES.txt'),
            (nuget / 'microsoft.windowsdesktop.app.runtime.win-x64' / NET_RUNTIME / 'LICENSE', 'WPF-LICENSE.txt'),
        ):
            shutil.copy2(source, payload / name)
        archive = shutil.make_archive(str(staging / 'release'), 'zip', staging, payload.name)
        with output.open('xb') as destination, Path(archive).open('rb') as source:
            shutil.copyfileobj(source, destination)
    print(output)


if __name__ == '__main__':
    main()
