#!/usr/bin/env bash
# 玉山交易 API 模擬環境 —— 安裝腳本
# 前置：先到 SDK 下載頁取得對應你 Python 版本/平台的 wheel，放到 ./sdk/ 下
#   https://www.esunsec.com.tw/trading-platforms/api-trading/docs  → 「SDK 下載」
#   檔名形如：esun_trade-<version>-<platform>.whl
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"

echo "[1/3] 建立 venv (.venv) ..."
"$PY" -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

echo "[2/3] 升級 pip ..."
python -m pip install --upgrade pip

echo "[3/3] 安裝 esun_trade wheel ..."
WHL=$(ls sdk/esun_trade-*.whl 2>/dev/null | head -n1 || true)
if [ -z "$WHL" ]; then
  echo "！找不到 sdk/esun_trade-*.whl —— 請先從 SDK 下載頁取得對應版本放進 sdk/ 再重跑。"
  exit 1
fi
pip install "$WHL"

echo
echo "完成。啟用環境後執行測試："
echo "  source .venv/bin/activate && python index.py"
