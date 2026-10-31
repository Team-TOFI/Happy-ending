import type { Metadata } from "next";
import { WardrobeScreen } from "@/components/tofi/wardrobe";
export const metadata: Metadata = { title: "내 옷장" };
export default function Page() {
  return <WardrobeScreen />;
}
