#!/usr/bin/env bash
set -euo pipefail

CERT_DIR="./backend/certs"
CERT_FILE="$CERT_DIR/cert.pem"
KEY_FILE="$CERT_DIR/key.pem"

if [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE" ]; then
    echo "Certificates already exist at $CERT_DIR — skipping generation."
    exit 0
fi

command -v openssl >/dev/null 2>&1 || { echo "openssl not found. Please install it."; exit 1; }

mkdir -p "$CERT_DIR"

openssl req -x509 \
    -newkey rsa:2048 \
    -keyout "$KEY_FILE" \
    -out "$CERT_FILE" \
    -days 365 \
    -nodes \
    -subj "/C=US/ST=Space/L=Orbit/O=OrbitalMesh/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

chmod 600 "$KEY_FILE"
chmod 644 "$CERT_FILE"

echo "Generated QUIC TLS certificates at $CERT_DIR"
echo "  cert: $CERT_FILE"
echo "  key:  $KEY_FILE"
