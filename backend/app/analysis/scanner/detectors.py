"""Build tool and framework detectors."""

from __future__ import annotations

import os
import re


def detect_build_tool(path: str) -> str:
    if os.path.exists(os.path.join(path, "pom.xml")):
        return "maven"
    if os.path.exists(os.path.join(path, "build.gradle")) or os.path.exists(os.path.join(path, "build.gradle.kts")):
        return "gradle"
    if os.path.exists(os.path.join(path, "build.xml")):
        return "ant"
    return "unknown"


def detect_java_version(path: str) -> str:
    pom = os.path.join(path, "pom.xml")
    if os.path.exists(pom):
        try:
            content = open(pom, "r", encoding="utf-8", errors="ignore").read()
            m = re.search(r"<java\.version>([\d.]+)</java\.version>", content)
            if m:
                return m.group(1)
            m = re.search(r"<maven\.compiler\.source>([\d.]+)</maven\.compiler\.source>", content)
            if m:
                return m.group(1)
        except Exception:
            pass
    gradle = os.path.join(path, "build.gradle")
    if os.path.exists(gradle):
        try:
            content = open(gradle, "r", encoding="utf-8", errors="ignore").read()
            m = re.search(r"sourceCompatibility\s*=\s*['\"]?(\d+)", content)
            if m:
                return m.group(1)
        except Exception:
            pass
    return "unknown"


def detect_spring_boot_version(path: str) -> str:
    pom = os.path.join(path, "pom.xml")
    if os.path.exists(pom):
        try:
            content = open(pom, "r", encoding="utf-8", errors="ignore").read()
            m = re.search(r"<spring-boot\.version>([\d.]+)</spring-boot\.version>", content)
            if m:
                return m.group(1)
            m = re.search(r"<parent>.*?<artifactId>spring-boot-starter-parent</artifactId>.*?<version>([\d.]+)</version>.*?</parent>", content, re.DOTALL)
            if m:
                return m.group(1)
        except Exception:
            pass
    return "unknown"


def detect_modules(path: str, build_tool: str) -> list[str]:
    modules = []
    if build_tool == "maven":
        pom = os.path.join(path, "pom.xml")
        if os.path.exists(pom):
            try:
                content = open(pom, "r", encoding="utf-8", errors="ignore").read()
                for m in re.finditer(r"<module>(.*?)</module>", content):
                    modules.append(m.group(1))
            except Exception:
                pass
    elif build_tool == "gradle":
        settings = os.path.join(path, "settings.gradle")
        if os.path.exists(settings):
            try:
                content = open(settings, "r", encoding="utf-8", errors="ignore").read()
                for m in re.finditer(r"include\s+['\"](.+?)['\"]", content):
                    modules.append(m.group(1))
            except Exception:
                pass
    return modules


def find_config_files(path: str) -> list[str]:
    config_extensions = {".yml", ".yaml", ".properties", ".xml", ".json", ".conf"}
    config_names = {"application.yml", "application.yaml", "application.properties", "bootstrap.yml", "logback.xml", "log4j2.xml"}
    found = []
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            if f in config_names or os.path.splitext(f)[1] in config_extensions:
                if "/test/" not in dirpath and "\\test\\" not in dirpath:
                    found.append(os.path.relpath(os.path.join(dirpath, f), path))
    return found[:100]
