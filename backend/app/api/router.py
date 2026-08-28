from typing import Dict

import importlib
import logging
from fastapi import APIRouter

logger = logging.getLogger(__name__)

FEATURE_ROUTER_MODULE_PATHS: Dict[str, str] = {
    "users": "app.users.router",
    "folders": "app.folders.router",
    "documents": "app.documents.router",
    "retrieval": "app.retrieval.router",
    "search": "app.retrieval.search_router",
    "chat": "app.chat.router",
    "insights": "app.insights.router",
    "notes": "app.notes.router",
}

api_router: APIRouter = APIRouter(prefix="/api/v1")

# Attempt to dynamically import and include available feature routers.
# Missing feature modules will be skipped to preserve application stability
# during incremental implementation phases.
for feature_name, module_path in FEATURE_ROUTER_MODULE_PATHS.items():
    # try:
    #     module = importlib.import_module(module_path)
    #     # Expect the feature router object to be named `router` inside the module
    #     feature_router = getattr(module, "router", None)
    #     if feature_router is not None:
    #         api_router.include_router(feature_router)
    #         logger.info("Included router for feature '%s' from %s", feature_name, module_path)
    # except Exception as exc:  # pragma: no cover - runtime import guard
    #     logger.debug("Feature router %s not available: %s", module_path, exc)

    module = importlib.import_module(module_path)
    feature_router = getattr(module, "router", None)
    if feature_router is not None:
        api_router.include_router(feature_router)