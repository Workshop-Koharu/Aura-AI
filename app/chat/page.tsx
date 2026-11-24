import {redirect} from "next/navigation";
import ChatClient from "./chat-client";
import {createClient} from "@/lib/supabase/server";
export const instant=false;
export default async function ChatPage({searchParams}:{searchParams:Promise<{message?:string}>}){
 const params=await searchParams;const supabase=await createClient();const {data:{user}}=await supabase.auth.getUser();
 if(!user){const target="/chat"+(params.message?"?message="+encodeURIComponent(params.message):"");redirect("/login?next="+encodeURIComponent(target));}
 return <ChatClient initialMessage={params.message??""}/>;
}
