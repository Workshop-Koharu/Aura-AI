"use client";

import { FormEvent, useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { ArrowUp, ChevronDown, Menu, Plus, Sparkles } from "lucide-react";

const suggestions = [
  "복잡한 개념을 쉽게 설명해 줘",
  "코드 작성과 디버깅을 도와줘",
  "아이디어를 구체적인 계획으로 바꿔줘",
];

export default function Home() {
  const [message, setMessage] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const router = useRouter();

  function submitMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = message.trim();
    if (!value) return;
    router.push(`/chat?message=${encodeURIComponent(value)}`);
  }

  return (
    <main className="app-shell">
      <aside className={`sidebar ${menuOpen ? "sidebar-open" : ""}`}>
        <div className="brand">
          <Image src="https://cdn.discordapp.com/attachments/1572752814092849313/1572752814554226809/aura-mark.png?ex=6b06c3f3&is=6b057273&hm=a34a78e1d0b73c92e017785b7107e030bd5fb898913d503ed2da2349c5119b12&" alt="Aura" width={29} height={29} unoptimized />
          <span>Aura</span>
        </div>
        <button className="new-chat" onClick={() => router.push("/")}><Plus size={17} /> 새 대화</button>
        <div className="sidebar-bottom">
          <div className="workspace-label">WORKSPACE</div>
          <div className="workspace-row"><span className="workspace-dot" /> 개인 작업공간</div>
          <div className="sidebar-footer">KCS · Koharu Coding Server</div>
        </div>
      </aside>

      <section className="main-panel">
        <header className="topbar">
          <button className="mobile-menu icon-button" aria-label="메뉴" onClick={() => setMenuOpen(!menuOpen)}><Menu size={20} /></button>
          <div className="model-picker">Aura <ChevronDown size={15} /></div>
          <div className="topbar-spacer" />
          <a className="topbar-link" href="mailto:admin@koharu.live">문의하기</a>
        </header>

        <div className="welcome-area">
          <div className="welcome-mark"><Sparkles size={22} /></div>
          <p className="eyebrow">YOUR AI COMPANION</p>
          <h1>무엇을 도와드릴까요?</h1>
          <p className="welcome-copy">생각을 정리하고, 새로운 것을 배우고, 만들고 싶은 것을 시작해 보세요.</p>

          <form className="composer" onSubmit={submitMessage}>
            <textarea
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  event.currentTarget.form?.requestSubmit();
                }
              }}
              placeholder="Aura에게 무엇이든 물어보세요..."
              rows={3}
              aria-label="메시지 입력"
            />
            <div className="composer-actions">
              <span className="composer-hint">Enter로 전송 · Shift + Enter로 줄바꿈</span>
              <button className="send-button" type="submit" disabled={!message.trim()} aria-label="전송"><ArrowUp size={18} /></button>
            </div>
          </form>

          <div className="suggestions">
            {suggestions.map((item) => (
              <button key={item} onClick={() => setMessage(item)}>{item}</button>
            ))}
          </div>
        </div>

        <footer className="page-footer">
          <span>Aura는 실수를 할 수 있습니다. 중요한 정보는 한 번 더 확인해 주세요.</span>
          <span>Powered by <strong>KCS</strong></span>
        </footer>
      </section>
    </main>
  );
}
