import json
import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "openapi"
DOCS.mkdir(parents=True, exist_ok=True)


def load_app(module_name: str, service_root: Path, main_py: Path):
    sys.path.insert(0, str(service_root))
    spec = importlib.util.spec_from_file_location(module_name, main_py)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from {main_py}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.path.pop(0)
    return module.app


def export_gateway() -> None:
    app = load_app(
        "api_gateway_main",
        ROOT / "api-gateway",
        ROOT / "api-gateway" / "app" / "main.py",
    )
    spec = app.openapi()
    (DOCS / "api-gateway.openapi.json").write_text(
        json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def export_core() -> None:
    app = load_app(
        "assistant_core_main",
        ROOT / "assistant-core",
        ROOT / "assistant-core" / "app" / "main.py",
    )
    spec = app.openapi()
    (DOCS / "assistant-core.openapi.json").write_text(
        json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> None:
    export_gateway()
    export_core()
    print("OpenAPI specs exported to docs/openapi")


if __name__ == "__main__":
    main()
