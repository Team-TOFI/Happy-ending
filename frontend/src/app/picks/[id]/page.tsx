import type { Metadata } from "next";
import { OutfitDetailScreen } from "@/components/tofi/outfit-detail";
export const metadata: Metadata = { title: "아이템과 수정" };
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <OutfitDetailScreen key={id} id={id} />;
}
