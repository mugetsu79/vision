import { AnimatePresence, motion } from "framer-motion";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type PropsWithChildren,
} from "react";

import { Toast, type ToastSpec } from "@/components/feedback/Toast";
import {
  ToastContext,
  type ShowToastInput,
} from "@/components/feedback/toast-context";
import { useReducedMotionSafe } from "@/lib/motion";

const DEFAULT_DURATION = 5000;

export function ToastProvider({ children }: PropsWithChildren) {
  const [items, setItems] = useState<ToastSpec[]>([]);
  const timers = useRef(new Map<string, ReturnType<typeof setTimeout>>());

  const dismiss = useCallback((id: string) => {
    setItems((prev) => prev.filter((item) => item.id !== id));
    const handle = timers.current.get(id);
    if (handle) {
      clearTimeout(handle);
      timers.current.delete(id);
    }
  }, []);

  const show = useCallback(
    (input: ShowToastInput) => {
      const id =
        typeof crypto !== "undefined" && "randomUUID" in crypto
          ? crypto.randomUUID()
          : `${Date.now()}-${Math.random()}`;
      const spec: ToastSpec = {
        id,
        tone: input.tone,
        message: input.message,
        description: input.description,
      };
      setItems((prev) => [...prev.slice(-2), spec]);
      const handle = setTimeout(
        () => dismiss(id),
        input.durationMs ?? DEFAULT_DURATION,
      );
      timers.current.set(id, handle);
      return id;
    },
    [dismiss],
  );

  useEffect(() => {
    const activeTimers = timers.current;
    return () => {
      activeTimers.forEach((handle) => clearTimeout(handle));
      activeTimers.clear();
    };
  }, []);

  const value = useMemo(() => ({ show, dismiss }), [show, dismiss]);
  const motionProps = useReducedMotionSafe("rise");
  const exitMotion =
    "exit" in motionProps ? motionProps.exit : { opacity: 0, y: 8 };

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed bottom-6 right-6 z-50 flex flex-col gap-2">
        <AnimatePresence>
          {items.map((spec) => (
            <motion.div
              key={spec.id}
              {...motionProps}
              exit={exitMotion}
              className="pointer-events-auto"
            >
              <Toast spec={spec} />
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}
