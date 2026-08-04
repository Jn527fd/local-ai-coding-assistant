import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ROUTERS_DIR = REPO_ROOT / "backend" / "app" / "routers"
NGINX_CONFIG = REPO_ROOT / "frontend" / "nginx.conf"


def _backend_router_prefixes() -> set[str]:
    prefixes: set[str] = set()
    for router_file in ROUTERS_DIR.glob("*.py"):
        if router_file.name == "__init__.py":
            continue
        content = router_file.read_text(encoding="utf-8")
        prefixes.update(
            match.group(1).strip("/")
            for match in re.finditer(r'prefix\s*=\s*["\'](/[^"\']+)["\']', content)
        )
    return prefixes


def _proxied_direct_prefixes(nginx_config: str) -> set[str]:
    match = re.search(r"location\s+~\s+\^/\(([^)]+)\)\(/", nginx_config)
    assert match, "Nginx config is missing the direct backend proxy location."
    return {
        prefix.strip()
        for prefix in match.group(1).split("|")
        if prefix.strip() and prefix.strip() not in {"docs", "redoc", "openapi.json"}
    }


def test_docker_frontend_proxies_api_namespace() -> None:
    nginx_config = NGINX_CONFIG.read_text(encoding="utf-8")

    assert "location /api/" in nginx_config
    assert "rewrite ^/api/(.*)$ /$1 break;" in nginx_config
    assert "proxy_pass http://backend:8000;" in nginx_config


def test_docker_frontend_proxies_all_backend_router_prefixes() -> None:
    nginx_config = NGINX_CONFIG.read_text(encoding="utf-8")

    assert _proxied_direct_prefixes(nginx_config) == _backend_router_prefixes()


def test_docker_frontend_proxies_backend_docs_routes() -> None:
    nginx_config = NGINX_CONFIG.read_text(encoding="utf-8")

    assert "docs|redoc|openapi.json" in nginx_config
