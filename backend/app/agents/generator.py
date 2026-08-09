"""Code Generation agent — generates a full Spring Boot service via Bedrock.

Each file is generated in its own Bedrock call so responses stay well under the
model's output-token budget (a whole-service JSON response truncates and is
rejected by the AI engine's validator). The deterministic scaffold provides the
authoritative file manifest and the per-file fallback, so the assembled service
is always complete and compilable even when a Bedrock call fails.
"""

from __future__ import annotations

import json
import re
import structlog
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.agents.base import Agent
from app.codegen import models as codegen_models
from app.codegen.project_builder import build_scaffold_service
from app.core.settings import get_settings

logger = structlog.get_logger(__name__)

_TYPE_DECL = re.compile(
    r"\b(?:public\s+|protected\s+|final\s+|abstract\s+)*(class|interface|enum|record)\s+([A-Za-z_]\w*)"
)
_PACKAGE_DECL = re.compile(r"^\s*package\s+([\w.]+)\s*;", re.MULTILINE)
_IMPORT_DECL = re.compile(r"import\s+(?:static\s+)?([\w.*]+)\s*;")


class CodeGenerationAgent(Agent):
    """Generates one complete Maven + Spring Boot 3 + Java 17 microservice."""

    agent_id = "code_generation"
    definition_file = "codeGenerationAgent.md"
    prompt_id = "codegen/code_generator"
    file_prompt_id = "codegen/code_generator_file"
    output_artifact = "service_code"
    model_role = "codegen"
    expected_fields = ["files"]

    @staticmethod
    def _is_complete_service(code: dict) -> bool:
        """True when the generated code is a structurally complete service.

        Mirrors ReviewAgent.fallback_review: at least one Java source under
        src/main/java, a pom.xml, an application config, and — when an entity
        exists — a matching repository. Incomplete output (e.g. Bedrock
        truncation) must not be persisted as a finished service; the scaffold
        fallback guarantees a compilable project.
        """
        paths = {str(f.get("path", "")) for f in code.get("files", [])}
        has_java = any(p.startswith("src/main/java") and p.endswith(".java") for p in paths)
        if not has_java:
            return False
        has_pom = any(p.endswith("pom.xml") for p in paths)
        has_config = any(p.endswith("application.yml") or p.endswith("application.yaml") for p in paths)
        if not (has_pom and has_config):
            return False
        has_entity = any("domain/" in p.lower() and p.endswith(".java") for p in paths)
        has_repository = any("repository/" in p.lower() and p.endswith(".java") for p in paths)
        if has_entity and not has_repository:
            return False
        return True

    @staticmethod
    def _declared_type(content: str) -> tuple[str, str] | None:
        """Return (kind, name) of the first top-level type declared in a file."""
        m = _TYPE_DECL.search(content or "")
        if m:
            return m.group(1), m.group(2)
        return None

    @staticmethod
    def _package_of(content: str) -> str:
        m = _PACKAGE_DECL.search(content or "")
        return m.group(1) if m else ""

    def _build_shared_types_manifest(self, scaffold: dict) -> dict:
        """Canonical type manifest for the service.

        Derived from the deterministic scaffold so every per-file prompt sees the
        exact class names/packages the final project must use. Files are generated
        independently, so without this the model invents divergent names per file
        (e.g. entity vs repository/generic parameter mismatch) and the project
        fails to compile.
        """
        types: list[dict] = []
        for f in scaffold.get("files", []):
            path = str(f.get("path", ""))
            if not path.endswith(".java"):
                continue
            declared = self._declared_type(f.get("content", ""))
            if not declared:
                continue
            kind, name = declared
            types.append(
                {
                    "name": name,
                    "kind": kind,
                    "package": self._package_of(f.get("content", "")),
                    "path": path,
                }
            )
        types.sort(key=lambda t: t["path"])
        return {"base_package": scaffold.get("base_package", "com.emip"), "types": types}

    @staticmethod
    def _inconsistent_file_paths(files: list[dict], base_package: str) -> set[str]:
        """Paths whose imports reference a type not declared by any file.

        Cross-file name drift (the per-file generation failure mode) produces
        imports like `com.emip.order.entity.Order` for a type that is never
        generated. Such a project cannot compile, so those files must fall back
        to the deterministic scaffold.
        """
        declared: dict[str, str] = {}
        for f in files:
            m = _TYPE_DECL.search(f.get("content", ""))
            if m:
                declared.setdefault(m.group(2), str(f.get("path", "")))

        bad: set[str] = set()
        for f in files:
            content = f.get("content", "")
            for imp in _IMPORT_DECL.finditer(content):
                full = imp.group(1)
                if not (full == base_package or full.startswith(base_package + ".")):
                    continue
                simple = full.rsplit(".", 1)[-1]
                if simple == "*":
                    continue
                if simple not in declared:
                    bad.add(str(f.get("path", "")))
        return bad

    def model_id(self) -> str:
        """Code generation uses the dedicated codegen model."""
        settings = get_settings()
        return settings.bedrock_model_codegen

    def build_template_variables(
        self,
        service_plan: dict,
        source_boundary: dict,
        analysis_data: dict,
        regeneration_context: dict | None = None,
    ) -> dict:
        from app.ai.service import _compact_json

        settings = get_settings()
        return {
            "definition": self.load_definition_text(),
            "service_plan_json": _compact_json(service_plan, settings.ai_prompt_max_tokens),
            "source_boundary_json": _compact_json(source_boundary, settings.ai_prompt_max_tokens),
            "analysis_context_json": _compact_json(analysis_data, settings.ai_prompt_max_tokens),
            "regeneration_context_json": _compact_json(regeneration_context or {}, settings.ai_prompt_max_tokens),
        }

    def _build_file_template_variables(
        self,
        service_plan: dict,
        source_boundary: dict,
        analysis_data: dict,
        regeneration_context: dict | None,
        file_path: str,
        file_description: str,
        shared_types_json: str,
    ) -> dict:
        from app.ai.service import _compact_json

        settings = get_settings()
        return {
            "definition": self.load_definition_text(),
            "service_plan_json": _compact_json(service_plan, settings.ai_prompt_max_tokens),
            "source_boundary_json": _compact_json(source_boundary, settings.ai_prompt_max_tokens),
            "analysis_context_json": _compact_json(analysis_data, settings.ai_prompt_max_tokens),
            "regeneration_context_json": _compact_json(regeneration_context or {}, settings.ai_prompt_max_tokens),
            "file_path": file_path,
            "file_description": file_description,
            "shared_types_json": shared_types_json,
        }

    @staticmethod
    def _file_description(path: str) -> str:
        """Short human-readable purpose for a scaffold file path."""
        if path.endswith("pom.xml"):
            return "Maven build config: Spring Boot 3.3.4 parent, Java 17, and every dependency referenced by the code"
        if path.endswith("application.yml") or path.endswith("application.yaml"):
            return "Spring Boot application.yml: server port, app name, datasource, eureka/config server URLs, messaging settings, actuator"
        if path.endswith("resilience4j.yml"):
            return "Resilience4j tuning: retry, circuit breaker, rate limiter, time limiter, bulkhead"
        if path.endswith("Dockerfile"):
            return "Multi-stage Dockerfile: maven build stage + eclipse-temurin:17-jre runtime"
        if path.endswith("openapi.yaml"):
            return "OpenAPI 3.0 spec of the service's exposed endpoints"
        if path.endswith("SmokeTest.java"):
            return "One context-load unit test using H2 with brokers disabled"
        if "client/" in path:
            return "Feign client interface with @FeignClient and a @CircuitBreaker fallback method"
        if "messaging/" in path:
            return "Kafka or RabbitMQ event listener for the service's subscribed topics/queues"
        if "web/dto/" in path:
            return "Request/response DTO with javax/jakarta validation annotations"
        if "domain/" in path:
            return "JPA entity mapped to the service's table"
        if "repository/" in path:
            return "Spring Data JpaRepository for the entity"
        if "service/" in path:
            return "Spring @Service with the business logic and Resilience4j annotations"
        if "web/" in path:
            return "Spring @RestController exposing the service's endpoints"
        if path.endswith("Application.java"):
            return "Main @SpringBootApplication class (with @EnableFeignClients when feign clients exist)"
        return "Source file for the service"

    def _generate_one_file(
        self,
        file_path: str,
        file_description: str,
        service_plan: dict,
        source_boundary: dict,
        analysis_data: dict,
        regeneration_context: dict | None,
        scaffold_content: str,
        shared_types_json: str,
        job_id: str,
    ) -> tuple[dict, bool]:
        """Generate a single file via Bedrock; fall back to the scaffold file.

        Returns (file_dict, used_scaffold) — used_scaffold is True when the
        scaffold content was kept (AI returned invalid/empty output).
        """
        template_vars = self._build_file_template_variables(
            service_plan, source_boundary, analysis_data, regeneration_context, file_path, file_description,
            shared_types_json,
        )

        def _scaffold_fallback():
            return {"path": file_path, "content": scaffold_content}

        result, metadata, used_ai = self.invoke(
            template_variables=template_vars,
            fallback_fn=_scaffold_fallback,
            job_id=job_id,
            model_id=self.model_id(),
            expected_fields=["path", "content"],
            prompt_id=self.file_prompt_id,
        )
        if isinstance(result, dict):
            content = result.get("content")
            if isinstance(content, str) and content.strip():
                # The engine's fallback path returns the exact scaffold content;
                # treat it as a scaffold file even though it passed validation.
                used_scaffold = (not used_ai) or (content == scaffold_content)
                return {"path": file_path, "content": content}, used_scaffold
            logger.warning("codegen_file_empty_using_scaffold", path=file_path)
        else:
            logger.warning("codegen_file_invalid_using_scaffold", path=file_path)
        return {"path": file_path, "content": scaffold_content}, True

    def _generate_files(
        self,
        service_plan: dict,
        source_boundary: dict,
        analysis_data: dict,
        regeneration_context: dict | None,
        job_id: str,
    ) -> tuple[list[dict], dict, bool]:
        """Generate every file of a service (parallel Bedrock calls).

        Returns (files, aggregated_metadata, used_ai). The scaffold manifest is
        authoritative so the assembled file set is always complete; each file's
        content is AI-generated when Bedrock succeeds and scaffold otherwise.
        """
        scaffold = build_scaffold_service(service_plan)
        scaffold_map = {f["path"]: f["content"] for f in scaffold["files"]}
        paths = list(scaffold_map.keys())
        shared_types_json = json.dumps(self._build_shared_types_manifest(scaffold), sort_keys=True)

        files_by_path: dict[str, dict] = {}
        origins: dict[str, bool] = {}
        aggregated: dict = {"model_id": self.model_id()}

        workers = min(max(get_settings().codegen_parallel_files, 1), len(paths) or 1)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    self._generate_one_file,
                    path,
                    self._file_description(path),
                    service_plan,
                    source_boundary,
                    analysis_data,
                    regeneration_context,
                    scaffold_map[path],
                    shared_types_json,
                    job_id,
                ): path
                for path in paths
            }
            for future in as_completed(futures):
                path = futures[future]
                try:
                    file_dict, used_scaffold = future.result()
                except Exception as exc:
                    logger.warning("codegen_file_generation_failed", path=path, error=str(exc))
                    file_dict, used_scaffold = {"path": path, "content": scaffold_map[path]}, True
                files_by_path[path] = file_dict
                origins[path] = used_scaffold

        # Consistency gate: drop any file whose intra-service imports reference a
        # type no generated file declares (cross-file name drift => won't compile).
        bad = self._inconsistent_file_paths([files_by_path[p] for p in paths], scaffold.get("base_package", ""))
        for path in bad:
            logger.warning("codegen_inconsistent_imports_using_scaffold", path=path)
            files_by_path[path] = {"path": path, "content": scaffold_map[path]}
            origins[path] = True

        ai_files = sum(1 for p in paths if not origins[p])
        scaffold_files = sum(1 for p in paths if origins[p])
        files = [files_by_path[p] for p in paths]
        aggregated["files_total"] = len(files)
        aggregated["files_ai"] = ai_files
        aggregated["files_scaffold"] = scaffold_files
        aggregated["used_fallback"] = scaffold_files > 0
        return files, aggregated, ai_files > 0

    def run(
        self,
        service_plan: dict,
        source_boundary: dict,
        analysis_data: dict,
        regeneration_context: dict | None = None,
        job_id: str = "",
    ) -> tuple[dict, dict, bool]:
        service_id = codegen_models.normalize_service_id(service_plan, "service")
        files, metadata, used_ai = self._generate_files(
            service_plan, source_boundary, analysis_data, regeneration_context, job_id
        )
        scaffold = build_scaffold_service(service_plan)
        code = codegen_models.normalize_service_code(
            {
                "service_id": service_id,
                "base_package": scaffold["base_package"],
                "language": "java",
                "build_tool": "maven",
                "files": files,
                "compilation_notes": (
                    f"AI-generated per-file with scaffold fallback "
                    f"({metadata['files_ai']} AI / {metadata['files_scaffold']} scaffold files)"
                ),
                "deployment_notes": scaffold["deployment_notes"],
            }
        )
        if not self._is_complete_service(code) or self._inconsistent_file_paths(
            code.get("files", []), code.get("base_package", "")
        ):
            logger.warning(
                "codegen_incomplete_using_scaffold",
                service_id=service_id,
                generated_files=len(code.get("files", [])),
            )
            code = codegen_models.normalize_service_code(build_scaffold_service(service_plan))
            metadata["used_fallback"] = True
        return code, metadata, used_ai
