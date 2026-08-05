from __future__ import annotations
from dataclasses import dataclass
import structlog
from typing import Iterator

logger = structlog.get_logger(__name__)

@dataclass
class ArchitectureSmell:
    name: str
    severity: str  # 'critical', 'warning', 'info'
    class_name: str
    evidence: str
    mitigation: str

def _detect_controller_repo_access(classes: list[dict]) -> Iterator[ArchitectureSmell]:
    for cls in classes:
        if cls.get('is_controller'):
            injected_fields = cls.get('injected_fields', [])
            if any(f.endswith('Repository') for f in injected_fields):
                yield ArchitectureSmell(
                    name='controller_repo_access',
                    severity='warning',
                    class_name=cls.get('name', ''),
                    evidence='Direct access to repository from controller',
                    mitigation='Introduce a service layer'
                )

def _detect_controller_entity_access(classes: list[dict]) -> Iterator[ArchitectureSmell]:
    entities = {cls.get('name') for cls in classes if cls.get('is_entity')}
    for cls in classes:
        if cls.get('is_controller'):
            dependencies = cls.get('dependencies', [])
            if any(dep in entities for dep in dependencies):
                yield ArchitectureSmell(
                    name='controller_entity_access',
                    severity='info',
                    class_name=cls.get('name', ''),
                    evidence='Entity used directly in controller',
                    mitigation='Use DTOs instead of entities in controllers'
                )

def _detect_cross_domain_coupling(classes: list[dict], boundaries: list[dict]) -> Iterator[ArchitectureSmell]:
    class_to_domain = {}
    for b in boundaries:
        for c_name in b.get('classes', []):
            class_to_domain[c_name] = b.get('name')
            
    for cls in classes:
        if cls.get('is_controller'):
            dependencies = cls.get('dependencies', [])
            referenced_domains = set()
            for dep in dependencies:
                domain = class_to_domain.get(dep)
                if domain:
                    referenced_domains.add(domain)
            
            if len(referenced_domains) >= 3:
                yield ArchitectureSmell(
                    name='cross_domain_coupling',
                    severity='critical',
                    class_name=cls.get('name', ''),
                    evidence=f'References domains: {", ".join(referenced_domains)}',
                    mitigation='Split controller into domain-specific controllers'
                )

def _detect_shared_repo_across_domains(classes: list[dict], boundaries: list[dict]) -> Iterator[ArchitectureSmell]:
    repo_to_domains = {}
    for b in boundaries:
        domain_name = b.get('name')
        for c_name in b.get('classes', []):
            if c_name.endswith('Repository'):
                repo_to_domains.setdefault(c_name, set()).add(domain_name)
                
    for repo, domains in repo_to_domains.items():
        if len(domains) > 1:
            yield ArchitectureSmell(
                name='shared_repo_across_domains',
                severity='warning',
                class_name=repo,
                evidence=f'Repository shared across domains: {", ".join(domains)}',
                mitigation='Duplicate repository per domain or extract shared data service'
            )

def _detect_controller_business_logic(classes: list[dict]) -> Iterator[ArchitectureSmell]:
    for cls in classes:
        if cls.get('is_controller'):
            method_count = cls.get('method_count', 0)
            lines_of_code = cls.get('lines_of_code', 0)
            if method_count > 10 and lines_of_code > 150:
                yield ArchitectureSmell(
                    name='controller_business_logic',
                    severity='warning',
                    class_name=cls.get('name', ''),
                    evidence=f'Methods: {method_count}, LOC: {lines_of_code}',
                    mitigation='Extract business logic to service layer'
                )

def detect_architecture_smells(classes: list[dict], boundaries: list[dict]) -> list[ArchitectureSmell]:
    smells = []
    smells.extend(_detect_controller_repo_access(classes))
    smells.extend(_detect_controller_entity_access(classes))
    smells.extend(_detect_cross_domain_coupling(classes, boundaries))
    smells.extend(_detect_shared_repo_across_domains(classes, boundaries))
    smells.extend(_detect_controller_business_logic(classes))
    return smells
