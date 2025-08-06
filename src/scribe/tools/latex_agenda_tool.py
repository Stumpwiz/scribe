"""
LaTeX agenda tool for the Scribe project.

This module provides the LaTeXAgendaTool class for rendering LaTeX agenda templates
and saving them as .tex files.
"""

import logging
from pathlib import Path
from typing import Any, Dict, ClassVar

from jinja2 import Environment, FileSystemLoader
from crewai.tools import BaseTool

logger = logging.getLogger(__name__)


class LaTeXAgendaTool(BaseTool):
    name: str = "LaTeXAgendaTool"
    description: str = "Renders a LaTeX agenda file from a template using meeting context information."
    base_dir: ClassVar[Path] = Path(__file__).resolve().parent.parent.parent
    output_dir: ClassVar[Path] = base_dir / "scribe" / "output" / "agendas"

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
