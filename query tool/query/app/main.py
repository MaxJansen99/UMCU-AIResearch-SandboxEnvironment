import argparse
from pathlib import Path

from app.api.server import QueryServer
from app.core.config import settings
from app.core.tls import create_ssl_context
from app.repositories.exports_repository import ExportsRepository
from app.repositories.requests_repository import RequestsRepository
from app.repositories.users_repository import UsersRepository
from app.services.auth import AuthService
from app.services.csv_data_source import CsvDataSource
from app.services.database import Database
from app.services.export_service import ExportService
from app.services.fallback_data_source import FallbackDataSource
from app.services.orthanc_client import OrthancClient
from app.services.query_service import QueryService
from app.services.request_workflow import RequestWorkflowService
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
    orthanc = OrthancClient(args.pacs_url, auth=settings.auth) if args.pacs_url else None
    query_data_source = build_query_data_source(orthanc)
    query_service = QueryService(query_data_source)
    database = Database(settings.db_connection_info)
    database.initialize()
    users_repository = UsersRepository()
    requests_repository = RequestsRepository()
    exports_repository = ExportsRepository()
    auth_service = AuthService(database, users_repository)
    export_service = ExportService(database, settings.approved_export_root, orthanc, exports_repository)
    request_workflow = RequestWorkflowService(
        database,
        orthanc,
        export_service,
        requests_repository,
        exports_repository,
    )

    if settings.collect_stats_on_startup:
        collect_and_save_stats(query_service, settings.stats_file)
        start_periodic_collection(query_service, settings.stats_file)

    frontend_root = Path(__file__).resolve().parents[1] / "frontend"
    frontend_dir = frontend_root / "dist" if (frontend_root / "dist" / "index.html").is_file() else frontend_root
    server = QueryServer(query_service, frontend_dir, database, auth_service, request_workflow).build(args.host, args.port)

    protocol = "http"
    if args.tls:
        context = create_ssl_context(args.tls_cert, args.tls_key, args.tls_ca or None)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        protocol = "https"

    print(f"DICOM query service listening on {protocol}://{args.host}:{args.port}")
    print(f"Query data source: {settings.data_source}")
    print(f"PACS URL: {args.pacs_url or '<not configured>'}")
    if settings.csv_file:
        print(f"CSV fallback file: {settings.csv_file}")
    server.serve_forever()


def build_query_data_source(orthanc: OrthancClient | None):
    if settings.data_source == "csv":
        return CsvDataSource(settings.csv_file)

    if settings.data_source == "auto":
        if orthanc is None:
            return CsvDataSource(settings.csv_file)
        return FallbackDataSource(orthanc, CsvDataSource(settings.csv_file))

    if settings.data_source != "orthanc":
        raise ValueError("QUERY_DATA_SOURCE must be one of: orthanc, csv, auto.")

    if orthanc is None:
        raise ValueError("QUERY_PACS_URL is required when QUERY_DATA_SOURCE=orthanc.")
    return orthanc


if __name__ == "__main__":
    main()
