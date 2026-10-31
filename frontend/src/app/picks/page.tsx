import type { Metadata } from "next";
import { PicksScreen } from "@/components/tofi/picks";
export const metadata: Metadata = { title: "Tofi Pick" };
export default function Page() {
  return <PicksScreen />;
}
