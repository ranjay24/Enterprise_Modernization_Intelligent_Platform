"""Project builder — assembles deterministic scaffold services from Jinja2 templates.

Used as the fallback path for the Code Generation agent (project rule 10: always
have a fallback). Builds a complete, compilable Spring Boot project from a service
plan when Bedrock is unavailable or returns invalid output.
"""

from __future__ import annotations

import structlog
import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from app.codegen import models as codegen_models

logger = structlog.get_logger(__name__)

_TEMPLATES_DIR = Path(__file__).parent / "templates"

_DEFAULT_GLOBAL = {
    "java_version": "17",
    "spring_boot_version": "3.3.4",
    "maven_group_id": "com.emip",
    "base_package": "com.emip",
}


def _sanitize_identifier(value: str) -> str:
    """Convert a service id to a valid Java identifier."""
    value = value.replace("-", "_").replace(".", "_")
    return "".join(ch for ch in value if ch.isalnum() or ch == "_") or "Service"


def _camel(value: str) -> str:
    parts = _sanitize_identifier(value).split("_")
    return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])


def _pascal(value: str) -> str:
    return "".join(p.capitalize() for p in _sanitize_identifier(value).split("_"))


def _method_name(value: str) -> str:
    """camelCase for Java method names, splitting words and preserving interior capitals."""
    parts = [p for p in _sanitize_identifier(value).split("_") if p]
    words: list[str] = []
    for part in parts:
        words.extend(w for w in re.split(r"(?<=[a-z0-9])(?=[A-Z])", part) if w)
    first = words[0][0].upper() + words[0][1:] if words else "Handle"
    return first + "".join(w[0].upper() + w[1:] for w in words[1:])


def _env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )
    env.filters["sanitize"] = _sanitize_identifier
    env.filters["camel"] = _camel
    env.filters["pascal"] = _pascal
    env.filters["method"] = _method_name
    return env


