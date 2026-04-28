from fastapi import FastAPI

from nhtsa_metadata import __version__
from nhtsa_metadata.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    effective_settings = settings or get_settings()
    app = FastAPI(title=effective_settings.app_name, version=__version__)
    app.state.settings = effective_settings

    @app.get("/api/health")
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "app": effective_settings.app_name,
            "environment": effective_settings.environment,
            "database_url_configured": bool(effective_settings.database_url),
        }

    return app
