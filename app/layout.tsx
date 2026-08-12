import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "양양 5조 · Pre-IPO 투자보고서 에이전트",
  description:
    "구조적 수요 · 검증된 기술 · 고객 손익 · 측정 가능한 임팩트가 만나는 지점에만 투자합니다.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-neutral-50 text-neutral-900">
        {children}
      </body>
    </html>
  );
}
