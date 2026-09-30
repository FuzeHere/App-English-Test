import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CEST Practice Simulator — Persiapan Ujian Bahasa Inggris (A1–C1)",
  description:
    "Simulator latihan dan ujian adaptif berbasis komputer untuk Reading, Listening, dan Writing (A1–C1) dengan mesin 1PL IRT Rasch dan evaluasi AI.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="id">
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased">
        {children}
      </body>
    </html>
  );
}
