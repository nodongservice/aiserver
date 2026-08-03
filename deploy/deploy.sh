#!/usr/bin/env bash
set -Eeuo pipefail

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

require_command() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    log "필수 명령어가 없습니다: $cmd"
    exit 1
  fi
}

is_container_running() {
  local container_name="$1"
  docker ps --format '{{.Names}}' | grep -q "^${container_name}$"
}

APP_NAME="${APP_NAME:-bridgework-aiserver}"
APP_ROOT="${APP_ROOT:-$HOME/bridgework/aiserver}"
STATE_DIR="${STATE_DIR:-$APP_ROOT/state}"
ACTIVE_SLOT_FILE="${ACTIVE_SLOT_FILE:-$STATE_DIR/fastapi_active_slot}"
ENV_FILE="${ENV_FILE:-$APP_ROOT/.env.prod}"
UPSTREAM_SWITCH_SCRIPT="${UPSTREAM_SWITCH_SCRIPT:-$HOME/bridgework-infra/deploy/fastapi_blue_green_switch.sh}"
DOCKER_NETWORK="${DOCKER_NETWORK:-bridgework-network}"
FASTAPI_NETWORK_ALIAS="${FASTAPI_NETWORK_ALIAS:-bridgework-aiserver}"

BLUE_PORT="${BLUE_PORT:-19000}"
GREEN_PORT="${GREEN_PORT:-19001}"
CONTAINER_PORT="${CONTAINER_PORT:-8000}"

HEALTH_TIMEOUT_SECONDS="${HEALTH_TIMEOUT_SECONDS:-120}"
HEALTH_INTERVAL_SECONDS="${HEALTH_INTERVAL_SECONDS:-2}"
HEALTH_CONNECT_TIMEOUT_SECONDS="${HEALTH_CONNECT_TIMEOUT_SECONDS:-2}"
HEALTH_REQUEST_TIMEOUT_SECONDS="${HEALTH_REQUEST_TIMEOUT_SECONDS:-3}"
HEALTH_REQUIRE_DB="${HEALTH_REQUIRE_DB:-true}"
HEALTH_REQUIRE_POSTGIS="${HEALTH_REQUIRE_POSTGIS:-true}"

IMAGE_URI="${IMAGE_URI:-}"
IMAGE_RETENTION_COUNT="${IMAGE_RETENTION_COUNT:-2}"
PRE_PULL_IMAGE_RETENTION_COUNT="${PRE_PULL_IMAGE_RETENTION_COUNT:-2}"
MIN_FREE_DISK_MB="${MIN_FREE_DISK_MB:-4096}"
DOCKER_LOG_DRIVER="${DOCKER_LOG_DRIVER:-local}"
DOCKER_LOG_MAX_SIZE="${DOCKER_LOG_MAX_SIZE:-20m}"
DOCKER_LOG_MAX_FILE="${DOCKER_LOG_MAX_FILE:-3}"
PULL_IMAGE="${PULL_IMAGE:-false}"
CLEANUP_ONLY="${CLEANUP_ONLY:-false}"
ASYNC_IMAGE_CLEANUP="${ASYNC_IMAGE_CLEANUP:-true}"
PRE_PULL_CLEANUP="${PRE_PULL_CLEANUP:-true}"
PRE_PULL_SYSTEM_PRUNE="${PRE_PULL_SYSTEM_PRUNE:-true}"
if [[ -z "$IMAGE_URI" ]]; then
  log "IMAGE_URI 환경변수는 필수입니다."
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  log "환경변수 파일이 없습니다: $ENV_FILE"
  exit 1
fi

require_command docker
require_command curl

if ! docker network inspect "$DOCKER_NETWORK" >/dev/null 2>&1; then
  log "도커 네트워크 생성: $DOCKER_NETWORK"
  docker network create "$DOCKER_NETWORK" >/dev/null
fi

log_docker_disk_usage() {
  log "디스크 사용량:"
  df -h / /var/lib/docker 2>/dev/null || df -h /
  log "Docker 사용량:"
  docker system df || true
}

