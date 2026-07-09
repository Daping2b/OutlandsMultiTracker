#!/bin/bash
# OMT — healthcheck.sh
# À placer sur le VPS : ~/healthcheck.sh
# Cron recommandé (crontab -e) :
#   */5 * * * * /home/ubuntu/healthcheck.sh >> /home/ubuntu/healthcheck.log 2>&1
#
# Ce script :
#   - Ping /health sur prod ET staging
#   - En cas d'échec, envoie un message Discord via webhook
#   - Si le service revient, envoie un message de rétablissement
#   - Ne spam pas : 1 alerte par panne (fichier flag)
#
# Configuration :
#   DISCORD_WEBHOOK — webhook URL du salon d'alerte (à renseigner ci-dessous)
#   FLAG_DIR        — dossier où les flags de panne sont stockés

set -euo pipefail

# ── CONFIGURATION ─────────────────────────────────────────────────────────────
DISCORD_WEBHOOK="${OMT_HEALTHCHECK_WEBHOOK:-}"   # Variable d'env, ou coller l'URL ici
PROD_URL="https://outlands-multi-tracker.com/health"
STAGING_URL="https://staging.outlands-multi-tracker.com/health"
TIMEOUT=10          # secondes avant timeout curl
FLAG_DIR="/tmp/omt_healthcheck_flags"
LOG_PREFIX="[OMT healthcheck]"

# ── HELPERS ───────────────────────────────────────────────────────────────────
timestamp() { date "+%Y-%m-%d %H:%M:%S"; }

log() { echo "$(timestamp) $LOG_PREFIX $*"; }

discord_send() {
    local msg="$1"
    if [[ -z "$DISCORD_WEBHOOK" ]]; then
        log "WARN: DISCORD_WEBHOOK non configuré — message non envoyé : $msg"
        return
    fi
    local payload
    payload=$(printf '{"content": "%s"}' "$msg")
    curl -s -o /dev/null -X POST "$DISCORD_WEBHOOK" \
        -H "Content-Type: application/json" \
        -d "$payload" \
        --max-time 10 || log "WARN: Échec envoi Discord"
}

discord_embed() {
    # Envoie un embed coloré : color 15158332 = rouge, 3066993 = vert
    local title="$1"
    local desc="$2"
    local color="$3"
    if [[ -z "$DISCORD_WEBHOOK" ]]; then
        log "WARN: DISCORD_WEBHOOK non configuré"
        return
    fi
    local payload
    payload=$(cat <<EOF
{
  "embeds": [{
    "title": "$title",
    "description": "$desc",
    "color": $color,
    "footer": {"text": "OMT Healthcheck • $(timestamp)"}
  }]
}
EOF
)
    curl -s -o /dev/null -X POST "$DISCORD_WEBHOOK" \
        -H "Content-Type: application/json" \
        -d "$payload" \
        --max-time 10 || log "WARN: Échec envoi Discord embed"
}

mkdir -p "$FLAG_DIR"

# ── CHECK FONCTION ─────────────────────────────────────────────────────────────
check_endpoint() {
    local name="$1"       # "prod" ou "staging"
    local url="$2"
    local flag_file="$FLAG_DIR/down_${name}"

    local http_code
    local body

    # curl : retourne le code HTTP, capture le body
    http_code=$(curl -s -o /tmp/omt_hc_body_${name} -w "%{http_code}" \
        --max-time "$TIMEOUT" "$url" 2>/dev/null || echo "000")
    body=$(cat /tmp/omt_hc_body_${name} 2>/dev/null || echo "")

    # Succès : HTTP 200 ET body contient "ok"
    if [[ "$http_code" == "200" ]] && echo "$body" | grep -q '"status".*"ok"'; then
        log "OK $name ($url) — HTTP $http_code"

        # Rétablissement : si un flag de panne existe, envoyer alerte retour
        if [[ -f "$flag_file" ]]; then
            local down_since
            down_since=$(cat "$flag_file")
            rm -f "$flag_file"
            discord_embed \
                "✅ OMT $name — Service rétabli" \
                "Le service **$name** répond à nouveau normalement.\nURL : \`$url\`\nEn panne depuis : $down_since" \
                "3066993"
            log "RECOVERY: $name rétabli — alerte Discord envoyée"
        fi

    else
        # Échec
        log "DOWN $name ($url) — HTTP $http_code | body: ${body:0:100}"

        if [[ ! -f "$flag_file" ]]; then
            # Première détection : créer le flag et envoyer l'alerte
            timestamp > "$flag_file"
            local detail
            if [[ "$http_code" == "000" ]]; then
                detail="Timeout ou connexion refusée (curl code 000)"
            else
                detail="HTTP $http_code — \`${body:0:200}\`"
            fi
            discord_embed \
                "🔴 OMT $name — Service DOWN" \
                "Le service **$name** ne répond plus !\nURL : \`$url\`\nDétail : $detail" \
                "15158332"
            log "ALERT: $name DOWN — alerte Discord envoyée"
        else
            log "STILL DOWN: $name (alerte déjà envoyée, pas de spam)"
        fi
    fi
}

# ── VÉRIFICATIONS ─────────────────────────────────────────────────────────────
log "=== Démarrage des checks ==="
check_endpoint "prod"    "$PROD_URL"
check_endpoint "staging" "$STAGING_URL"
log "=== Fin des checks ==="
