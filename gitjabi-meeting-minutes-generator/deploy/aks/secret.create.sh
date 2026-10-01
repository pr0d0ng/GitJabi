#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-meeting-minutes}"
SECRET_NAME="${SECRET_NAME:-meeting-minutes-secrets}"

required_vars=(
  TENANT_ID
  CLIENT_ID
  CLIENT_SECRET
  BLOB_CONNECTION_STRING
  LLAMA_ENDPOINT
  DATABRICKS_TOKEN
  HF_TOKEN
  MEETING_API_KEY
)

for var in "${required_vars[@]}"; do
  if [[ -z "${!var:-}" ]]; then
    echo "Missing required env var: ${var}" >&2
    exit 1
  fi
done

kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

kubectl -n "${NAMESPACE}" create secret generic "${SECRET_NAME}" \
  --from-literal=TENANT_ID="${TENANT_ID}" \
  --from-literal=CLIENT_ID="${CLIENT_ID}" \
  --from-literal=CLIENT_SECRET="${CLIENT_SECRET}" \
  --from-literal=BLOB_CONNECTION_STRING="${BLOB_CONNECTION_STRING}" \
  --from-literal=LLAMA_ENDPOINT="${LLAMA_ENDPOINT}" \
  --from-literal=DATABRICKS_TOKEN="${DATABRICKS_TOKEN}" \
  --from-literal=HF_TOKEN="${HF_TOKEN}" \
  --from-literal=MEETING_API_KEY="${MEETING_API_KEY}" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "Secret '${SECRET_NAME}' applied in namespace '${NAMESPACE}'."
