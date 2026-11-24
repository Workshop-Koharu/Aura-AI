import ChatClient from "./chat-client";

export const instant = false;

export default async function ChatPage({ searchParams }: { searchParams: Promise<{ message?: string }> }) {
  const params = await searchParams;
  return <ChatClient initialMessage={params.message ?? ""} />;
}
