# bridge-vague-ping-response

- Scope: shared
- Audience: feedback
- Author: wellstseng
- Confidence: [臨]
- Trigger: vague ping, crawlertool專案代理, bridge 上線, Discord bridge 打招呼, 溫蒂, AskUserQuestion 菜單, 待命
- Created-at: 2026-07-02
- Related: esun-realtime-monitoring, feedback-workflow-discipline
- Source: unknown 2026-07-02（原對話已逾保留期）

## 知識

- [臨] CatClaw Discord bridge 收到模糊招呼（如 溫蒂 只丟「crawlertool專案代理」、或 bridge 上線回放）→ 回 1–3 行純文字後待命；不要開 AskUserQuestion 強制菜單、不要主動跑工具（Bash echo / discord MCP）
- [臨] 本 session 這三種動作（capability rundown 後接 AskUserQuestion、discord MCP、Bash echo）被使用者連續中斷/拒絕三次
- [臨] stdout 回覆會由 CatClaw 自動轉送 Discord，不需額外呼叫 discord 工具
- [臨] bridge 回放的『judy-cli 已上線』是 agent 自己的系統訊息，非真實請求，勿當任務處理
- [臨] 溫蒂（Wendy）與 Wells（wellstseng）是不同人，共用同一頻道

## 行動

- 模糊招呼/ping → 短文字回覆即停，待使用者給明確任務再升級到菜單或工具
- bridge 上線回放內容若為 agent 自身通知 → 待命，不動工具
