"""Prompt Loader — loads prompt templates from the filesystem with version parsing."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

_PROMPTS_DIR = Path(__file__).parent.parent


@dataclass
class PromptTemplate:
    """A loaded prompt template with metadata."""
    prompt_id: str = ""
    version: str = "1.0.0"
    model_id: str = ""
    analysis_version: str = "1.0.0"
    content: str = ""
    file_path: str = ""
    variables: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "prompt_id": self.prompt_id,
            "version": self.version,
            "model_id": self.model_id,
            "analysis_version": self.analysis_version,
            "content": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "file_path": self.file_path,
            "variables": self.variables,
        }


class PromptLoader:
    """Loads prompt templates from the prompts directory.

    Supports:
    - Automatic version parsing from file headers
    - Variable extraction from {{variable}} patterns
    - Directory-based organization (category/subcategory)
    """

    HEADER_PATTERN = re.compile(r"^#\s*(prompt|version|model|analysis_version|description):\s*(.+)$", re.MULTILINE)
    VARIABLE_PATTERN = re.compile(r"\{\{(\w+)\}\}")

    def __init__(self, base_dir: str | None = None):
        self._base_dir = Path(base_dir) if base_dir else _PROMPTS_DIR
        self._cache: dict[str, PromptTemplate] = {}

    def load(self, prompt_id: str) -> PromptTemplate | None:
        """Load a prompt template by ID.

        ID format: 'category/name' or just 'name' (searches all categories).
        """
        if prompt_id in self._cache:
            return self._cache[prompt_id]

        template = self._load_by_id(prompt_id)
        if template:
            self._cache[prompt_id] = template
        return template

    def load_file(self, relative_path: str) -> PromptTemplate | None:
        """Load a prompt template by relative file path."""
        file_path = self._base_dir / relative_path
        return self._load_from_file(file_path)

    def load_all(self) -> list[PromptTemplate]:
        """Load all prompt templates from the prompts directory."""
        templates = []
        for root, _, files in os.walk(self._base_dir):
            for fname in files:
                if fname.endswith((".txt", ".j2", ".jinja2", ".jinja")):
                    file_path = Path(root) / fname
                    template = self._load_from_file(file_path)
                    if template:
                        templates.append(template)
        return templates

    def list_prompts(self) -> list[dict]:
        """List all available prompt templates with metadata."""
        return [t.to_dict() for t in self.load_all()]

    def _load_by_id(self, prompt_id: str) -> PromptTemplate | None:
        """Resolve a prompt ID to a file path and load it."""
        parts = prompt_id.split("/")
        if len(parts) == 2:
            category, name = parts
            candidates = [
                self._base_dir / category / f"{name}.txt",
                self._base_dir / category / f"{name}.j2",
            ]
        else:
            name = parts[0]
            candidates = []
            for root, _, files in os.walk(self._base_dir):
                for fname in files:
                    stem = Path(fname).stem
                    if stem == name:
                        candidates.append(Path(root) / fname)

        for candidate in candidates:
            if candidate.exists():
                return self._load_from_file(candidate)

        logger.warning("prompt_not_found", prompt_id=prompt_id)
        return None

    def _load_from_file(self, file_path: Path) -> PromptTemplate | None:
        """Load and parse a prompt template file."""
        try:
            content = file_path.read_text(encoding="utf-8")
            metadata = self._parse_header(content)
            variables = self._extract_variables(content)
            clean_content = self._strip_header(content)

            prompt_id = metadata.get("prompt_id", file_path.stem)

            return PromptTemplate(
                prompt_id=prompt_id,
                version=metadata.get("version", "1.0.0"),
                model_id=metadata.get("model", ""),
                analysis_version=metadata.get("analysis_version", "1.0.0"),
                content=clean_content.strip(),
                file_path=str(file_path.relative_to(self._base_dir)),
                variables=variables,
            )
        except Exception as exc:
            logger.error("prompt_load_failed", path=str(file_path), error=str(exc))
            return None

    def _parse_header(self, content: str) -> dict:
        """Parse version metadata from file header comments."""
        metadata = {}
        for match in self.HEADER_PATTERN.finditer(content):
            key = match.group(1).strip()
            value = match.group(2).strip()
            if key == "prompt":
                metadata["prompt_id"] = value
            else:
                metadata[key] = value
        return metadata

    def _extract_variables(self, content: str) -> list[str]:
        """Extract {{variable}} names from template content."""
        return list(set(self.VARIABLE_PATTERN.findall(content)))

    def _strip_header(self, content: str) -> str:
        """Remove header comment lines from content."""
        lines = content.split("\n")
        result_lines = []
        in_header = True
        for line in lines:
            if in_header and (line.startswith("#") or line.strip() == ""):
                continue
            in_header = False
            result_lines.append(line)
        return "\n".join(result_lines)
