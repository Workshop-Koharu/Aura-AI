import Link from "next/link";
import { Sparkles } from "lucide-react";
import ChatClient from "./chat-client";
import Sidebar from "../sidebar";
import { createClient } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default async function ChatPage({ searchParams }: { searchParams: Promise<{ message?: string; id?: string }> }) {
  const params = await searchParams;
  let user: { id: string } | null = null;
  let supabase: Awaited<ReturnType<typeof createClient>> | null = null;
  try {
    supabase = await createClient();
    const { data } = await supabase.auth.getUser();
    user = data.user ? { id: data.user.id } : null;
  } catch {
    // Public chat remains available when auth lookup is temporarily unavailable.
  }

  if (!user || !supabase) {
    return <ChatClient initialMessage={params.message ?? ""} initialConversationId={null} initialMessages={[]} />;
  }

  let initialMessages: { role: "user" | "assistant"; content: string }[] = [];
  if (params.id) {
    const { data: conversation, error: conversationError } = await supabase.from("conversations")
      .select("id").eq("id", params.id).eq("user_id", user.id).maybeSingle();
    if (conversationError || !conversation) {
      return <main className="app-shell"><Sidebar /><section className="main-panel">
        <header className="topbar"><div className="model-picker">Aura <Sparkles size={14} /></div><div className="topbar-spacer" /><Link href="/login" className="topbar-link">로그인</Link></header>
        <div className="empty-chat"><h1>대화를 찾을 수 없습니다</h1><p>이 대화가 삭제되었거나 현재 계정에서 열 수 없습니다.</p><Link className="settings-save" href="/">새 대화 시작</Link></div>
      </section></main>;
    }
    const { data, error } = await supabase.from("messages").select("role,content")
      .eq("conversation_id", params.id).eq("user_id", user.id).order("created_at", { ascending: true });
    if (error) {
      return <main className="app-shell"><Sidebar /><section className="main-panel"><div className="empty-chat">
        <h1>대화를 불러오지 못했습니다</h1><p>잠시 후 다시 시도해 주세요.</p><Link className="settings-save" href="/">새 대화 시작</Link>
      </div></section></main>;
    }
    initialMessages = (data ?? []).filter((m): m is { role: "user" | "assistant"; content: string } =>
      ["user", "assistant"].includes(m.role) && typeof m.content === "string");
  }
  return <ChatClient initialMessage={params.message ?? ""} initialConversationId={params.id ?? null} initialMessages={initialMessages} />;
}
