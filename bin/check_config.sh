#!/bin/bash
set -e

MINIMAL_VARS=(
    "SECRET_KEY"
    "DJANGO_SETTINGS_MODULE"
)

DATABASE_VARS=(
    "POSTGRES_SERVER_NAME"
    "POSTGRES_ADMIN_USER"
    "POSTGRES_ADMIN_PASSWORD"
    "POSTGRES_HOST"
    "APP_DB_NAME"
)

STRICT_MODE=false
if [ "$1" = "--strict" ]; then
    STRICT_MODE=true
fi

echo "🔍 Running minimal pre-start configuration check (strict=$STRICT_MODE)..."

MISSING=()
for VAR in "${MINIMAL_VARS[@]}"; do
    if [ -z "${!VAR}" ]; then
        MISSING+=("$VAR")
    fi
done

if [ "$STRICT_MODE" = true ]; then
    for VAR in "${DATABASE_VARS[@]}"; do
        if [ -z "${!VAR}" ]; then
            MISSING+=("$VAR")
        fi
    done
fi

if [ ${#MISSING[@]} -gt 0 ]; then
    echo "❌ Missing required environment variables for startup:"
    for VAR in "${MISSING[@]}"; do
        echo "   - $VAR"
    done
    echo "Please set these variables before deploying."
    echo "Note: Deep configuration checks (OAuth, CORS, JWT, etc.) are handled by 'python manage.py check_config'."
    exit 1
fi

echo "✅ Minimal startup configuration is valid."
echo "   Deep configuration checks will run next via 'python manage.py check_config'."
exit 0
