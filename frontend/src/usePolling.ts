import { useState, useEffect, useRef, useCallback } from "react";

export interface PollingResult<T> {
  data: T | null;
  error: Error | null;
  isLoading: boolean;
  isStale: boolean;
  refresh: () => void;
}

export function usePolling<T>(
  fetcher: (signal: AbortSignal) => Promise<T>,
  intervalMs: number
): PollingResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isStale, setIsStale] = useState<boolean>(false);

  const lastSuccessRef = useRef<number>(0);
  const activeAbortRef = useRef<AbortController | null>(null);
  const isMountedRef = useRef<boolean>(true);

  const executeFetch = useCallback(async () => {
    if (activeAbortRef.current) {
      activeAbortRef.current.abort();
    }
    const controller = new AbortController();
    activeAbortRef.current = controller;

    try {
      const result = await fetcher(controller.signal);
      if (!isMountedRef.current) return;
      setData(result);
      setError(null);
      lastSuccessRef.current = Date.now();
      setIsStale(false);
      setIsLoading(false);
    } catch (err: unknown) {
      if (!isMountedRef.current) return;
      if (err instanceof DOMException && err.name === "AbortError") {
        return;
      }
      setError(err instanceof Error ? err : new Error(String(err)));
      setIsLoading(false);
    } finally {
      if (activeAbortRef.current === controller) {
        activeAbortRef.current = null;
      }
    }
  }, [fetcher]);

  useEffect(() => {
    isMountedRef.current = true;
    executeFetch();

    const intervalId = setInterval(executeFetch, intervalMs);

    const staleCheckId = setInterval(() => {
      if (lastSuccessRef.current > 0 && Date.now() - lastSuccessRef.current >= 10000) {
        setIsStale(true);
      }
    }, 1000);

    return () => {
      isMountedRef.current = false;
      clearInterval(intervalId);
      clearInterval(staleCheckId);
      if (activeAbortRef.current) {
        activeAbortRef.current.abort();
      }
    };
  }, [executeFetch, intervalMs]);

  return { data, error, isLoading, isStale, refresh: executeFetch };
}