cleanup_old_app_images() {
  local image_ref="$1"
  local keep_count="$2"
  local repository running_image_ids candidate_ids deleted=0
  repository="${image_ref%%:*}"

  if [[ -z "$repository" || "$repository" == "$image_ref" ]]; then
    log "이미지 정리를 건너뜁니다. 저장소 파싱 실패: $image_ref"
    return 0
  fi

  if ! [[ "$keep_count" =~ ^[0-9]+$ ]] || (( keep_count < 1 )); then
    keep_count=2
  fi

  running_image_ids="$(docker ps --format '{{.Image}}' | xargs -r docker image inspect --format '{{.Id}}' 2>/dev/null | sort -u || true)"
  candidate_ids="$(
    docker image ls "$repository" --format '{{.ID}}' | awk '!seen[$0]++' | tail -n +"$((keep_count + 1))"
  )"

  if [[ -z "$candidate_ids" ]]; then
    log "이미지 정리 대상이 없습니다. repository=$repository keep=$keep_count"
    return 0
  fi

  while IFS= read -r image_id; do
    [[ -z "$image_id" ]] && continue
    if grep -q "$image_id" <<<"$running_image_ids"; then
      continue
    fi
    if docker image rm "$image_id" >/dev/null 2>&1; then
      deleted=$((deleted + 1))
    fi
  done <<<"$candidate_ids"

  docker image prune -f >/dev/null 2>&1 || true
  log "이미지 정리 완료: repository=$repository deleted=$deleted keep=$keep_count"
}

ensure_minimum_free_disk() {
  local required_mb="$1"
  local available_mb

  if ! [[ "$required_mb" =~ ^[0-9]+$ ]] || (( required_mb < 1024 )); then
    log "최소 여유 공간 설정이 올바르지 않습니다: ${required_mb}MB"
    exit 1
  fi

  available_mb="$(df -Pm / | awk 'NR == 2 {print $4}')"
  if ! [[ "$available_mb" =~ ^[0-9]+$ ]]; then
    log "루트 디스크 여유 공간을 확인하지 못했습니다."
    exit 1
  fi

  log "배포 전 루트 디스크 여유 공간: ${available_mb}MB (필요: ${required_mb}MB)"
  if (( available_mb < required_mb )); then
    log "디스크 여유 공간이 부족해 배포를 중단합니다."
    log_docker_disk_usage
    exit 1
  fi
}

cleanup_before_pull() {
  log "pull 전 Docker 공간 정리 시작"
  cleanup_old_app_images "$IMAGE_URI" "$PRE_PULL_IMAGE_RETENTION_COUNT"

  if [[ "$PRE_PULL_SYSTEM_PRUNE" == "true" ]]; then
    docker system prune -f >/dev/null 2>&1 || true
    log "Docker system prune 완료"
  fi

  log_docker_disk_usage
  ensure_minimum_free_disk "$MIN_FREE_DISK_MB"
}

if [[ "$CLEANUP_ONLY" == "true" ]]; then
  cleanup_old_app_images "$IMAGE_URI" "$IMAGE_RETENTION_COUNT"
  exit 0
fi

mkdir -p "$STATE_DIR"

BLUE_CONTAINER="${APP_NAME}-blue"
GREEN_CONTAINER="${APP_NAME}-green"

resolve_current_slot() {
  if [[ -f "$ACTIVE_SLOT_FILE" ]]; then
    local slot
    slot="$(tr -d '[:space:]' < "$ACTIVE_SLOT_FILE")"
    if [[ "$slot" == "blue" || "$slot" == "green" ]]; then
      echo "$slot"
      return
    fi
  fi

  if is_container_running "$BLUE_CONTAINER"; then
    echo "blue"
    return
  fi

  if is_container_running "$GREEN_CONTAINER"; then
    echo "green"
    return
  fi

  echo "blue"
}

CURRENT_SLOT="$(resolve_current_slot)"
if [[ "$CURRENT_SLOT" == "blue" ]]; then
  TARGET_SLOT="green"
  TARGET_CONTAINER="$GREEN_CONTAINER"
  TARGET_PORT="$GREEN_PORT"
  OLD_CONTAINER="$BLUE_CONTAINER"
