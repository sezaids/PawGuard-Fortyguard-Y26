import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PawGuard | Safer walks, happier dogs",
  description: "Dog heat-safety and smart walk planning.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
