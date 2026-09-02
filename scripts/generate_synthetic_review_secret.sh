#!/usr/bin/env bash
# generate_synthetic_review_secret.sh
# Generates a one-time secret for the synthetic review environment.
# - Idempotent: if secrets/synthetic_review.key exists, prints its SHA-256 and exits 0.
# - If missing: generates a Django-compatible secret key, writes to secrets/synthetic_review.key (mode 600), prints the SHA-256 of the file.
# - Never prints the secret itself.
set -euo pipefail

SECRET_FILE="$(cd "$(dirname "$0")/.." && pwd)/secrets/synthetic_review.key"
SHA256_FILE="${SECRET_FILE}.sha256"

if [[ -f "$SECRET_FILE" ]]; then
    echo "Secret already exists: $SECRET_FILE"
    echo "SHA-256 of file:"
    sha256sum "$SECRET_FILE" | awk '{print $1}'
    exit 0
fi

SECRET_DIR="$(dirname "$SECRET_FILE")"
mkdir -p "$SECRET_DIR"
chmod 700 "$SECRET_DIR"

SECRET=$(python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
echo "$SECRET" > "$SECRET_FILE"
chmod 600 "$SECRET_FILE"

echo "Generated: $SECRET_FILE"
echo "SHA-256 of file (use this to verify integrity):"
sha256sum "$SECRET_FILE" | awk '{print $1}'
echo ""
echo "To start the review server, run:"
echo "  export SYNTHETIC_REVIEW_SECRET=\$(cat $SECRET_FILE)"
echo "  export DJANGO_SETTINGS_MODULE=portal.settings_synthetic_review"
echo "  python manage.py runserver 127.0.0.1:8000 --noreload"
