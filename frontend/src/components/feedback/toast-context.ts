import { createContext, useContext } from "react";

import type { ToastSpec } from "@/components/feedback/Toast";

export type ShowToastInput = Omit<ToastSpec, "id"> & { durationMs?: number };

export type ToastContextValue = {
  show: (input: ShowToastInput) => string;
  dismiss: (id: string) => void;
};

export const ToastContext = createContext<ToastContextValue | null>(null);

export function useToastContext() {
  const value = useContext(ToastContext);
  if (!value) {
    throw new Error("useToast must be used inside <ToastProvider>");
  }
  return value;
}
