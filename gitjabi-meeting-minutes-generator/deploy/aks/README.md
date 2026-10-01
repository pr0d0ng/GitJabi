# AKS Deployment Guide (Meeting Minutes API)

## 1) Build and push image

Run from project root:

```powershell
$ACR_NAME="<your-acr-name>"
$IMAGE="$ACR_NAME.azurecr.io/meeting-minutes-api:latest"

az acr login -n $ACR_NAME
docker build -f docker/meeting-minutes-api.Dockerfile -t $IMAGE .
docker push $IMAGE
```

If your AKS is not attached to ACR:

```powershell
az aks update -g <aks-rg> -n <aks-name> --attach-acr $ACR_NAME
```

## 2) Prepare Kubernetes manifests

1. Update image in `deploy/aks/deployment.yaml`:
   - `<acr-name>.azurecr.io/meeting-minutes-api:latest`
2. Copy `deploy/aks/secret.sample.yaml` to a local file and fill real values.
3. Apply manifests:

```powershell
kubectl apply -f deploy/aks/namespace.yaml
kubectl apply -f deploy/aks/configmap.yaml
kubectl apply -f <your-secret-file>.yaml
kubectl apply -f deploy/aks/deployment.yaml
kubectl apply -f deploy/aks/worker-deployment.yaml
kubectl apply -f deploy/aks/service.yaml
```

## 3) Validate service

```powershell
kubectl -n meeting-minutes get pods
kubectl -n meeting-minutes get svc
kubectl -n meeting-minutes logs deploy/meeting-minutes-api --tail=100
kubectl -n meeting-minutes logs deploy/meeting-minutes-worker --tail=100
```

In-cluster health check:

```powershell
kubectl -n meeting-minutes run curltest --rm -it --image=curlimages/curl -- \
  curl -s http://meeting-minutes-api:8080/healthz
```

Expected response:

```json
{"status":"ok"}
```

## 4) Connect Function App -> AKS API

Set Function App settings:

```powershell
az functionapp config appsettings set -g 2dt-final-team2 -n 2dt-final-team2-meeting-video-downloaderFA --settings `
  MEETING_API_BASE_URL="http://<reachable-aks-api-url>" `
  MEETING_API_KEY="<internal-api-key>"
```

Then restart:

```powershell
az functionapp restart -g 2dt-final-team2 -n 2dt-final-team2-meeting-video-downloaderFA
```

## 5) Notes

- `MEETING_API_KEY` is optional in API, but if set, poller must send same key.
- Job status is stored in Blob (`JOB_STORE_CONTAINER` / `JOB_STORE_PREFIX`) so API and worker can share state.
- API enqueues to Azure Queue (`JOB_QUEUE_NAME`), worker consumes queue and executes pipeline.
- Function App cannot reach `*.svc.cluster.local` unless VNet integration is configured.
- If Function App is public-only, expose AKS API with Ingress or apply `deploy/aks/service-loadbalancer.sample.yaml`.

## 6) CI/CD with GitHub Actions

Workflow file:
- `.github/workflows/deploy-aks.yml`

Required GitHub Secrets:
- `AZURE_CREDENTIALS` (Service Principal JSON)
- `ACR_NAME`
- `AKS_RESOURCE_GROUP`
- `AKS_NAME`
- `TENANT_ID`
- `CLIENT_ID`
- `CLIENT_SECRET`
- `BLOB_CONNECTION_STRING`
- `LLAMA_ENDPOINT`
- `DATABRICKS_TOKEN`
- `HF_TOKEN`
- `MEETING_API_KEY`
- `MODEL_BLOB_CONTAINER`
- `MODEL_BLOB_PREFIX`

Behavior:
1. Download classifier models from Blob into:
   - `outputs/summary_worthy/best_model`
   - `outputs/has_action_item/best_model`
1. Build image from `docker/meeting-minutes-api.Dockerfile`
2. Push image to ACR (`<ACR_NAME>.azurecr.io/meeting-minutes-api:<git-sha>`)
3. Update/apply Kubernetes manifests
4. Rollout wait + health check

Expected blob layout for model download:
- `<MODEL_BLOB_PREFIX>/summary_worthy/best_model/config.json`
- `<MODEL_BLOB_PREFIX>/summary_worthy/best_model/model.safetensors`
- `<MODEL_BLOB_PREFIX>/summary_worthy/best_model/tokenizer.json`
- `<MODEL_BLOB_PREFIX>/summary_worthy/best_model/tokenizer_config.json`
- `<MODEL_BLOB_PREFIX>/summary_worthy/best_model/training_args.bin`
- `<MODEL_BLOB_PREFIX>/has_action_item/best_model/config.json`
- `<MODEL_BLOB_PREFIX>/has_action_item/best_model/model.safetensors`
- `<MODEL_BLOB_PREFIX>/has_action_item/best_model/tokenizer.json`
- `<MODEL_BLOB_PREFIX>/has_action_item/best_model/tokenizer_config.json`
- `<MODEL_BLOB_PREFIX>/has_action_item/best_model/training_args.bin`

You can also run manual secret apply with:

```bash
export TENANT_ID=...
export CLIENT_ID=...
export CLIENT_SECRET=...
export BLOB_CONNECTION_STRING=...
export LLAMA_ENDPOINT=...
export DATABRICKS_TOKEN=...
export HF_TOKEN=...
export MEETING_API_KEY=...
bash deploy/aks/secret.create.sh
```

## 7) Spot GPU on-demand worker (optional)

Use this when you want GPU speed but keep cost down by scaling worker to zero when queue is empty.

1. Add Spot GPU node pool (AKS):

```powershell
az aks nodepool add -g <aks-rg> -n gpuspot --cluster-name <aks-name> `
  --priority Spot --eviction-policy Delete --spot-max-price -1 `
  --node-vm-size Standard_NC24ads_A100_v4 --enable-cluster-autoscaler `
  --min-count 0 --max-count 1 --node-count 0 --mode User
```

2. Install KEDA once (if not installed):

```powershell
helm repo add kedacore https://kedacore.github.io/charts
helm repo update
helm upgrade --install keda kedacore/keda --namespace keda --create-namespace
```

3. Apply dedicated GPU worker deployment (separate from CPU worker):

```powershell
kubectl apply -f deploy/aks/worker-deployment.gpu-spot.yaml
```

4. Enable queue-driven autoscale (0 -> 1) for GPU worker:

```powershell
kubectl apply -f deploy/aks/keda-scaledobject.worker.yaml
```

5. Verify:

```powershell
kubectl -n meeting-minutes get deploy meeting-minutes-worker meeting-minutes-worker-gpu
kubectl -n meeting-minutes get scaledobject
kubectl -n meeting-minutes logs deploy/meeting-minutes-worker-gpu --tail=100
```

Notes:
- Spot can be evicted at any time. Keep retry logic enabled.
- `deploy/aks/configmap.yaml` sets `POLLER_STT_CHUNK_MINUTES` to `20` by default.
- To avoid double-consuming jobs, run only one worker type at a time:
  - CPU only: `kubectl -n meeting-minutes scale deploy meeting-minutes-worker --replicas=1` and keep GPU scaler/replicas 0
  - GPU only: `kubectl -n meeting-minutes scale deploy meeting-minutes-worker --replicas=0`
