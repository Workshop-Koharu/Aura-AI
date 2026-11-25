import {redirect} from "next/navigation";import {createClient} from "@/lib/supabase/server";import SettingsClient from "./settings-client";
export const dynamic="force-dynamic";export const revalidate=0;export const metadata={title:"설정 · Aura"};
export default async function SettingsPage(){const s=await createClient();const {data:{user}}=await s.auth.getUser();if(!user)redirect("/login?next=%2Fsettings");return <SettingsClient email={user.email??""} initialName={String(user.user_metadata?.display_name??user.user_metadata?.full_name??"")}/>;}
