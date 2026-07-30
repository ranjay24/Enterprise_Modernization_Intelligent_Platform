"""FastAPI dependency injection providers."""

from functools import lru_cache

from app.aws.clients import AWSClients
from app.core.settings import Settings, get_settings


@lru_cache
def get_aws_clients() -> AWSClients:
    """Provide cached AWS clients instance."""
    settings = get_settings()
    return AWSClients(settings=settings)


def get_settings_dependency() -> Settings:
    """Provide application settings."""
    return get_settings()
