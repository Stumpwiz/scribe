"""
Formatter service tool for the Scribe project.

Formatter v1:
- Convert a PDF report into one or more PNGs for LaTeX appendices.
- Naming convention:
    * single-page:  <office>.png
    * multi-page:   <office>-1.png, <office>-2.png, ...
- Default DPI: 300 (matches scan workflow)
- Optional whitespace trim (only if Pillow is available)
- Writes manifest.json describing outputs

NOTE:
- This operates on local files only (no Gmail attachment downloads here).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

import json
import logging

import pypdfium2 as pdfium

logger = logging.getLogger(__name__)


@dataclass
class FormatResult:
    success: bool
    status: str
    pdf_path: str
    office: str
    output_dir: str
    dpi: int
    pages: int
    images: List[str]
    manifest_path: str
    message: str


class FormatterService:
    DEFAULT_DPI = 300

    def pdf_to_pngs_v1(
            self,
            pdf_path: str,
            office: str,
            output_dir: Optional[str] = None,
            dpi: int = DEFAULT_DPI,
            trim_whitespace: bool = True,
    ) -> Dict[str, Any]:
        """
        Convert a local PDF into one or more PNG files.

        Args:
            pdf_path: Path to the input PDF.
            office: Naming stem, e.g., "president" -> president.png or president-1.png...
            output_dir: Directory to write outputs. If None, uses src/scribe/output/appendix_assets/<timestamp>/<office>
            dpi: Render DPI (default 300).
            trim_whitespace: If True and Pillow is installed, trims outer whitespace.

        Returns:
            Dict with success/status + paths and manifest metadata.
        """
        pdf_p = Path(pdf_path).expanduser().resolve()
        if not pdf_p.exists():
            return {
                "success": False,
                "status": "failed",
                "message": f"PDF not found: {pdf_p}",
                "pdf_path": str(pdf_p),
                "office": office,
            }
        if pdf_p.suffix.lower() != ".pdf":
            return {
                "success": False,
                "status": "failed",
                "message": f"Input must be a .pdf file: {pdf_p}",
                "pdf_path": str(pdf_p),
                "office": office,
            }

        office = (office or "").strip()
        if not office:
            return {
                "success": False,
                "status": "failed",
                "message": "office is required (e.g., --office president).",
                "pdf_path": str(pdf_p),
                "office": office,
            }

        out_dir = self._resolve_output_dir(output_dir=output_dir, office=office)
        out_dir.mkdir(parents=True, exist_ok=True)

        # Load PDF
        try:
            pdf = pdfium.PdfDocument(str(pdf_p))
        except Exception as e:
            return {
                "success": False,
                "status": "failed",
                "message": f"Failed to open PDF: {e}",
                "pdf_path": str(pdf_p),
                "office": office,
            }

        try:
            n_pages = len(pdf)
            if n_pages < 1:
                return {
                    "success": False,
                    "status": "failed",
                    "message": "PDF has no pages.",
                    "pdf_path": str(pdf_p),
                    "office": office,
                }

            # pypdfium2 uses a scale factor relative to 72 DPI.
            scale = dpi / 72.0

            rendered_pages: List[Dict[str, Any]] = []
            generated_filenames: List[str] = []
            skipped_blank_pages: List[int] = []

            pillow_ok = False
            Image = None
            ImageChops = None
            if trim_whitespace:
                try:
                    from PIL import Image as _Image
                    from PIL import ImageChops as _ImageChops
                    Image = _Image
                    ImageChops = _ImageChops
                    pillow_ok = True
                except Exception:
                    pillow_ok = False

            for idx in range(n_pages):
                page = pdf.get_page(idx)

                # Render page -> PIL image (pypdfium2 provides PIL conversion)
                try:
                    bitmap = page.render(scale=scale)
                    pil_img = bitmap.to_pil()
                finally:
                    try:
                        page.close()
                    except Exception:
                        pass

                orig_w, orig_h = pil_img.size

                if trim_whitespace and pillow_ok:
                    pil_img = self._trim_whitespace(pil_img, ImageChops=ImageChops)
                trimmed_w, trimmed_h = pil_img.size

                # Suppress pages that are effectively blank/white after render/trim.
                if self._is_effectively_blank(pil_img):
                    skipped_blank_pages.append(idx + 1)
                    continue

                rendered_pages.append({
                    "page_index": idx,
                    "page_number": idx + 1,
                    "image": pil_img,
                    "original_size_px": [orig_w, orig_h],
                    "trimmed_size_px": [trimmed_w, trimmed_h],
                })

            images: List[str] = []
            page_meta: List[Dict[str, Any]] = []
            rendered_count = len(rendered_pages)
            for output_idx, rendered_page in enumerate(rendered_pages, start=1):
                if rendered_count == 1:
                    filename = f"{office}.png"
                else:
                    filename = f"{office}-{output_idx}.png"

                out_path = out_dir / filename
                rendered_page["image"].save(out_path, format="PNG", optimize=True)

                images.append(str(out_path))
                generated_filenames.append(filename)
                page_meta.append({
                    "page_index": rendered_page["page_index"],
                    "page_number": rendered_page["page_number"],
                    "filename": filename,
                    "path": str(out_path),
                    "original_size_px": rendered_page["original_size_px"],
                    "trimmed_size_px": rendered_page["trimmed_size_px"],
                })

            # Remove stale office PNGs that were not generated in this run
            # (e.g., stale office.png after office-1.png/office-2.png, and vice versa).
            self._cleanup_stale_office_pngs(out_dir=out_dir, office=office, keep_filenames=generated_filenames)

            manifest = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "pdf_path": str(pdf_p),
                "office": office,
                "dpi": dpi,
                "scale": scale,
                "source_pages": n_pages,
                "pages": len(images),
                "skipped_blank_pages": skipped_blank_pages,
                "trim_whitespace_requested": bool(trim_whitespace),
                "trim_whitespace_applied": bool(trim_whitespace and pillow_ok),
                "output_dir": str(out_dir),
                "images": page_meta,
            }

            manifest_path = out_dir / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

            result = FormatResult(
                success=True,
                status="completed",
                pdf_path=str(pdf_p),
                office=office,
                output_dir=str(out_dir),
                dpi=dpi,
                pages=len(images),
                images=images,
                manifest_path=str(manifest_path),
                message=(
                    f"Rendered {len(images)} non-blank page(s) "
                    f"(from {n_pages} source page(s)) to PNG for office='{office}'."
                ),
            )
            return result.__dict__

        finally:
            try:
                pdf.close()
            except Exception:
                pass

    @staticmethod
    def _resolve_output_dir(output_dir: Optional[str], office: str) -> Path:
        if output_dir:
            return Path(output_dir).expanduser().resolve()

        # Default: src/scribe/output/appendix_assets/<timestamp>/<office>
        # This mirrors your other tools that locate src/ by walking parents from this file.
        base_src = Path(__file__).resolve().parents[2]  # .../src
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        return base_src / "scribe" / "output" / "appendix_assets" / ts / office

    @staticmethod
    def _trim_whitespace(pil_img, ImageChops):
        """
        Trim uniform border (whitespace) without cutting content.
        This is conservative and only trims borders that match the top-left pixel.
        """
        bg = pil_img.getpixel((0, 0))
        # Create a background image filled with that pixel and diff against original
        bg_img = pil_img.copy()
        bg_img.paste(bg, (0, 0, pil_img.size[0], pil_img.size[1]))
        diff = ImageChops.difference(pil_img, bg_img)
        bbox = diff.getbbox()
        if bbox:
            return pil_img.crop(bbox)
        return pil_img

    @staticmethod
    def _is_effectively_blank(
            pil_img,
            white_threshold: int = 245,
            max_dark_pixel_ratio: float = 0.0001,
    ) -> bool:
        """
        Return True when the image has too little non-white content to be meaningful.

        white_threshold: pixels >= threshold are treated as white background.
        max_dark_pixel_ratio: pages at or below this proportion of dark pixels
            are treated as blank, allowing isolated rendering artifacts without
            suppressing sparse real text.
        """
        gray = pil_img.convert("L")
        total_pixels = gray.width * gray.height
        if total_pixels == 0:
            return True

        dark_pixels = sum(gray.histogram()[:white_threshold])
        return dark_pixels / total_pixels <= max_dark_pixel_ratio

    @staticmethod
    def _cleanup_stale_office_pngs(out_dir: Path, office: str, keep_filenames: List[str]) -> None:
        """
        Keep only the PNGs for this office generated by the current run.
        Removes stale single-page and multi-page variants.
        """
        keep = set(keep_filenames)
        pattern = re.compile(rf"^{re.escape(office)}(?:-\d+)?\.png$")
        for p in out_dir.iterdir():
            if not p.is_file():
                continue
            if pattern.fullmatch(p.name) and p.name not in keep:
                try:
                    p.unlink()
                except Exception:
                    logger.warning("Failed to remove stale PNG: %s", p)
