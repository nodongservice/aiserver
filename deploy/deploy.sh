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
NGINX_UPSTREAM_CONF="${NGINX_UPSTREAM_CONF:-}"

BLUE_PORT="${BLUE_PORT:-19000}"
GREEN_PORT="${GREEN_PORT:-19001}"
CONTAINER_PORT="${CONTAINER_PORT:-8000}"

HEALTH_ENDPOINT="${HEALTH_ENDPOINT:-/health}"
HEALTH_TIMEOUT_SECONDS="${HEALTH_TIMEOUT_SECONDS:-120}"
HEALTH_INTERVAL_SECONDS="${HEALTH_INTERVAL_SECONDS:-2}"
HEALTH_CONNECT_TIMEOUT_SECONDS="${HEALTH_CONNECT_TIMEOUT_SECONDS:-2}"
HEALTH_REQUEST_TIMEOUT_SECONDS="${HEALTH_REQUEST_TIMEOUT_SECONDS:-3}"

IMAGE_URI="${IMAGE_URI:-}"
IMAGE_RETENTION_COUNT="${IMAGE_RETENTION_COUNT:-5}"
PULL_IMAGE="${PULL_IMAGE:-false}"
CLEANUP_ONLY="${CLEANUP_ONLY:-false}"
ASYNC_IMAGE_CLEANUP="${ASYNC_IMAGE_CLEANUP:-true}"
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
require_command nginx

resolve_upstream_conf_path() {
  if [[ -n "$NGINX_UPSTREAM_CONF" ]]; then
    echo "$NGINX_UPSTREAM_CONF"
    return
  fi

  if [[ -f "/etc/nginx/conf.d/fastapi-upstream.inc" || -d "/etc/nginx/conf.d" ]]; then
    echo "/etc/nginx/conf.d/fastapi-upstream.inc"
    return
  fi

  if [[ -f "/etc/nginx/sites-enabled/fastapi-upstream.inc" || -d "/etc/nginx/sites-enabled" ]]; then
    echo "/etc/nginx/sites-enabled/fastapi-upstream.inc"
    return
  fi

  echo "/etc/nginx/conf.d/fastapi-upstream.inc"
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
    keep_count=5
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

if [[ "$CLEANUP_ONLY" == "true" ]]; then
  cleanup_old_app_images "$IMAGE_URI" "$IMAGE_RETENTION_COUNT"
  exit 0
fi

NGINX_UPSTREAM_CONF="$(resolve_upstream_conf_path)"
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

  if [[ -f "$NGINX_UPSTREAM_CONF" ]]; then
    if grep -Eq "server[[:space:]]+127\\.0\\.0\\.1:${BLUE_PORT};" "$NGINX_UPSTREAM_CONF"; then
      echo "blue"
      return
    fi

    if grep -Eq "server[[:space:]]+127\\.0\\.0\\.1:${GREEN_PORT};" "$NGINX_UPSTREAM_CONF"; then
      echo "green"
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

docker rm -f "$TARGET_CONTAINER" >/dev/null 2>&1 || true

if [[ "$PULL_IMAGE" == "true" ]]; then
  pull_started_at="$(date +%s)"
  log "이미지 pull: $IMAGE_URI"
  docker pull "$IMAGE_URI"
  log "이미지 pull 완료: $(( $(date +%s) - pull_started_at ))s"
fi

run_started_at="$(date +%s)"
log "새 컨테이너 실행: $TARGET_CONTAINER"
docker run -d \
  --name "$TARGET_CONTAINER" \
  --restart no \
  --env-file "$ENV_FILE" \
  -e TZ="${TZ:-Asia/Seoul}" \
  -p "${TARGET_PORT}:${CONTAINER_PORT}" \
  "$IMAGE_URI" >/dev/null
log "새 컨테이너 실행 완료: $(( $(date +%s) - run_started_at ))s"

wait_for_health() {
  local url="$1"
  local timeout="$2"
  local interval="$3"
  local container_name="$4"
  local waited=0

  while (( waited < timeout )); do
    if ! docker ps --format '{{.Names}}' | grep -q "^${container_name}$"; then
      return 2
    fi

    if curl \
      --connect-timeout "$HEALTH_CONNECT_TIMEOUT_SECONDS" \
      --max-time "$HEALTH_REQUEST_TIMEOUT_SECONDS" \
      -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi

    sleep "$interval"
    waited=$((waited + interval))
  done

  return 1
}

HEALTH_URL="http://127.0.0.1:${TARGET_PORT}${HEALTH_ENDPOINT}"
health_started_at="$(date +%s)"
log "헬스체크 대기: $HEALTH_URL"
if ! wait_for_health "$HEALTH_URL" "$HEALTH_TIMEOUT_SECONDS" "$HEALTH_INTERVAL_SECONDS" "$TARGET_CONTAINER"; then
  log "헬스체크 실패. 새 컨테이너를 제거하고 배포를 중단합니다."
  docker ps -a --filter "name=${TARGET_CONTAINER}" --format 'table {{.Names}}\t{{.Status}}' || true
  docker logs --tail 120 "$TARGET_CONTAINER" || true
  docker rm -f "$TARGET_CONTAINER" >/dev/null 2>&1 || true
  exit 1
fi
log "헬스체크 성공: $(( $(date +%s) - health_started_at ))s"

TMP_UPSTREAM_FILE="$(mktemp)"
cat > "$TMP_UPSTREAM_FILE" <<UPSTREAM
upstream bridgework_fastapi_backend {
    server 127.0.0.1:${TARGET_PORT};
    keepalive 64;
}
UPSTREAM

PREV_UPSTREAM_FILE=""
if sudo test -f "$NGINX_UPSTREAM_CONF"; then
  PREV_UPSTREAM_FILE="$(mktemp)"
  sudo cp "$NGINX_UPSTREAM_CONF" "$PREV_UPSTREAM_FILE"
fi

log "nginx upstream 전환: $NGINX_UPSTREAM_CONF"
sudo cp "$TMP_UPSTREAM_FILE" "$NGINX_UPSTREAM_CONF"
rm -f "$TMP_UPSTREAM_FILE"

if ! sudo nginx -t >/dev/null 2>&1; then
  log "nginx 설정 검증 실패. 이전 설정으로 롤백합니다."
  if [[ -n "$PREV_UPSTREAM_FILE" ]]; then
    sudo cp "$PREV_UPSTREAM_FILE" "$NGINX_UPSTREAM_CONF"
  fi
  docker rm -f "$TARGET_CONTAINER" >/dev/null 2>&1 || true
  exit 1
fi

sudo systemctl reload nginx
log "nginx 리로드 완료"

echo "$TARGET_SLOT" > "$ACTIVE_SLOT_FILE"
docker update --restart unless-stopped "$TARGET_CONTAINER" >/dev/null

if docker ps -a --format '{{.Names}}' | grep -q "^${OLD_CONTAINER}$"; then
  log "이전 슬롯 컨테이너 정리: $OLD_CONTAINER"
  docker rm -f "$OLD_CONTAINER" >/dev/null 2>&1 || true
fi

if [[ -n "$PREV_UPSTREAM_FILE" ]]; then
  rm -f "$PREV_UPSTREAM_FILE"
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
