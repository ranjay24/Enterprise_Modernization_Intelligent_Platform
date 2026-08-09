from __future__ import annotations
import structlog
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

logger = structlog.get_logger(__name__)

@dataclass
class RuleViolation:
    rule_name: str
    severity: str  # 'error', 'warning', 'info'
    message: str
    service_name: str = ''
    class_name: str = ''

class BoundaryRule:
    name: str = ''
    severity: str = 'warning'
    
    def validate(self, services: list[dict], class_by_name: dict, **kwargs) -> list[RuleViolation]:
        return []

class SingleOwnershipRule(BoundaryRule):
    name = "SingleOwnershipRule"
    severity = "error"
    
    def validate(self, services: list[dict], class_by_name: dict, **kwargs) -> list[RuleViolation]:
        violations = []
        class_to_services = {}
        for svc in services:
            svc_name = svc.get('name', 'Unknown')
            for cls_name in svc.get('classes', []):
                class_to_services.setdefault(cls_name, []).append(svc_name)
                
        for cls_name, svc_names in class_to_services.items():
            if len(svc_names) > 1:
                violations.append(RuleViolation(
                    rule_name=self.name,
                    severity=self.severity,
                    message=f"Class {cls_name} belongs to multiple boundaries: {', '.join(svc_names)}",
                    class_name=cls_name
                ))
        return violations

class EntityOwnershipRule(BoundaryRule):
    name = "EntityOwnershipRule"
    severity = "error"
    
    def validate(self, services: list[dict], class_by_name: dict, **kwargs) -> list[RuleViolation]:
        violations = []
        entities = {name: cls for name, cls in class_by_name.items() if cls.get('is_entity', False)}
        
        class_to_services = {}
        for svc in services:
            svc_name = svc.get('name', 'Unknown')
            for cls_name in svc.get('classes', []):
                class_to_services.setdefault(cls_name, []).append(svc_name)
                
        for entity_name in entities:
            owners = class_to_services.get(entity_name, [])
            if len(owners) == 0:
                violations.append(RuleViolation(
                    rule_name=self.name,
                    severity=self.severity,
                    message=f"Entity {entity_name} does not belong to any boundary",
                    class_name=entity_name
                ))
        return violations

class NoOrphanEndpointsRule(BoundaryRule):
    name = "NoOrphanEndpointsRule"
    severity = "error"
    
    def validate(self, services: list[dict], class_by_name: dict, **kwargs) -> list[RuleViolation]:
        all_endpoints = kwargs.get('all_endpoints')
        if not all_endpoints:
            return []
            
        violations = []
        assigned_classes = set()
        for svc in services:
            assigned_classes.update(svc.get('classes', []))
            
        for endpoint in all_endpoints:
            handler_class = endpoint.get('handler_class')
            if handler_class and handler_class not in assigned_classes:
                violations.append(RuleViolation(
                    rule_name=self.name,
                    severity=self.severity,
                    message=f"Endpoint {endpoint.get('path')} handler class {handler_class} is not in any boundary",
                    class_name=handler_class
                ))
        return violations

class NoDuplicateServicesRule(BoundaryRule):
    name = "NoDuplicateServicesRule"
    severity = "error"
    
    def validate(self, services: list[dict], class_by_name: dict, **kwargs) -> list[RuleViolation]:
        violations = []
        seen = set()
        for svc in services:
            name = svc.get('name')
            if name in seen:
                violations.append(RuleViolation(
                    rule_name=self.name,
                    severity=self.severity,
                    message=f"Duplicate service boundary name: {name}",
                    service_name=name
                ))
            if name:
                seen.add(name)
        return violations

class DDDChainIntegrityRule(BoundaryRule):
    name = "DDDChainIntegrityRule"
    severity = "warning"
    
    def validate(self, services: list[dict], class_by_name: dict, **kwargs) -> list[RuleViolation]:
        violations = []
        for svc in services:
            svc_name = svc.get('name', 'Unknown')
            classes_in_boundary = set(svc.get('classes', []))
            has_controller = False
            for cls_name in classes_in_boundary:
                cls = class_by_name.get(cls_name, {})
                if cls.get('is_controller', False):
                    has_controller = True
                    break
                    
            if has_controller:
                has_service_or_repo = False
                for cls_name in classes_in_boundary:
                    cls = class_by_name.get(cls_name, {})
                    if cls.get('is_service', False) or cls.get('is_repository', False):
                        has_service_or_repo = True
                        break
                
                # Check injected fields of controllers (approximated by having a service/repo in the boundary)
                if not has_service_or_repo:
                    violations.append(RuleViolation(
                        rule_name=self.name,
                        severity=self.severity,
                        message=f"Boundary {svc_name} has a controller but no service or repository",
                        service_name=svc_name
                    ))
        return violations

class CompleteBoundaryRule(BoundaryRule):
    name = "CompleteBoundaryRule"
    severity = "warning"
    
    def validate(self, services: list[dict], class_by_name: dict, **kwargs) -> list[RuleViolation]:
        violations = []
        for svc in services:
            svc_name = svc.get('name', 'Unknown')
            if len(svc.get('classes', [])) < 2:
                violations.append(RuleViolation(
                    rule_name=self.name,
                    severity=self.severity,
                    message=f"Boundary {svc_name} is incomplete (has fewer than 2 classes)",
                    service_name=svc_name
                ))
        return violations

class BoundaryRuleEngine:
    def __init__(self):
        self.rules = [
            SingleOwnershipRule(), 
            EntityOwnershipRule(), 
            NoDuplicateServicesRule(), 
            DDDChainIntegrityRule(), 
            CompleteBoundaryRule(),
            NoOrphanEndpointsRule()
        ]
    
    def validate(self, services: list[dict], class_by_name: dict, all_endpoints: Optional[list[dict]] = None) -> list[RuleViolation]:
        violations = []
        for rule in self.rules:
            if isinstance(rule, NoOrphanEndpointsRule):
                if all_endpoints is not None:
                    violations.extend(rule.validate(services, class_by_name, all_endpoints=all_endpoints))
            else:
                violations.extend(rule.validate(services, class_by_name))
        return violations
    
    def would_violate(self, services: list[dict], class_by_name: dict, check_rules: Optional[list[str]] = None) -> bool:
        """Quick check if current state has errors (not warnings)."""
        violations = self.validate(services, class_by_name)
        return any(v.severity == 'error' for v in violations)