else
  TARGET_SLOT="blue"
  TARGET_CONTAINER="$BLUE_CONTAINER"
  TARGET_PORT="$BLUE_PORT"
  OLD_CONTAINER="$GREEN_CONTAINER"
fi

if is_container_running "$BLUE_CONTAINER" && is_container_running "$GREEN_CONTAINER"; then
  if [[ "$CURRENT_SLOT" == "blue" ]]; then
    log "이중 실행 감지. 비활성 슬롯 정리: $GREEN_CONTAINER"
    docker rm -f "$GREEN_CONTAINER" >/dev/null 2>&1 || true
  else
    log "이중 실행 감지. 비활성 슬롯 정리: $BLUE_CONTAINER"
    docker rm -f "$BLUE_CONTAINER" >/dev/null 2>&1 || true
  fi
fi

log "현재 슬롯: $CURRENT_SLOT"
log "대상 슬롯: $TARGET_SLOT (container=$TARGET_CONTAINER, hostPort=$TARGET_PORT)"

if [[ "$PRE_PULL_CLEANUP" == "true" ]]; then
  cleanup_before_pull
else
  ensure_minimum_free_disk "$MIN_FREE_DISK_MB"
fi

docker rm -f "$TARGET_CONTAINER" >/dev/null 2>&1 || true

if [[ "$PULL_IMAGE" == "true" ]]; then
  pull_started_at="$(date +%s)"
  log "이미지 pull: $IMAGE_URI"
  if ! docker pull "$IMAGE_URI"; then
    log "이미지 pull 실패. 디스크 상태를 출력합니다."
    log_docker_disk_usage
    exit 1
  fi
  log "이미지 pull 완료: $(( $(date +%s) - pull_started_at ))s"
fi

run_started_at="$(date +%s)"
log "새 컨테이너 실행: $TARGET_CONTAINER"
docker run -d \
  --name "$TARGET_CONTAINER" \
  --restart no \
  --network "$DOCKER_NETWORK" \
  --network-alias "$FASTAPI_NETWORK_ALIAS" \
  --log-driver "$DOCKER_LOG_DRIVER" \
  --log-opt "max-size=$DOCKER_LOG_MAX_SIZE" \
  --log-opt "max-file=$DOCKER_LOG_MAX_FILE" \
  --add-host host.docker.internal:host-gateway \
  --env-file "$ENV_FILE" \
  -e TZ="${TZ:-Asia/Seoul}" \
  -e UVICORN_WORKERS="${UVICORN_WORKERS:-1}" \
  -p "${TARGET_PORT}:${CONTAINER_PORT}" \
  "$IMAGE_URI" >/dev/null
log "새 컨테이너 실행 완료: $(( $(date +%s) - run_started_at ))s"

fetch_health_body() {
  local url="$1"

  curl \
    --connect-timeout "$HEALTH_CONNECT_TIMEOUT_SECONDS" \
    --max-time "$HEALTH_REQUEST_TIMEOUT_SECONDS" \
    -fsS "$url"
}

check_readiness() {
  local base_url="$1"
  local require_db="$2"
  local require_postgis="$3"
  local body

  if ! body="$(fetch_health_body "${base_url}/health" 2>&1)"; then
    printf '/health request failed: %s\n' "$body" >&2
    return 1
  fi
  if [[ "$body" != *'"code":"SUCCESS"'* || "$body" != *'"status":"ok"'* ]]; then
    printf '/health returned unexpected body: %s\n' "$body" >&2
    return 1
  fi

  if [[ "$require_db" == "true" ]]; then
    if ! body="$(fetch_health_body "${base_url}/db-health" 2>&1)"; then
      printf '/db-health request failed: %s\n' "$body" >&2
      return 1
    fi
    if [[ "$body" != *'"code":"SUCCESS"'* || "$body" != *'"status":"ok"'* || "$body" != *'"database":"connected"'* ]]; then
      printf '/db-health returned unexpected body: %s\n' "$body" >&2
      return 1
    fi
  fi

  if [[ "$require_postgis" == "true" ]]; then
    if ! body="$(fetch_health_body "${base_url}/postgis-health" 2>&1)"; then
      printf '/postgis-health request failed: %s\n' "$body" >&2
      return 1
    fi
    if [[ "$body" != *'"code":"SUCCESS"'* || "$body" != *'"status":"ok"'* || "$body" != *'"postgis":"enabled"'* ]]; then
      printf '/postgis-health returned unexpected body: %s\n' "$body" >&2
      return 1
    fi
  fi
}

