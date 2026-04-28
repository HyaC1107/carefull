#!/bin/bash
# Carefull 앱 런처 — 바탕화면 아이콘 및 PM2 에서 호출

# 스크립트 위치로 이동 (어디서 실행하든 raspberry/ 기준)
cd "$(dirname "$(readlink -f "$0")")"

export DISPLAY=:0
export XAUTHORITY="$HOME/.Xauthority"

# X 서버가 준비될 때까지 대기 (부팅 직후 PM2 자동실행 대비, 최대 60초)
for i in $(seq 1 60); do
    if xset q &>/dev/null 2>&1; then
        break
    fi
    sleep 1
done

# 가상환경 자동 감지 (venv가 있으면 활성화)
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "../venv/bin/activate" ]; then
    source ../venv/bin/activate
fi

python main.py
