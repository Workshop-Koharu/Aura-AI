import type { Metadata } from "next";
import "./globals.css";
import CookieConsent from "./cookie-consent";
export const metadata:Metadata={title:"Aura — 생각을 현실로",description:"KCS - Koharu Coding Server가 제공하는 글로벌 생성형 AI 어시스턴트 Aura",metadataBase:new URL("https://aura.koharu.live"),icons:{icon:"/aura-mark.png",shortcut:"/aura-mark.png",apple:"/aura-mark.png"}};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="ko"><body>{children}<CookieConsent/></body></html>;}
