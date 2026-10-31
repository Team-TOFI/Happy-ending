import type { Metadata } from "next";
import type { ReactNode } from "react";
import { TofiShell } from "@/components/tofi/shell";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "tofi — 취향은 선명하게, 쇼핑은 단순하게",
    template: "%s — tofi",
  },
  description: "바디타입과 추구미를 바탕으로 T.P.O에 맞는 스타일을 제안합니다.",
  icons: {
    icon: [
      { url: "/brand/tofi-favicon-v2.ico", type: "image/x-icon", sizes: "any" },
    ],
    shortcut: "/brand/tofi-favicon-v2.ico",
    apple: [
      {
        url: "/brand/tofi-app-icon-v2.png",
        type: "image/png",
        sizes: "1024x1024",
      },
    ],
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ko">
      <body>
        <TofiShell>{children}</TofiShell>
      </body>
    </html>
  );
}
