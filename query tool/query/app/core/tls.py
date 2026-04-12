import os
import ssl


def create_ssl_context(certfile: str, keyfile: str, ca_file: str | None = None) -> ssl.SSLContext:
    if not os.path.isfile(certfile) or not os.path.isfile(keyfile):
        raise FileNotFoundError(f"TLS certificate or key file not found: {certfile}, {keyfile}")

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=certfile, keyfile=keyfile)

    if ca_file:
        if not os.path.isfile(ca_file):
            raise FileNotFoundError(f"TLS CA file not found: {ca_file}")
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_verify_locations(cafile=ca_file)

    return context
