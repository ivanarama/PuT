"""Package the tagged configuration and its pinned OneBase runtime for Windows."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile


def output(*args):
    return subprocess.check_output(args, encoding="utf-8").strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True, help="Existing configuration tag, e.g. v1.4.0")
    parser.add_argument("--onebase", required=True, type=Path)
    parser.add_argument("--engine-source", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    ref = "refs/tags/" + args.tag
    runtime = json.loads(output("git", "-C", project, "show", ref + ":platform-patches/runtime.json"))
    version = runtime["configuration_version"]
    if args.tag != "v" + version:
        raise ValueError("Tag and configuration version differ")
    if output("git", "-C", args.engine_source, "rev-parse", "HEAD") != runtime["commit"]:
        raise ValueError("Engine checkout differs from the pinned commit")
    binary = args.onebase.resolve(strict=True)
    build = json.loads(output("go", "version", "-m", "-json", binary))
    settings = {s["Key"]: s["Value"] for s in build["Settings"]}
    if (settings.get("GOOS"), settings.get("GOARCH")) != ("windows", "amd64"):
        raise ValueError("Expected a windows/amd64 executable")
    if build["Path"] != "github.com/ivantit66/onebase/cmd/onebase" or settings.get("vcs.revision") != runtime["commit"]:
        raise ValueError("Executable does not report the pinned OneBase source revision")
    module_paths = dict(line.split("|", 1) for line in output(
        "go", "-C", args.engine_source, "list", "-m", "-f", "{{.Path}}|{{.Dir}}", "all"
    ).splitlines())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    name = f"PuT-{version}-windows-amd64.zip"
    with tempfile.TemporaryDirectory(dir=args.output_dir) as tmp:
        tmp = Path(tmp)
        archive = tmp / name
        prefix = f"PuT-{version}/"
        subprocess.run(["git", "-C", project, "archive", "--format=zip", "--prefix=" + prefix,
                        "--output", archive, ref], check=True)
        with zipfile.ZipFile(archive, "a", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
            for file in ("scripts/check_runtime.py", "platform-patches/runtime.json",
                         "platform-patches/put-ui.patch", "config/app.yaml"):
                bundle.extract(prefix + file, tmp)
            check_dir = tmp / prefix
            subprocess.run([sys.executable, check_dir / "scripts/check_runtime.py", "--onebase", binary], check=True)
            bundle.write(binary, prefix + ".local/onebase-preview.exe")
            bundle.writestr(prefix + "START-HERE.txt", (
                f"ПУТ {version} для Windows x64\r\n\r\n"
                "Распакуйте ZIP целиком. В PowerShell откройте каталог с этим файлом и выполните:\r\n"
                "powershell -NoProfile -ExecutionPolicy RemoteSigned -File .\\scripts\\start_preview.ps1\r\n\r\n"
                "Если Windows заблокировала скачанный архив, откройте свойства ZIP, нажмите "
                "«Разблокировать» и распакуйте его снова. Затем повторите запуск.\r\n"
                "Откроется http://127.0.0.1:8100/ui/. При первом запуске создаётся демобаза SQLite.\r\n"
                "Пользователь preview, случайный пароль находится в .local/credentials.txt.\r\n"
                "Сохранённая база находится в .local/preview.db.\r\n"
            ).encode("utf-8-sig"))

            def add_notices(folder, dest):
                if not folder.is_dir():
                    raise FileNotFoundError(folder)
                files = [p for p in sorted(folder.iterdir()) if p.is_file() and
                         p.name.upper().startswith(("LICENSE", "LICENCE", "COPYING", "NOTICE", "PATENTS"))]
                if not files:
                    raise ValueError(f"Missing licensing files in {folder}")
                for p in files:
                    bundle.write(p, prefix + "licenses/" + dest + "/" + p.name)
            add_notices(args.engine_source, "onebase")
            add_notices(Path(output("go", "env", "GOROOT")), "go")
            for dep in build["Deps"]:
                folder = module_paths.get(dep["Path"])
                if not folder:
                    raise ValueError(f"Missing sources for linked dependency {dep['Path']}")
                add_notices(Path(folder), dep["Path"])
        with zipfile.ZipFile(archive) as bundle:
            if bundle.testzip():
                raise ValueError("ZIP integrity check failed")
        archive.replace(args.output_dir / name)
    with (args.output_dir / name).open("rb") as package:
        sha256 = hashlib.sha256()
        for block in iter(lambda: package.read(1024 * 1024), b""):
            sha256.update(block)
        digest = sha256.hexdigest()
    (args.output_dir / (name + ".sha256")).write_text(f"{digest}  {name}\n", encoding="ascii")
    print(name, digest)


if __name__ == "__main__":
    main()
