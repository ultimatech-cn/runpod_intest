#!/usr/bin/env bash

echo "Symlinking files from Network Volume"
rm -rf /workspace && \
  ln -s /runpod-volume /workspace

echo "[INFO] runpod-volume"
ls -l /runpod-volume
echo "[INFO] workspace"
ls -l /workspace

echo "Starting ComfyUI API"

cd /workspace/ComfyUI

echo "environment"
source /workspace/myenv/bin/activate

echo "Clear old log content"
rm -f /tmp/comfyui.log
touch /tmp/comfyui.log

echo "Start ComfyUI, redirect output to log"
yes | comfy launch > /tmp/comfyui.log 2>&1 &

COMFY_PID=$!

echo "[INFO]Waiting for ComfyUI to become available..."

TIMEOUT=300  
START_TIME=$(date +%s)

while true; do
  if ! ps -p $COMFY_PID > /dev/null; then
    echo "[ERROR] ? ComfyUI process exited unexpectedly. Check /tmp/comfyui.log for details."
    echo "[INFO] ?? ComfyUI log output:"
    cat /tmp/comfyui.log
    exit 1
  fi

  if grep -q "To see the GUI go to: http://127.0.0.1:8188" /tmp/comfyui.log; then
    NOW=$(date +%s)
    ELAPSED=$((NOW - START_TIME))
    echo "[INFO] ? ComfyUI is ready at http://127.0.0.1:8188"
    echo "[INFO] ?? ComfyUI startup time: ${ELAPSED} seconds"
    break
  fi

  NOW=$(date +%s)
  ELAPSED=$((NOW - START_TIME))
  if [ $ELAPSED -ge $TIMEOUT ]; then
    echo "[ERROR] ? Timeout waiting for ComfyUI to start."
    echo "[INFO] ?? ComfyUI log output:"
    cat /tmp/comfyui.log
    exit 1
  fi

  sleep 1
done

echo "[INFO] ? Now you can safely run the following commands..."

echo "[INFO] ?? Full ComfyUI log output:"
cat /tmp/comfyui.log
echo "[INFO] ?? ----- End of comfyui.log -----"

# ------------------------
# Start RunPod Handler
# ------------------------
echo "[INFO] ?? Starting RunPod Handler"
python -u /rp_handler.py
