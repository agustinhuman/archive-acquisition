import sys
import tomllib
from pathlib import Path
from typing import Any

import uvicorn

from context import AppContext, set_app_context
from exporters import FolderExporter
from preprocessors import ExtractDocument
from providers import Phone
from webapp import app

DEBUG = False

def read_conf() -> dict[str, Any]:
    if len(sys.argv) < 2:
        conf_file = "conf.toml"
    else:
        conf_file = sys.argv[1]
    with open(conf_file, "rb") as f:
        return tomllib.load(f)


if __name__ == '__main__':

    raw_conf = read_conf()

    provider = Phone(
        raw_conf,
        mock_photo=Path("photo.jpg") if DEBUG else None
    )

    preprocessor = ExtractDocument
    exporter = FolderExporter(raw_conf)

    context = AppContext(config=raw_conf, provider=provider, preprocessor=preprocessor, exporter=exporter)
    set_app_context(context)
    uvicorn.run(app, host="0.0.0.0", port=5000, reload=False, log_level="debug",
                workers=1)
