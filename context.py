"""Handles global context in a more type-safe way than using globals."""

import dataclasses
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from providers import ImageProvider
    from preprocessors import Preprocessor


@dataclasses.dataclass
class AppContext:
    provider: "ImageProvider"
    preprocessor: type["Preprocessor"]
    exporter: "Exporter"
    config: dict[str, Any]

    last_image_raw: bytes | None = None
    last_image_processed: bytes | None = None
    last_rotation: int = 0
    
_app_context: AppContext | None = None

def get_app_context() -> AppContext:
    global _app_context
    if _app_context is None:
        raise RuntimeError("App context not initialized")
    return _app_context

def set_app_context(context: AppContext):
    global _app_context
    _app_context = context
