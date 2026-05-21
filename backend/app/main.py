from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from app.api.routes.upload_routes       import router as upload_router
from app.api.routes.github_routes       import router as github_router
from app.api.routes.repo_routes         import router as repo_router
from app.api.routes.retrieval_routes    import router as retrieval_router
from app.api.routes.agent_routes        import router as agent_router
from app.api.routes.intelligence_routes import router as intelligence_router
from app.api.routes.graph_rca_routes    import router as graph_rca_router
from app.api.routes.ingest_routes       import router as ingest_router
from app.api.routes.ingest_code_routes  import router as ingest_code_router
from app.api.routes.fix_routes          import router as fix_router      # NEW

from app.services.persistence_service import load_graph_memory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SentriX starting up...")
    loaded = load_graph_memory()
    if loaded:
        logger.info("Repository graph restored from disk — ready.")
    else:
        logger.info(
            "No persisted graph found. "
            "Call POST /api/ingest-code or /api/ingest-repo to load a repository."
        )
    yield
    logger.info("SentriX shutting down.")


app = FastAPI(
    title="SentriX — Cognitive Software Failure Intelligence",
    description=(
        "Graph-grounded semantic cognition platform for "
        "autonomous root cause analysis and repair."
    ),
    version="2.0.0",
    lifespan=lifespan,
)


@app.get("/")
def home():
    return {
        "system":    "SentriX",
        "version":   "2.0.0",
        "status":    "running",
        "docs":      "/docs",
        "endpoints": {
            "status":       "GET  /api/status",
            "ingest_code":  "POST /api/ingest-code",
            "ingest_repo":  "POST /api/ingest-repo",
            "rca":          "POST /api/rca",
            "graph_rca":    "POST /api/graph-rca",
            "fix":          "POST /api/fix",           # NEW
            "fix_and_rca":  "POST /api/fix-and-rca",   # NEW
        }
    }


app.include_router(upload_router,        prefix="/api")
app.include_router(github_router,        prefix="/api")
app.include_router(repo_router,          prefix="/api")
app.include_router(retrieval_router,     prefix="/api")
app.include_router(agent_router,         prefix="/api")
app.include_router(intelligence_router,  prefix="/api")
app.include_router(graph_rca_router,     prefix="/api")
app.include_router(ingest_router,        prefix="/api")
app.include_router(ingest_code_router,   prefix="/api")
app.include_router(fix_router,           prefix="/api")   # NEW