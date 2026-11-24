import {redirect} from "next/navigation";
import ChatClient from "./chat-client";
import {createClient} from "@/lib/supabase/server";
export const instant=false;
export default async function ChatPage({searchParams}:{searchParams:Promise<{message?:string;id?:string}>}){
 const params=await searchParams;const supabase=await createClient();const {data:{user}}=await supabase.auth.getUser();
 if(!user){const target="/chat"+(params.message?"?message="+encodeURIComponent(params.message):params.id?"?id="+encodeURIComponent(params.id):"");redirect("/login?next="+encodeURIComponent(target));}
 let initialMessages:{role:"user"|"assistant";content:string}[]=[];
 if(params.id){const {data:conversation}=await supabase.from("conversations").select("id").eq("id",params.id).eq("user_id",user.id).maybeSingle();if(!conversation)redirect("/");const {data}=await supabase.from("messages").select("role,content").eq("conversation_id",params.id).eq("user_id",user.id).order("created_at",{ascending:true});initialMessages=(data??[]).filter((m):m is {role:"user"|"assistant";content:string}=>["user","assistant"].includes(m.role)&&typeof m.content==="string");}
 return <ChatClient initialMessage={params.message??""} initialConversationId={params.id??null} initialMessages={initialMessages}/>;
}
