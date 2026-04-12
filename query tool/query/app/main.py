import argparse
from pathlib import Path

from app.api.server import QueryServer
from app.core.config import settings
from app.core.tls import create_ssl_context
from app.services.orthanc_client import OrthancClient
from app.services.query_service import QueryService
from app.services.stats_service import collect_and_save_stats, start_periodic_collection


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the DICOM query HTTP service.")
    parser.add_argument("pacs_url", nargs="?", default=settings.pacs_url)
    parser.add_argument("--host", default=settings.host)
    parser.add_argument("--port", type=int, default=settings.port)
    parser.add_argument("--tls", action="store_true", default=settings.tls_enabled)
    parser.add_argument("--tls-cert", default=settings.tls_cert)
    parser.add_argument("--tls-key", default=settings.tls_key)
    parser.add_argument("--tls-ca", default=settings.tls_ca)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    orthanc = OrthancClient(args.pacs_url, auth=settings.auth)
    query_service = QueryService(orthanc)

    if settings.collect_stats_on_startup:
        collect_and_save_stats(query_service, settings.stats_file)
        start_periodic_collection(query_service, settings.stats_file)

    frontend_root = Path(__file__).resolve().parents[1] / "frontend"
    frontend_dir = frontend_root / "dist" if (frontend_root / "dist" / "index.html").is_file() else frontend_root
    server = QueryServer(query_service, frontend_dir).build(args.host, args.port)

    protocol = "http"
    if args.tls:
        context = create_ssl_context(args.tls_cert, args.tls_key, args.tls_ca or None)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        protocol = "https"

    print(f"DICOM query service listening on {protocol}://{args.host}:{args.port}")
    print(f"PACS URL: {args.pacs_url}")
    server.serve_forever()


if __name__ == "__main__":
    main()
