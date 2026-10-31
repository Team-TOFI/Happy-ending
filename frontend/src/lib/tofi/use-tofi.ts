"use client";
import { useSyncExternalStore } from "react";
import { getSnapshot, getServerSnapshot, subscribe } from "./store";
export function useTofi() {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
