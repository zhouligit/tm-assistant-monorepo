import React from "react";
import ReactDOM from "react-dom/client";
import { useMemo, useState } from "react";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  confidence?: number;
  handoffSuggested?: boolean;
};

type ApiResponse<T> = {
  code: number;
  message: string;
  request_id: string;
  data: T;
};

type WidgetConfig = {
  baseUrl: string;
  visitorId: string;
  channel: string;
};

function normalizeBaseUrl(raw: string): string {
  return raw.replace(/\/+$/, "");
}

const ENV_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "";
const WINDOW_BASE_URL = (window as { TM_CHAT_WIDGET_BASE_URL?: string }).TM_CHAT_WIDGET_BASE_URL ?? "";
const RESOLVED_BASE_URL = normalizeBaseUrl(WINDOW_BASE_URL || ENV_BASE_URL || window.location.origin);

const DEFAULT_CONFIG: WidgetConfig = {
  baseUrl: RESOLVED_BASE_URL,
  visitorId: `visitor_${Math.random().toString(36).slice(2, 10)}`,
  channel: "web_widget",
};

async function createSession(config: WidgetConfig): Promise<string> {
  const res = await fetch(`${config.baseUrl}/api/v1/tm/chat/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ channel: config.channel, visitor_id: config.visitorId }),
  });
  if (!res.ok) {
    throw new Error(`创建会话失败: HTTP ${res.status}`);
  }
  const payload = (await res.json()) as ApiResponse<{ session_id: string }>;
  return payload.data.session_id;
}

async function sendMessage(config: WidgetConfig, sessionId: string, content: string): Promise<{
  reply: string;
  confidence?: number;
  handoffSuggested?: boolean;
}> {
  const res = await fetch(`${config.baseUrl}/api/v1/tm/chat/sessions/${sessionId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role: "user", content }),
  });
  if (!res.ok) {
    throw new Error(`发送消息失败: HTTP ${res.status}`);
  }
  const payload = (await res.json()) as ApiResponse<{
    reply: string;
    confidence?: number;
    handoff_suggested?: boolean;
  }>;
  return {
    reply: payload.data.reply,
    confidence: payload.data.confidence,
    handoffSuggested: payload.data.handoff_suggested,
  };
}

function App() {
  const config = useMemo(() => DEFAULT_CONFIG, []);
  const [sessionId, setSessionId] = useState<string>("");
  const [handoffActive, setHandoffActive] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: "assistant", content: "你好，我是课程顾问助手。请问你想咨询哪个课程？" },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || loading) return;
    setError("");
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    try {
      setLoading(true);
      let sid = sessionId;
      if (!sid) {
        sid = await createSession(config);
        setSessionId(sid);
      }
      const result = await sendMessage(config, sid, trimmed);
      if (result.handoffSuggested) {
        setHandoffActive(true);
      }
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: result.reply,
          confidence: result.confidence,
          handoffSuggested: result.handoffSuggested,
        },
      ]);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        width: 360,
        border: "1px solid #d9d9d9",
        borderRadius: 12,
        background: "#fff",
        boxShadow: "0 8px 24px rgba(0,0,0,0.08)",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        fontFamily: "Arial, sans-serif",
      }}
    >
      <div style={{ padding: "12px 14px", background: "#1677ff", color: "#fff", fontWeight: 600 }}>
        教育课程咨询助手
        <div style={{ marginTop: 4, fontSize: 12, fontWeight: 400, opacity: 0.95 }}>
          会话ID: {sessionId || "-"} {handoffActive ? "| 当前状态：转人工跟进中" : ""}
        </div>
      </div>
      <div style={{ padding: 12, height: 340, overflowY: "auto", background: "#fafafa" }}>
        {messages.map((msg, idx) => (
          <div key={idx} style={{ marginBottom: 10, textAlign: msg.role === "user" ? "right" : "left" }}>
            <div
              style={{
                display: "inline-block",
                maxWidth: "84%",
                background: msg.role === "user" ? "#1677ff" : "#fff",
                color: msg.role === "user" ? "#fff" : "#222",
                border: msg.role === "user" ? "none" : "1px solid #eee",
                borderRadius: 10,
                padding: "8px 10px",
                lineHeight: 1.5,
              }}
            >
              <div>{msg.content}</div>
              {msg.role === "assistant" && typeof msg.confidence === "number" && (
                <div style={{ marginTop: 6, fontSize: 12, color: "#666" }}>
                  置信度: {msg.confidence.toFixed(2)}{" "}
                  {msg.handoffSuggested ? <span style={{ color: "#cf1322" }}>| 已建议转人工</span> : null}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
      <div style={{ padding: 10, borderTop: "1px solid #f0f0f0" }}>
        {error ? <div style={{ color: "#cf1322", fontSize: 12, marginBottom: 8 }}>{error}</div> : null}
        {handoffActive ? (
          <div style={{ color: "#cf1322", fontSize: 12, marginBottom: 8 }}>
            已进入人工跟进队列，客服将尽快联系你。你也可以继续补充问题信息。
          </div>
        ) : null}
        <div style={{ display: "flex", gap: 8 }}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                void handleSend();
              }
            }}
            placeholder="输入你的问题..."
            style={{
              flex: 1,
              border: "1px solid #d9d9d9",
              borderRadius: 8,
              padding: "8px 10px",
              outline: "none",
            }}
          />
          <button
            onClick={() => void handleSend()}
            disabled={loading}
            style={{
              background: "#1677ff",
              color: "#fff",
              border: "none",
              borderRadius: 8,
              padding: "0 14px",
              cursor: "pointer",
            }}
          >
            {loading ? "发送中" : "发送"}
          </button>
        </div>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