def build_scaffold_service(service_plan: dict, global_config: dict | None = None) -> dict:
    """Build a deterministic Spring Boot project from a service plan entry.

    Returns a normalized service_code dict (see codegen/models.normalize_service_code).
    """
    gc = {**_DEFAULT_GLOBAL, **(global_config or {})}
    service_id = codegen_models.normalize_service_id(service_plan, "service")
    base_package = str(service_plan.get("package") or f"{gc['base_package']}.{_camel(service_id)}")
    broker_role = codegen_models.broker_role_of(service_plan)

    resilience = service_plan.get("resilience", {})
    if isinstance(resilience, list):
        resilience = {}

    database = service_plan.get("database", {}) or {}
    database_name = str(database.get("name") or f"{_camel(service_id)}_db")
    tables = database.get("tables") or [f"{_camel(service_id)}_table"]

    main_class = f"{_pascal(service_id)}Application"
    controller_class = f"{_pascal(service_id)}Controller"
    service_class = f"{_pascal(service_id)}Service"
    repository_class = f"{_pascal(service_id)}Repository"
    entity_class = f"{_pascal(service_id)}Entity"
    dto_class = f"{_pascal(service_id)}Dto"
    service_var = _camel(service_id) + "Service"
    resource_path = _camel(service_id) + "s"

    feign_clients = [f for f in codegen_models._as_list(service_plan.get("feign_clients")) if isinstance(f, dict)]
    events = service_plan.get("events", {}) or {}
    publish_topics = [e.get("topic") for e in codegen_models._as_list(events.get("publishes")) if e.get("topic")]
    subscribe_queues = [e.get("queue") for e in codegen_models._as_list(events.get("subscribes")) if e.get("queue")]

    server_port = service_plan.get("server_port", 8081)
    if isinstance(server_port, str) and server_port.isdigit():
        server_port = int(server_port)

    context = {
        "service_id": service_id,
        "base_package": base_package,
        "main_class": main_class,
        "controller_class": controller_class,
        "service_class": service_class,
        "repository_class": repository_class,
        "entity_class": entity_class,
        "dto_class": dto_class,
        "service_var": service_var,
        "resource_path": resource_path,
        "table_name": tables[0] if tables else "resource",
        "base_path": f"/{resource_path}",
        "server_port": server_port,
        "java_version": gc["java_version"],
        "spring_boot_version": gc["spring_boot_version"],
        "maven_group_id": gc["maven_group_id"],
        "uses_kafka": broker_role in ("kafka", "both"),
        "uses_rabbitmq": broker_role in ("rabbitmq", "both"),
        "feign_clients": feign_clients,
        "publish_topics": publish_topics,
        "subscribe_queues": subscribe_queues,
        "database_name": database_name,
        "retry": resilience.get("retry", {"max_attempts": 3, "backoff_ms": 500}),
        "circuit_breaker": resilience.get("circuit_breaker", {"failure_rate_threshold": 50, "wait_duration_seconds": 10}),
        "rate_limiter": resilience.get("rate_limiter", {"limit_for_period": 100, "limit_refresh_period_seconds": 1}),
        "time_limiter": resilience.get("time_limiter", {"timeout_duration_seconds": 3}),
        "bulkhead": resilience.get("bulkhead", {"max_concurrent_calls": 20}),
    }

    env = _env()
    files: list[dict] = []

    def add(template_name: str, path: str, **extra):
        try:
            content = env.get_template(template_name).render(**context, **extra)
        except Exception as exc:
            logger.warning("scaffold_template_failed", template=template_name, error=str(exc))
            content = f"// template {template_name} failed: {exc}"
        files.append({"path": path, "content": content})

    add("pom.xml.j2", "pom.xml")
    add("application.yml.j2", "src/main/resources/application.yml")
    add("resilience4j.yml.j2", "src/main/resources/resilience4j.yml")
    add("dockerfile.j2", "Dockerfile")
    add("openapi.yaml.j2", "openapi.yaml")

    pkg_dir = f"src/main/java/{base_package.replace('.', '/')}"
    add("main_application.java.j2", f"{pkg_dir}/{main_class}.java")
    add("controller.java.j2", f"{pkg_dir}/web/{controller_class}.java")
    add("service.java.j2", f"{pkg_dir}/service/{service_class}.java")
    add("repository.java.j2", f"{pkg_dir}/repository/{repository_class}.java")
    add("entity.java.j2", f"{pkg_dir}/domain/{entity_class}.java")
    add("dto.java.j2", f"{pkg_dir}/web/dto/{dto_class}.java")

    for client in feign_clients:
        client_name = _pascal(str(client.get("name") or "RemoteClient"))
        target_service = str(client.get("target_service") or service_id)
        target_port = client.get("target_port") or 8081
        add(
            "feign_client.java.j2",
            f"{pkg_dir}/client/{client_name}.java",
            client_name=client_name,
            client_class=client_name,
            target_service=target_service,
            feign_url="${{{}.url:http://{}:{}}}".format(client_name, target_service, target_port),
        )

    if context["uses_kafka"]:
        kafka_class = f"{_pascal(service_id)}KafkaEventListener"
        add(
            "kafka_listener.java.j2",
            f"{pkg_dir}/messaging/{kafka_class}.java",
            event_listener_class=kafka_class,
        )
    if context["uses_rabbitmq"]:
        rabbit_class = f"{_pascal(service_id)}RabbitEventListener"
        add(
            "rabbit_listener.java.j2",
            f"{pkg_dir}/messaging/{rabbit_class}.java",
            event_listener_class=rabbit_class,
        )

    add("smoke_test.java.j2", f"src/test/java/{base_package.replace('.', '/')}/SmokeTest.java")

    return {
        "service_id": service_id,
        "base_package": base_package,
        "language": "java",
        "build_tool": "maven",
        "files": files,
        "compilation_notes": "Scaffold service built from templates (deterministic fallback)",
        "deployment_notes": f"Runs on port {server_port} behind the gateway",
    }
