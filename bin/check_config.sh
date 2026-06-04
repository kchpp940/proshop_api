#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
YELLOW='\033[0;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

ENV="${ENVIRONMENT:-development}"
ERRORS=0
WARNINGS=0

printf "${CYAN}======================================================================${NC}\n"
printf "${CYAN}Bootstrap / CI Configuration Check (lightweight, no Django required)${NC}\n"
printf "${CYAN}======================================================================${NC}\n"
printf "Environment: ${ENV}\n\n"

check_var() {
    local name="$1"
    local required="$2"
    local description="$3"
    local source="$4"

    local value="${!name:-}"

    if [[ -n "$value" ]]; then
        if [[ "$name" == *"KEY"* || "$name" == *"SECRET"* || "$name" == *"PASSWORD"* ]]; then
            printf "  ${GREEN}✓${NC} %s: SET = ******** [%s]\n" "$name" "$source"
        else
            printf "  ${GREEN}✓${NC} %s: SET = %s [%s]\n" "$name" "${value:0:20}" "$source"
        fi
    elif [[ "$required" == "always" ]]; then
        printf "  ${RED}✗${NC} %s: MISSING - REQUIRED (%s) [%s]\n" "$name" "$description" "$source"
        ERRORS=$((ERRORS+1))
    elif [[ "$required" == "production" && "$ENV" == "production" ]]; then
        printf "  ${RED}✗${NC} %s: MISSING - REQUIRED in production (%s) [%s]\n" "$name" "$description" "$source"
        ERRORS=$((ERRORS+1))
    else
        printf "  ${YELLOW}△${NC} %s: MISSING - optional (%s) [%s]\n" "$name" "$description" "$source"
        WARNINGS=$((WARNINGS+1))
    fi
}

check_dir() {
    local name="$1"
    local rel_path="$2"

    local full_path="$PROJECT_DIR/$rel_path"

    if [[ ! -e "$full_path" ]]; then
        printf "  ${YELLOW}△${NC} %s: %s does not exist\n" "$name" "$full_path"
        WARNINGS=$((WARNINGS+1))
    elif [[ ! -d "$full_path" ]]; then
        printf "  ${RED}✗${NC} %s: %s is not a directory\n" "$name" "$full_path"
        ERRORS=$((ERRORS+1))
    elif [[ ! -w "$full_path" ]]; then
        printf "  ${RED}✗${NC} %s: %s is not writable\n" "$name" "$full_path"
        ERRORS=$((ERRORS+1))
    else
        printf "  ${GREEN}✓${NC} %s: %s (exists, writable)\n" "$name" "$full_path"
    fi
}

printf "${CYAN}[1/3] Checking Environment Variables${NC}\n"

check_var SECRET_KEY          always     "Django secret key"                 "settings.py"
check_var DOMAIN              production "Domain for email/OAuth"            "settings.py"
check_var SITE_NAME           production "Site name for email"               "settings.py"
check_var EMAIL_HOST_USER     production "SMTP email username"               "settings.py"
check_var EMAIL_HOST_PASSWORD production "SMTP email password"               "settings.py"
check_var SOCIAL_AUTH_GOOGLE_OAUTH2_KEY    no "Google OAuth2 client ID"    "settings.py"
check_var SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET no "Google OAuth2 client secret" "settings.py"

if [[ "$ENV" == "production" ]]; then
    check_var APP_DB_NAME            always "PostgreSQL database name"    "azure_settings.py"
    check_var POSTGRES_ADMIN_USER    always "PostgreSQL admin username"   "azure_settings.py"
    check_var POSTGRES_ADMIN_PASSWORD always "PostgreSQL admin password"  "azure_settings.py"
    check_var POSTGRES_HOST          always "PostgreSQL host"             "azure_settings.py"
    check_var AZ_STORAGE_ACCOUNT_NAME always "Azure storage account name" "azure_settings.py"
    check_var AZ_STORAGE_CONTAINER   always "Azure storage container"     "azure_settings.py"
    check_var AZ_STORAGE_KEY         always "Azure storage account key"   "azure_settings.py"
fi

printf "\n${CYAN}[2/3] Checking Dangerous Configs (env-based)${NC}\n"

if [[ "$ENV" == "production" ]]; then
    if [[ "${DEBUG:-}" == "True" || "${DEBUG:-}" == "true" || "${DEBUG:-}" == "1" ]]; then
        printf "  ${RED}✗${NC} DEBUG is explicitly enabled in production\n"
        ERRORS=$((ERRORS+1))
    else
        printf "  ${GREEN}✓${NC} DEBUG: not explicitly enabled in production\n"
    fi
else
    printf "  ${YELLOW}△${NC} Running in development mode (DEBUG=True expected)\n"
    WARNINGS=$((WARNINGS+1))
fi

printf "\n${CYAN}[3/3] Checking Storage Directories${NC}\n"

check_dir STATIC_ROOT staticfiles
check_dir MEDIA_ROOT  static/images

printf "\n${CYAN}======================================================================${NC}\n"
printf "${CYAN}Summary${NC}\n"
printf "${CYAN}======================================================================${NC}\n"
printf "Warnings: %d  Errors: %d\n" "$WARNINGS" "$ERRORS"

if [[ "$ERRORS" -gt 0 ]]; then
    printf "\n${RED}Bootstrap check FAILED with %d error(s).${NC}\n" "$ERRORS"
    exit 1
fi

if [[ "$WARNINGS" -gt 0 ]]; then
    printf "\n${YELLOW}Bootstrap check passed with %d warning(s).${NC}\n" "$WARNINGS"
    if [[ "${1:-}" == "--strict" ]]; then
        printf "${YELLOW}Strict mode: treating warnings as errors.${NC}\n"
        exit 1
    fi
else
    printf "\n${GREEN}All bootstrap checks passed!${NC}\n"
fi

exit 0
