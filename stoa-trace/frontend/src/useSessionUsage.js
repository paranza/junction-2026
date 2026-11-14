import { useCallback, useEffect, useRef, useState } from 'react';
import { acceptUsageSnapshot, inferenceSessionId, usagePending } from './inferenceUsage.js';

export default function useSessionUsage(request, asking, threadId) {
  const [sessionId] = useState(() => {
    if (threadId) return threadId;
    let storage;
    try { storage = window.sessionStorage; } catch { /* Browser storage can be unavailable. */ }
    return inferenceSessionId(storage);
  });
  const [snapshot, setSnapshot] = useState(null);
  const [unavailable, setUnavailable] = useState(false);
  const [trackUntil, setTrackUntil] = useState(0);
  const mounted = useRef(true);
  const refresh = useCallback(async () => {
    try {
      const next = await request(`/api/usage?session_id=${encodeURIComponent(sessionId)}`);
      if (!mounted.current) return;
      setSnapshot(current => acceptUsageSnapshot(current, next, sessionId));
      setUnavailable(false);
    } catch {
      if (mounted.current) setUnavailable(true);
    }
  }, [request, sessionId]);
  const trackRequest = useCallback(() => {
    // An aborted browser request can still finish on the server. Keep checking
    // long enough to observe its pending row, then follow it to completion.
    setTrackUntil(Date.now() + 20_000);
    refresh();
  }, [refresh]);
  useEffect(() => {
    mounted.current = true;
    refresh();
    const onFocus = () => refresh();
    window.addEventListener('focus', onFocus);
    return () => { mounted.current = false; window.removeEventListener('focus', onFocus); };
  }, [refresh]);
  const pending = usagePending(snapshot);
  useEffect(() => {
    if (!asking && !pending && trackUntil <= Date.now()) return;
    const timer = window.setInterval(() => {
      if (!asking && !pending && trackUntil <= Date.now()) { window.clearInterval(timer); return; }
      refresh();
    }, 2000);
    return () => window.clearInterval(timer);
  }, [asking, pending, refresh, trackUntil]);
  return { sessionId, snapshot, unavailable, refresh, trackRequest };
}
