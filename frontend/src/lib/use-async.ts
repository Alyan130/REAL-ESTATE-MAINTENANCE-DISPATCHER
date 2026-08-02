"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { errorMessage } from "@/lib/errors";

interface AsyncState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
}

interface UseAsyncResult<T> extends AsyncState<T> {
  /** Re-run the loader. `silent` keeps the current data on screen (used by polling). */
  reload: (options?: { silent?: boolean }) => Promise<void>;
  setData: (data: T) => void;
}

/**
 * Load data on mount and whenever `deps` change.
 *
 * Results from a superseded request are discarded, so a fast filter change can't
 * be overwritten by a slower earlier response.
 */
export function useAsync<T>(
  loader: () => Promise<T>,
  deps: unknown[],
): UseAsyncResult<T> {
  const [state, setState] = useState<AsyncState<T>>({
    data: null,
    error: null,
    loading: true,
  });

  const loaderRef = useRef(loader);
  const requestId = useRef(0);
  const mounted = useRef(true);

  // Declared before the effect that calls it, so `run` always reads the current
  // loader. The initial useRef value already covers the first render.
  useEffect(() => {
    loaderRef.current = loader;
  }, [loader]);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const run = useCallback(
    async (options?: { silent?: boolean }) => {
      const id = ++requestId.current;

      if (!options?.silent) {
        setState((previous) => ({ ...previous, loading: true, error: null }));
      }

      try {
        const data = await loaderRef.current();
        if (!mounted.current || id !== requestId.current) return;
        setState({ data, error: null, loading: false });
      } catch (error) {
        if (!mounted.current || id !== requestId.current) return;
        setState((previous) => ({
          data: previous.data,
          error: errorMessage(error),
          loading: false,
        }));
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    deps,
  );

  useEffect(() => {
    void run();
  }, [run]);

  const setData = useCallback((data: T) => {
    setState({ data, error: null, loading: false });
  }, []);

  return { ...state, reload: run, setData };
}

/**
 * Call `onTick` on an interval while `active`, then give up after `maxTicks`.
 *
 * Approval and photo upload both finish in the background with no push channel,
 * so the UI polls — but only for as long as it's plausibly still working.
 */
export function usePolling(
  active: boolean,
  onTick: () => void,
  {
    intervalMs = 3000,
    maxTicks = 20,
    resetKey,
  }: { intervalMs?: number; maxTicks?: number; resetKey?: unknown } = {},
): void {
  const tickRef = useRef(onTick);

  useEffect(() => {
    tickRef.current = onTick;
  }, [onTick]);

  useEffect(() => {
    if (!active) return;

    let ticks = 0;
    const timer = setInterval(() => {
      ticks += 1;
      if (ticks > maxTicks) {
        clearInterval(timer);
        return;
      }
      tickRef.current();
    }, intervalMs);

    return () => clearInterval(timer);
    // `resetKey` restarts the tick budget. A chat page polls for a reply, gives
    // up, and would then sit dead for the rest of the session — passing the
    // last-sent timestamp means each new message buys a fresh window. Raising
    // maxTicks instead would just poll a dead thread forever.
  }, [active, intervalMs, maxTicks, resetKey]);
}
