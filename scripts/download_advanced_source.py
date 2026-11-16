"""Download the frozen Advanced PDF from its official source and verify it."""

from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    manifest = json.loads((ROOT / "advanced" / "source_manifest.json").read_text(encoding="utf-8"))
    output = ROOT / "advanced" / "source" / manifest["file_name"]
    output.parent.mkdir(parents=True, exist_ok=True)
    if not output.is_file():
        request = urllib.request.Request(manifest["download_url"], headers={"User-Agent": "Day07-Lab/1.0"})
        with urllib.request.urlopen(request, timeout=120) as response, output.open("wb") as target:
            while block := response.read(1024 * 1024):
                target.write(block)

    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    if digest != manifest["sha256"]:
        raise SystemExit(f"PDF checksum mismatch: {digest}")
    reader = PdfReader(output)
    if len(reader.pages) != manifest["physical_pages"]:
        raise SystemExit(f"Expected {manifest['physical_pages']} pages, got {len(reader.pages)}")
    license_text = reader.pages[manifest["verified_license_pdf_page"] - 1].extract_text() or ""
    if "Creative Commons Attribution 3.0 IGO" not in license_text:
        raise SystemExit("The declared CC BY 3.0 IGO license was not found on PDF page 6")
    print(f"Advanced source OK: {len(reader.pages)} pages, SHA-256 {digest}, CC BY 3.0 IGO")


if __name__ == "__main__":
    main()
