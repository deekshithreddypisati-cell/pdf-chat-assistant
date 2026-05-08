import { useState } from "react";
import type { ChatMessage } from "../types";

interface Props {
  workspaceId: string | null;
}

export default function ChatPanel({ workspaceId }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);

  const askStreaming = async () => {
    if (!workspaceId || !question.trim()) return;

    const currentQuestion = question;

    setMessages((prev) => [
      ...prev,
      { role: "user", content: currentQuestion },
      { role: "assistant", content: "", citations: [], evidence_quotes: [] },
    ]);

    setQuestion("");
    setLoading(true);

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/chat_stream?workspace_id=${workspaceId}&q=${encodeURIComponent(currentQuestion)}`
      );

      if (!response.body) throw new Error("No response stream");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      let buffer = "";
      let answer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.trim()) continue;

          try {
            const event = JSON.parse(line);

            if (event.type === "token") {
              answer += event.content;

              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  ...updated[updated.length - 1],
                  content: answer,
                };
                return updated;
              });
            }

            if (event.type === "citations") {
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  ...updated[updated.length - 1],
                  citations: event.data || [],
                };
                return updated;
              });
            }
          } catch (err) {
            console.error("Invalid JSON line:", line);
          }
        }
      }

      const fullRes = await fetch(
        `http://127.0.0.1:8000/ask?q=${encodeURIComponent(currentQuestion)}&workspace_id=${workspaceId}`
      );
      const fullData = await fullRes.json();

      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          ...updated[updated.length - 1],
          citations: fullData.citations || [],
          evidence_quotes: fullData.evidence_quotes || [],
        };
        return updated;
      });
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel chat-panel">
      <h3>Chat</h3>

      <div className="chat-messages">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={msg.role === "user" ? "message user" : "message assistant"}
          >
            <strong>{msg.role === "user" ? "You" : "Assistant"}:</strong>
            <p>{msg.content}</p>

            {msg.citations && msg.citations.length > 0 && (
              <div className="citations">
                {msg.citations.map((c, i) => (
                  <span key={i} className="citation-pill">
                    Page {c.page_num}
                  </span>
                ))}
              </div>
            )}

            {msg.evidence_quotes && msg.evidence_quotes.length > 0 && (
              <div className="quotes-box">
                <strong>Evidence quotes:</strong>
                <ul className="quotes-list">
                  {msg.evidence_quotes.map((q, i) => (
                    <li key={i}>
                      “{q.quote}” <span className="quote-page">(p.{q.page_num})</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="chat-input-row">
        <input
          type="text"
          placeholder="Ask a question about your PDFs..."
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") askStreaming();
          }}
        />

        <button onClick={askStreaming} disabled={!workspaceId || loading}>
          {loading ? "Thinking..." : "Send"}
        </button>
      </div>
    </div>
  );
}