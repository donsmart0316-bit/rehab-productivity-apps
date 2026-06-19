from __future__ import annotations

import argparse
import json
from pathlib import Path


DATASETS = {
    "sleep_health_lifestyle": "uom190346a/sleep-health-and-lifestyle-dataset",
    "employee_burnout": "blurredmachine/are-your-employees-burning-out",
    "wfh_employee_burnout": "sonalshinde123/work-from-home-employee-burnout-dataset",
}


def download_with_kaggle_cli(slug: str, destination: Path) -> dict:
    destination.mkdir(parents=True, exist_ok=True)
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi

        api = KaggleApi()
        api.authenticate()
        api.dataset_download_files(slug, path=destination, unzip=True, quiet=False)
        ok = True
        stdout = "Downloaded with KaggleApi.dataset_download_files"
        stderr = ""
    except BaseException as exc:
        ok = False
        stdout = ""
        if isinstance(exc, SystemExit):
            stderr = "Kaggle authentication is not configured. Run `kaggle auth login` or add a Kaggle API token."
        else:
            stderr = repr(exc)
    return {
        "slug": slug,
        "ok": ok,
        "stdout": stdout[-1000:],
        "stderr": stderr[-1000:],
        "files": [str(path.relative_to(destination)) for path in destination.rglob("*") if path.is_file()],
    }


def download_all(project_root: Path) -> list[dict]:
    raw_root = project_root / "data" / "raw"
    manifest = []
    for name, slug in DATASETS.items():
        manifest.append(download_with_kaggle_cli(slug, raw_root / name))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Kaggle datasets for the Productivity & Recovery project.")
    parser.add_argument("--project-root", default=Path(__file__).resolve().parents[2], type=Path)
    args = parser.parse_args()
    manifest = download_all(args.project_root)
    manifest_path = args.project_root / "data" / "raw" / "download_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
