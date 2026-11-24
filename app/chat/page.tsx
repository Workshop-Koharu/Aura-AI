import {redirect} from "next/navigation";
import ChatClient from "./chat-client";
import {createClient} from "@/lib/supabase/server";
export const instant=false;
export default async function ChatPage({searchParams}:{searchParams:Promise<{message?:string}>}){const supabase=await createClient();const {data:{user}}=await supabase.auth.getUser();if(!user)redirect("/login?next=/chat");const params=await searchParams;return <ChatClient initialMessage={params.message??""}/>;}
