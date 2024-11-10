#!/bin/bash -e

_term() {
    echo "Caught SIGTERM/SIGINT signal!"
}

trap '_term' SIGTERM SIGINT

LOG_CONFIG_PATH=${JUUDGE_LOG_CONFIG_PATH:-/opt/juudge/etc/logging.yaml}
UVICORN_ARGS=

echo "Extra uvicorn args: ${UVICORN_ARGS:-<none>}"
exec /opt/juudge/bin/uvicorn \
    --proxy-headers \
    --forwarded-allow-ips "*" \
    --host 0.0.0.0 \
    --log-config "${LOG_CONFIG_PATH}" \
    ${UVICORN_ARGS} \
    --factory juudge.web.web:create_app
