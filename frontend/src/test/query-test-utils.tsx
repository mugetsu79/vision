import type { PropsWithChildren } from "react";
import { useEffect } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

export function createTestQueryWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return function Wrapper({ children }: PropsWithChildren) {
    useEffect(() => {
      return () => {
        queryClient.clear();
      };
    }, []);

    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}
