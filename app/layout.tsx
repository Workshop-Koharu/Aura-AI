import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Aura — 생각을 현실로",
  description: "KCS가 만드는 AI 어시스턴트 Aura",
  metadataBase: new URL("https://aura.koharu.live"),
  icons: {
    icon: "https://cdn.discordapp.com/attachments/1572752814092849313/1572752814554226809/aura-mark.png?ex=6b06c3f3&is=6b057273&hm=a34a78e1d0b73c92e017785b7107e030bd5fb898913d503ed2da2349c5119b12&",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
