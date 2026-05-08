#!/bin/bash
# 사용법 (SSH에서):
#   ./record.sh start    # 녹화 시작
#   ./record.sh stop     # 녹화 종료 및 파일 저장
#   ./record.sh status   # 녹화 중 여부 확인
#
# 설치 (최초 1회):
#   sudo apt install wf-recorder

OUTPUT_DIR="$HOME/Videos/carefull_recordings"
PID_FILE="/tmp/carefull_record.pid"

# SSH 접속 시 Wayland 환경변수가 없으므로 직접 설정
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-1}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

_start() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "[RECORD] 이미 녹화 중입니다. (PID: $(cat "$PID_FILE"))"
        exit 1
    fi

    if ! command -v wf-recorder &>/dev/null; then
        echo "[RECORD] wf-recorder 없음. 설치: sudo apt install wf-recorder"
        exit 1
    fi

    mkdir -p "$OUTPUT_DIR"
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    OUTPUT_FILE="$OUTPUT_DIR/carefull_${TIMESTAMP}.mp4"

    wf-recorder -f "$OUTPUT_FILE" &
    echo $! > "$PID_FILE"
    echo "[RECORD] 녹화 시작됨"
    echo "[RECORD] 저장 경로: $OUTPUT_FILE"
    echo "[RECORD] PID: $!"
}

_stop() {
    if [ ! -f "$PID_FILE" ]; then
        echo "[RECORD] 녹화 중이 아닙니다."
        exit 1
    fi

    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        kill -SIGINT "$PID"   # SIGTERM 아닌 SIGINT로 끝내야 mp4 정상 저장됨
        sleep 1
        rm -f "$PID_FILE"
        echo "[RECORD] 녹화 종료. 파일 저장 완료."
        echo "[RECORD] 확인: ls -lh $OUTPUT_DIR"
    else
        echo "[RECORD] 프로세스가 이미 종료되어 있습니다."
        rm -f "$PID_FILE"
    fi
}

_status() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "[RECORD] 녹화 중 (PID: $(cat "$PID_FILE"))"
    else
        [ -f "$PID_FILE" ] && rm -f "$PID_FILE"
        echo "[RECORD] 녹화 중 아님"
    fi
}

case "$1" in
    start)  _start  ;;
    stop)   _stop   ;;
    status) _status ;;
    *)
        echo "사용법: $0 {start|stop|status}"
        echo ""
        echo "  start   녹화 시작 (저장: ~/Videos/carefull_recordings/)"
        echo "  stop    녹화 종료 및 mp4 저장"
        echo "  status  현재 상태 확인"
        ;;
esac
