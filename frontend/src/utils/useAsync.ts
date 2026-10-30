import { useCallback, useEffect, useRef, useState, type DependencyList } from "react";
import { getErrorMessage } from "../api/client";

interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

/** Runs an async loader, re-running whenever `deps` change; ignores stale responses. */
export function useAsync<T>(loader: () => Promise<T>, deps: DependencyList): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);
  const requestId = useRef(0);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(loader, deps);

  useEffect(() => {
    const id = ++requestId.current;
    setLoading(true);
    setError(null);
    run()
      .then((result) => id === requestId.current && setData(result))
      .catch((err) => id === requestId.current && setError(getErrorMessage(err)))
      .finally(() => id === requestId.current && setLoading(false));
  }, [run, nonce]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  return { data, loading, error, reload };
}
