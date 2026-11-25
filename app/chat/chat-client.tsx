"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { ArrowUp, Sparkles, UserRound } from "lucide-react";
import Sidebar from "../sidebar";

type Message = { role: "user" | "assistant"; content: string };

export default function ChatClient({ initialMessage, initialConversationId, initialMessages = [] }: {
  initialMessage: string;
  initialConversationId: string | null;
  initialMessages?: Message[];
}) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [, setConversationId] = useState<string | null>(initialConversationId);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const sentInitial = useRef(false);
  const sending = useRef(false);
  const conversationIdRef = useRef<string | null>(initialConversationId);
  const messagesRef = useRef<Message[]>(initialMessages);

  useEffect(() => { messagesRef.current = messages; }, [messages]);
  useEffect(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), [messages, loading]);

  const applyConversationId = useCallback((id: string) => {
    conversationIdRef.current = id;
    setConversationId(id);
    const target = `/chat?id=${encodeURIComponent(id)}`;
    if (window.location.pathname + window.location.search !== target) {
      window.history.replaceState(null, "", target);
    }
    window.dispatchEvent(new Event("aura:conversations-refresh"));
  }, []);

  const send = useCallback(async (raw: string) => {
    const content = raw.trim();
    if (!content || sending.current) return;
    sending.current = true;
    const previous = messagesRef.current;
    const next: Message[] = [...previous, { role: "user", content }];
    messagesRef.current = next;
    setMessages(next);
    setDraft("");
    setError("");
    setLoading(true);

    try {
      const activeId = conversationIdRef.current;

      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "application/json" },
        cache: "no-store",
        body: JSON.stringify({ messages: next, conversationId: activeId }),
      });
      const data = await response.json().catch(() => null) as {
        content?: unknown; conversationId?: unknown; error?: unknown;
      } | null;

      if (typeof data?.conversationId === "string" && data.conversationId !== conversationIdRef.current) {
        applyConversationId(data.conversationId);
      } else {
        window.dispatchEvent(new Event("aura:conversations-refresh"));
      }
      if (!response.ok) {
        throw new Error(typeof data?.error === "string" ? data.error : `요청 실패 (HTTP ${response.status})`);
      }
      if (typeof data?.content !== "string" || !data.content.trim()) {
        throw new Error("모델 서버가 빈 답변을 반환했습니다. 잠시 후 다시 시도해 주세요.");
      }

      const completed: Message[] = [...next, { role: "assistant", content: data.content }];
      messagesRef.current = completed;
      setMessages(completed);
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : "알 수 없는 오류가 발생했습니다.";
      setError(message);
    } finally {
      sending.current = false;
      setLoading(false);
    }
  }, [applyConversationId]);

  useEffect(() => {
    if (sentInitial.current) return;
    let queued = "";
    try {
      queued = sessionStorage.getItem("aura.pending-message") || "";
      if (queued) sessionStorage.removeItem("aura.pending-message");
    } catch { /* session storage may be unavailable */ }
    const firstMessage = queued || initialMessage;
    if (!firstMessage) return;
    sentInitial.current = true;
    void send(firstMessage);
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
          {messages.length === 0 && !loading && <div className="empty-chat"><div className="welcome-mark"><Sparkles size={22} /></div><h1>무엇이든 물어보세요</h1><p>Aura와 새로운 대화를 시작해 보세요.</p></div>}
          {messages.map((message, index) => <article className={`message-row ${message.role}`} key={index}><div className="message-avatar">{message.role === "assistant" ? <Sparkles size={16} /> : <UserRound size={16} />}</div><div className="message-body"><div className="message-name">{message.role === "assistant" ? "Aura" : "나"}</div><div className="message-text">{message.content}</div></div></article>)}
          {loading && <article className="message-row assistant"><div className="message-avatar"><Sparkles size={16} /></div><div className="message-body"><div className="message-name">Aura</div><div className="typing"><i /><i /><i /></div></div></article>}
          {error && <div className="chat-error" role="alert">{error}</div>}
          <div ref={bottomRef} />
        </div>
        <div className="chat-composer-wrap"><form className="composer" onSubmit={submit}><textarea value={draft} onChange={event => setDraft(event.target.value)} onKeyDown={event => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} placeholder="메시지를 입력하세요..." rows={2} aria-label="메시지 입력" /><div className="composer-actions"><span className="composer-hint">Enter로 전송 · Shift + Enter로 줄바꿈</span><button className="send-button" type="submit" disabled={!draft.trim() || loading} aria-label="전송"><ArrowUp size={18} /></button></div></form><p className="chat-disclaimer">Aura는 실수를 할 수 있습니다. 중요한 정보는 한 번 더 확인해 주세요.</p></div>
      </section>
    </main>
  );
}
