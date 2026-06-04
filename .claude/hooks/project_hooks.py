"""project_hooks.py — 專案層 delegate hooks

由核心引擎 (workflow-guardian.py) 在 SessionStart 時載入。
透過 subprocess 呼叫，stdin/stdout JSON 通訊。
自訂邏輯寫在 on_session_start / inject / extract 內。
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent  # .claude/hooks/ -> project root
MEMORY_DIR = PROJECT_ROOT / ".claude" / "memory"


def inject(context: dict) -> list:
    """回傳要注入的 atom 檔案絕對路徑列表。"""
    paths = []
    for md in MEMORY_DIR.glob("*.md"):
        if md.name != "MEMORY.md":
            paths.append(str(md))
    return paths


def extract(knowledge: list, context: dict) -> None:
    """接收萃取出的知識項目，決定如何寫入專案記憶。
    knowledge 格式: [{"type": "fact|failure|decision", "content": "...", "confidence": "[臨]"}]
    """
    # 預設：由核心引擎處理寫入，此處可加自訂邏輯
    pass


def on_session_start(context: dict) -> dict:
    """Session 初始化時呼叫，可回傳補充 lines。
    回傳格式: {"lines": ["額外注入的文字行"]}
    """
    return {}


# CLI 入口（subprocess 呼叫）
if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    ctx = json.loads(sys.stdin.read()) if not sys.stdin.isatty() else {}

    if action == "inject":
        print(json.dumps(inject(ctx)))
    elif action == "extract":
        items = ctx.get("knowledge", [])
        extract(items, ctx)
        print(json.dumps({"status": "ok"}))
    elif action == "session_start":
        print(json.dumps(on_session_start(ctx)))
    else:
        print(json.dumps({"error": f"unknown action: {action}"}))
        sys.exit(1)
