"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowUp, Sparkles, UserRound } from "lucide-react";
import Sidebar from "../sidebar";

type Message = { role: "user" | "assistant"; content: string };

export default function ChatClient({ initialMessage, initialConversationId, initialMessages = [] }: { initialMessage: string; initialConversationId: string | null; initialMessages?: Message[] }) {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(initialConversationId);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const sentInitial = useRef(false);

  useEffect(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), [messages, loading]);

  const send = useCallback(async (raw: string) => {
    const content = raw.trim();
    if (!content || loading) return;
    const next = [...messages, { role: "user" as const, content }];
    setMessages(next);
    setDraft("");
    setError("");
    setLoading(true);
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: next, conversationId }),
      });
      const data = await response.json();
      if (data.conversationId) { setConversationId(data.conversationId); if (!conversationId) router.replace("/chat?id="+encodeURIComponent(data.conversationId)); }
      if (!response.ok) throw new Error(data.error || "응답을 가져오지 못했습니다.");
      setMessages([...next, { role: "assistant", content: data.content }]);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "알 수 없는 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  }, [conversationId, loading, messages, router]);

  useEffect(() => {
    if (initialMessage && !sentInitial.current) {
      sentInitial.current = true;
      void send(initialMessage);
    }
  }, [initialMessage, send]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void send(draft);
  }

  return (
    <main className="app-shell">
      <Sidebar />
      <section className="main-panel">
        <header className="topbar"><div className="model-picker">Aura <Sparkles size={14} /></div><div className="topbar-spacer" /><a className="topbar-link" href="mailto:admin@koharu.live">문의하기</a></header>
        <div className="chat-content">
          {messages.length === 0 && <div className="empty-chat"><div className="welcome-mark"><Sparkles size={22} /></div><h1>무엇이든 물어보세요</h1><p>Aura와 새로운 대화를 시작해 보세요.</p></div>}
          {messages.map((message, index) => <article className={`message-row ${message.role}`} key={index}><div className="message-avatar">{message.role === "assistant" ? <Sparkles size={16} /> : <UserRound size={16} />}</div><div className="message-body"><div className="message-name">{message.role === "assistant" ? "Aura" : "나"}</div><div className="message-text">{message.content}</div></div></article>)}
          {loading && <article className="message-row assistant"><div className="message-avatar"><Sparkles size={16} /></div><div className="message-body"><div className="message-name">Aura</div><div className="typing"><i /><i /><i /></div></div></article>}
          {error && <div className="chat-error">{error}</div>}
          <div ref={bottomRef} />
        </div>
        <div className="chat-composer-wrap"><form className="composer" onSubmit={submit}><textarea value={draft} onChange={event => setDraft(event.target.value)} onKeyDown={event => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} placeholder="메시지를 입력하세요..." rows={2} aria-label="메시지 입력" /><div className="composer-actions"><span className="composer-hint">Enter로 전송 · Shift + Enter로 줄바꿈</span><button className="send-button" type="submit" disabled={!draft.trim() || loading} aria-label="전송"><ArrowUp size={18} /></button></div></form><p className="chat-disclaimer">Aura는 실수를 할 수 있습니다. 중요한 정보는 한 번 더 확인해 주세요.</p></div>
      </section>
    </main>
  );
}
