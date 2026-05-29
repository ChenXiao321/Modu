from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.exceptions import (
    ModuException,
    modu_exception_handler,
)
from app.models.base import Base, engine
from app.models.design_document import DesignDocument  # noqa: F401
from app.models.design_revision import DesignRevision  # noqa: F401
from app.models.document import Document  # noqa: F401
from app.models.parsed_requirement import ParsedRequirement  # noqa: F401
from app.models.review_comment import ReviewComment  # noqa: F401
from app.models.agent_workflow_run import AgentWorkflowRun  # noqa: F401
from app.models.fc_requirement_document import FcRequirementDocument  # noqa: F401
from app.models.safety_critical_parameter import SafetyCriticalParameter  # noqa: F401
from app.routers.v1 import documents

def create_app() -> FastAPI:
    app = FastAPI(title="Modu Backend", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(ModuException, modu_exception_handler)

    app.include_router(documents.router, prefix="/api/v1")

    @app.on_event("startup")
    def startup() -> None:
        Base.metadata.create_all(bind=engine)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
