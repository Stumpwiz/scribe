"""
Formatter tool for generating meeting agendas from LaTeX Jinja2 templates.

This module provides the FormatterTool class with a single public method
format_agenda_from_template that renders a LaTeX template and compiles it to PDF.

Constraints and behavior:
- Uses pathlib.Path for all path management
- Uses Jinja2 with FileSystemLoader for templating
- Saves rendered .tex under src/scribe/output/agendas/YYYY-MM-DD_<type>_agenda.tex
- Compiles with xelatex using: xelatex -output-directory <output_dir> <path/to/.tex>
- Creates needed directories if missing
- Uses logging for status and error reporting
- Handles errors for missing templates, rendering, file writing, and PDF compilation
- Returns the final PDF path as a string on success

No CLI or test code is included — only the class, importable by agents or registries.
"""
from __future__ import annotations

import logging
import subprocess
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Union

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

# Configure a module-level logger
logger = logging.getLogger(__name__)


class FormatterTool:
    """
    FormatterTool renders LaTeX agenda templates and compiles them to PDF.

    Public API:
        format_agenda_from_template(meeting_type: str, context: dict) -> str
    """

    # Base directory resolved to the project src/ folder
    base_dir: Path = Path(__file__).resolve().parents[2]

    # Supported meeting types mapped to template filenames
    _TEMPLATE_NAME_MAP = {
        "regular": "agenda_regular.tex.j2",
        "open": "agenda_open.tex.j2",
        "association": "agenda_association.tex.j2",
    }

    def format_agenda_from_template(self, meeting_type: str, context: Dict) -> str:
        """
        Render the corresponding LaTeX Jinja2 template for the given meeting_type
        and compile it to PDF.

        Args:
            meeting_type: One of {"regular", "open", "association"}.
            context: Dictionary of variables available to the Jinja2 template.

        Returns:
            str: The absolute path to the generated PDF.

        Raises:
            FileNotFoundError: If the template file is missing.
            ValueError: If meeting_type is invalid.
            RuntimeError: On template rendering failure, file write issues, or PDF compilation errors.
        """
        normalized_type = (meeting_type or "").strip().lower()
        if normalized_type not in self._TEMPLATE_NAME_MAP:
            msg = (
                f"Unsupported meeting_type '{meeting_type}'. "
                f"Expected one of: {', '.join(self._TEMPLATE_NAME_MAP.keys())}."
            )
            logger.error(msg)
            raise ValueError(msg)

        # Resolve paths
        templates_dir = self.base_dir / "scribe" / "assets" / "templates"
        template_name = self._TEMPLATE_NAME_MAP[normalized_type]
        template_path = templates_dir / template_name

        if not template_path.exists():
            msg = f"Template file not found: {template_path}"
            logger.error(msg)
            raise FileNotFoundError(msg)

        logger.info("Loading template: %s", template_path)

        # Prepare Jinja2 environment
        env = Environment(loader=FileSystemLoader(str(templates_dir)))

        # Render template
        try:
            jinja_template = env.get_template(template_name)
        except TemplateNotFound as e:
            msg = f"Template not found in loader: {template_name}"
            logger.exception(msg)
            raise FileNotFoundError(msg) from e

        try:
            rendered_tex = jinja_template.render(**(context or {}))
        except Exception as e:  # Rendering error
            msg = f"Error rendering template '{template_name}': {e}"
            logger.exception(msg)
            raise RuntimeError(msg) from e

        # Ensure output directory exists
        output_dir = self.base_dir / "scribe" / "output" / "agendas"
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            msg = f"Unable to create output directory: {output_dir}. Error: {e}"
            logger.exception(msg)
            raise RuntimeError(msg) from e

        # Compose output filenames
        today = datetime.now().strftime("%Y-%m-%d")
        tex_filename = f"{today}_{normalized_type}_agenda.tex"
        tex_path = output_dir / tex_filename

        # Write .tex file
        try:
            tex_path.write_text(rendered_tex, encoding="utf-8")
            logger.info("Wrote LaTeX file: %s", tex_path)
        except Exception as e:
            msg = f"Failed to write LaTeX file '{tex_path}': {e}"
            logger.exception(msg)
            raise RuntimeError(msg) from e

        # Compile to PDF using xelatex
        pdf_path = tex_path.with_suffix(".pdf")
        cmd = [
            "xelatex",
            f"-output-directory={str(output_dir)}",
            tex_path.name,  # run within cwd so only filename is needed
        ]

        try:
            logger.info("Compiling PDF with xelatex: %s", " ".join(cmd))
            proc = subprocess.run(
                cmd,
                cwd=str(output_dir),
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception as e:
            msg = f"Failed to invoke xelatex for '{tex_path}': {e}"
            logger.exception(msg)
            raise RuntimeError(msg) from e

        if proc.returncode != 0 or not pdf_path.exists():
            # Log stderr to help debugging
            stderr_tail = (proc.stderr or "").strip()
            stdout_tail = (proc.stdout or "").strip()
            msg = (
                f"PDF compilation failed for '{tex_path}'. Return code: {proc.returncode}.\n"
                f"stderr:\n{stderr_tail}\n"
                f"stdout:\n{stdout_tail}"
            )
            logger.error(msg)
            raise RuntimeError(msg)

        logger.info("PDF generated: %s", pdf_path)
        return str(pdf_path.resolve())

    def transcribe_audio(self, audio_path: Union[str, Path]) -> str:
        """
        Transcribe a local audio file using AssemblyAI with speaker separation and
        save the transcript as a dated .txt file.

        Behavior:
        - Loads ASSEMBLYAI_API_KEY from environment; raises RuntimeError if missing.
        - Uses AssemblyAI Transcriber with speaker_labels=True.
        - Waits for completion with built-in polling.
        - Writes lines as "Speaker X: <utterance>" under
          src/scribe/output/transcripts/YYYY-MM-DD_transcript.txt

        Args:
            audio_path: Path to a local audio file (e.g., .m4a). Accepts str or Path.

        Returns:
            str: Absolute path to the saved transcript .txt file.

        Raises:
            FileNotFoundError: If the audio file does not exist.
            RuntimeError: If the API key is missing, transcription fails, or output directory creation/writing fails.
        """
        # Late import to avoid module import errors when this feature isn't used
        try:
            import assemblyai as aai  # type: ignore
        except Exception as e:
            msg = (
                "AssemblyAI SDK is required for transcription but could not be imported. "
                "Please install the 'assemblyai' package."
            )
            logger.exception(msg)
            raise RuntimeError(msg) from e

        # Validate audio path
        src_path = Path(audio_path) if not isinstance(audio_path, Path) else audio_path
        src_path = src_path.expanduser().resolve()
        if not src_path.exists() or not src_path.is_file():
            msg = f"Audio file not found: {src_path}"
            logger.error(msg)
            raise FileNotFoundError(msg)

        # Load API key
        api_key = os.getenv("ASSEMBLYAI_API_KEY", "").strip()
        if not api_key:
            msg = (
                "Missing ASSEMBLYAI_API_KEY environment variable. "
                "Set it to your AssemblyAI API key to enable transcription."
            )
            logger.error(msg)
            raise RuntimeError(msg)

        # Configure SDK
        aai.settings.api_key = api_key
        transcriber = aai.Transcriber()
        config = aai.TranscriptionConfig(speaker_labels=True)

        logger.info("Starting transcription with AssemblyAI for: %s", src_path)
        try:
            transcript = transcriber.transcribe(str(src_path), config=config)
        except Exception as e:
            msg = f"AssemblyAI transcription request failed for '{src_path}': {e}"
            logger.exception(msg)
            raise RuntimeError(msg) from e

        # Check for error status exposed by the SDK object
        status = getattr(transcript, "status", None)
        error_detail = getattr(transcript, "error", None)
        if status == "error" or error_detail:
            msg = f"Transcription failed for '{src_path}': {error_detail or status}"
            logger.error(msg)
            raise RuntimeError(msg)

        # Prepare output directory
        output_dir = self.base_dir / "scribe" / "output" / "transcripts"
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            msg = f"Unable to create output directory: {output_dir}. Error: {e}"
            logger.exception(msg)
            raise RuntimeError(msg) from e

        # Compose output file path
        today = datetime.now().strftime("%Y-%m-%d")
        out_path = output_dir / f"{today}_transcript.txt"

        # Build lines with speaker labels
        lines = []
        utterances = getattr(transcript, "utterances", None)
        if utterances:
            for utt in utterances:
                speaker = getattr(utt, "speaker", None)
                text = getattr(utt, "text", "").strip()
                # Normalize speaker label to something printable
                label = str(speaker) if speaker is not None else "Unknown"
                if text:
                    lines.append(f"Speaker {label}: {text}")
        else:
            # Fallback: no utterances provided; use full text as one line
            full_text = (getattr(transcript, "text", "") or "").strip()
            if not full_text:
                msg = "Empty transcription result received from AssemblyAI."
                logger.error(msg)
                raise RuntimeError(msg)
            lines.append(f"Speaker 1: {full_text}")

        # Write transcript file
        try:
            out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            logger.info("Transcript saved: %s", out_path)
        except Exception as e:
            msg = f"Failed to write transcript file '{out_path}': {e}"
            logger.exception(msg)
            raise RuntimeError(msg) from e

        return str(out_path.resolve())
