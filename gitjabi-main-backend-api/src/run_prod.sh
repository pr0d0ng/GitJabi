#!/bin/bash

APP_NAME="fastapi-uvicorn"
APP_DIR="/home/gitjabi/gitjabi_backend_api"  
VENV_DIR="$APP_DIR/.venv"
LOG_FILE="$APP_DIR/uvicorn.log"
PID_FILE="$APP_DIR/uvicorn.pid"

export PYTHONPATH="$APP_DIR/src"

UVICORN_CMD="$VENV_DIR/bin/uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8443 \
  --workers 4 \
  --proxy-headers \
  --forwarded-allow-ips='*'" 
#   --ssl-keyfile=$APP_DIR/privkey.pem \
#   --ssl-certfile=$APP_DIR/fullchain.pem"

start() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "이미 실행 중입니다 (PID: $(cat $PID_FILE))"
        exit 1
    fi

    echo "FastAPI 서버 시작..."
    cd "$APP_DIR" || exit 1

    source "$VENV_DIR/bin/activate"

    nohup $UVICORN_CMD > "$LOG_FILE" 2>&1 &

    echo $! > "$PID_FILE"
    echo "시작 완료 (PID: $(cat $PID_FILE))"
}

stop() {
    if [ ! -f "$PID_FILE" ]; then
        echo "실행 중인 프로세스가 없습니다"
        exit 1
    fi

    PID=$(cat "$PID_FILE")

    if kill -0 "$PID" 2>/dev/null; then
        echo "⏹ FastAPI 서버 종료 (PID: $PID)"
        kill "$PID"
        rm -f "$PID_FILE"
        echo "종료 완료"
    else
        echo "PID 파일은 있으나 프로세스가 없습니다"
        rm -f "$PID_FILE"
    fi
}

status() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "실행 중 (PID: $(cat $PID_FILE))"
    else
        echo "실행 중 아님"
    fi
}

restart() {
    stop
    sleep 1
    start
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    *)
        echo "사용법: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac