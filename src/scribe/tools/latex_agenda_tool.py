"""
LaTeX agenda tool for the Scribe project.

This module provides the LaTeXAgendaTool class for rendering LaTeX agenda templates
and saving them as .tex files.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, ClassVar

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from crewai.tools import BaseTool

from scribe.meeting.meeting_dates import compute_meeting_dates, cycle_from_meeting_date
logger = logging.getLogger(__name__)


class LaTeXAgendaTool(BaseTool):
    name: str = "LaTeXAgendaTool"
    description: str = "Renders a LaTeX agenda file from a template using meeting context information."
    base_dir: ClassVar[Path] = Path(__file__).resolve().parent.parent.parent
    output_dir: ClassVar[Path] = base_dir / "scribe" / "output" / "agendas"

    @staticmethod
    def _format_human_date(value: str) -> str:
        parsed = datetime.fromisoformat(value).date()
        return f"{parsed.strftime('%B')} {parsed.day}, {parsed.year}"

    def _render_meeting_dates(self, meeting_info: Dict[str, Any], output_dir: Path) -> None:
        cycle = meeting_info.get("cycle")
        if not cycle:
            meeting_date = meeting_info.get("meetingDate") or meeting_info.get("date")
            if meeting_date:
                cycle = cycle_from_meeting_date(meeting_date)
        if not cycle:
            raise ValueError("Missing meetingDate or cycle for meeting date rendering")

        meeting_type = meeting_info.get("meetingType", "")
        meeting_dates = compute_meeting_dates(cycle, meeting_type)
        explicit_meeting_date = meeting_info.get("meetingDate") or meeting_info.get("date")
        if explicit_meeting_date:
            try:
                # Keep last/next from cycle defaults, but render the selected meeting date in the header.
                meeting_dates["meeting_date"] = self._format_human_date(str(explicit_meeting_date))
            except ValueError:
                logger.warning("Could not parse explicit meetingDate '%s'; using cycle-derived date", explicit_meeting_date)
        meeting_info.update(meeting_dates)

        template_dir = self.base_dir / "scribe" / "assets" / "templates"
        env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=False,
            undefined=StrictUndefined
        )
        template = env.get_template("meeting_dates.tex.j2")
        rendered = template.render(**meeting_dates)
        (output_dir / "meeting_dates.tex").write_text(rendered, encoding="utf-8")

    def _render_template(self, template_path: str, meeting_info: Dict[str, Any]) -> str:
        """
        Render a Jinja2 LaTeX template with the meeting_info context.
        """
        try:
            template_dir = self.base_dir / "scribe" / "assets" / "templates"
            if not template_dir.exists():
                raise FileNotFoundError(f"Template directory does not exist: {template_dir}")

            env = Environment(
                loader=FileSystemLoader(str(template_dir)),
                autoescape=False
            )

            template_name = Path(template_path).name
            template = env.get_template(template_name)

            return template.render(**meeting_info)
        except Exception as e:
            raise ValueError(f"Error rendering Jinja2 template: {str(e)}")

    def _run(self, meeting_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a .tex file for the given meeting date and type.
        """
        try:
            logger.info(f"Using Tool: {self.name}")
            required_fields = ["meetingDate", "meetingType", "agendaTemplate"]
            for field in required_fields:
                if field not in meeting_info:
                    raise ValueError(f"Required field '{field}' is missing from meeting_info")

            meeting_date = meeting_info["meetingDate"]
            meeting_type = meeting_info["meetingType"]
            template_path = meeting_info["agendaTemplate"]

            self.output_dir.mkdir(parents=True, exist_ok=True)

            self._render_meeting_dates(meeting_info, self.output_dir)

            tex_filename = f"agenda_{meeting_date}_{meeting_type}.tex"
            tex_path = self.output_dir / tex_filename

            rendered_latex = self._render_template(template_path, meeting_info)

            with tex_path.open("w", encoding="utf-8") as f:
                f.write(rendered_latex)

            logger.info(f"LaTeX agenda file generated successfully: {tex_path}")
            return {"texPath": str(tex_path)}
        except Exception as e:
            error_message = f"Error in LaTeXAgendaTool: {str(e)}"
            logger.error(error_message)
            return {"error": error_message}