wait_for_readiness() {
  local base_url="$1"
  local timeout="$2"
  local interval="$3"
  local container_name="$4"
  local waited=0
  local last_error=""

  while (( waited < timeout )); do
    if ! docker ps --format '{{.Names}}' | grep -q "^${container_name}$"; then
      return 2
    fi

    if last_error="$(check_readiness "$base_url" "$HEALTH_REQUIRE_DB" "$HEALTH_REQUIRE_POSTGIS" 2>&1)"; then
      return 0
    fi

    sleep "$interval"
    waited=$((waited + interval))
  done

  if [[ -n "$last_error" ]]; then
    log "마지막 readiness 실패 사유: $last_error"
  fi
  return 1
}

READINESS_BASE_URL="http://127.0.0.1:${TARGET_PORT}"
health_started_at="$(date +%s)"
log "readiness 체크 대기: ${READINESS_BASE_URL} (/health, /db-health, /postgis-health)"
if ! wait_for_readiness "$READINESS_BASE_URL" "$HEALTH_TIMEOUT_SECONDS" "$HEALTH_INTERVAL_SECONDS" "$TARGET_CONTAINER"; then
  log "readiness 체크 실패. 새 컨테이너를 제거하고 배포를 중단합니다."
  docker ps -a --filter "name=${TARGET_CONTAINER}" --format 'table {{.Names}}\t{{.Status}}' || true
  docker logs --tail 120 "$TARGET_CONTAINER" || true
  docker rm -f "$TARGET_CONTAINER" >/dev/null 2>&1 || true
  exit 1
fi
log "readiness 체크 성공: $(( $(date +%s) - health_started_at ))s"

if [[ ! -f "$UPSTREAM_SWITCH_SCRIPT" ]]; then
  log "공통 인프라 전환 스크립트가 없습니다: $UPSTREAM_SWITCH_SCRIPT"
  docker rm -f "$TARGET_CONTAINER" >/dev/null 2>&1 || true
  exit 1
fi

log "공통 인프라 전환 스크립트 실행: ${UPSTREAM_SWITCH_SCRIPT} ${TARGET_SLOT}"
if ! FASTAPI_STATE_DIR="$STATE_DIR" bash "$UPSTREAM_SWITCH_SCRIPT" "$TARGET_SLOT"; then
  log "공통 인프라 전환 스크립트 실행 실패"
  docker rm -f "$TARGET_CONTAINER" >/dev/null 2>&1 || true
  exit 1
fi

echo "$TARGET_SLOT" > "$ACTIVE_SLOT_FILE"
docker update --restart unless-stopped "$TARGET_CONTAINER" >/dev/null

if docker ps -a --format '{{.Names}}' | grep -q "^${OLD_CONTAINER}$"; then
  log "이전 슬롯 컨테이너 정리: $OLD_CONTAINER"
  docker rm -f "$OLD_CONTAINER" >/dev/null 2>&1 || true
fi

log "배포 완료: active_slot=$TARGET_SLOT"
if [[ "$ASYNC_IMAGE_CLEANUP" == "true" ]]; then
  log "이미지 정리 예약: repository=${IMAGE_URI%%:*} keep=$IMAGE_RETENTION_COUNT"
  nohup env \
    IMAGE_URI="$IMAGE_URI" \
    IMAGE_RETENTION_COUNT="$IMAGE_RETENTION_COUNT" \
    CLEANUP_ONLY=true \
    bash "$0" >> "$STATE_DIR/image-cleanup.log" 2>&1 &
else
  cleanup_old_app_images "$IMAGE_URI" "$IMAGE_RETENTION_COUNT"
fi
