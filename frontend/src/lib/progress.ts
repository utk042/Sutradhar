/**
 * Following a document's checks over Server-Sent Events.
 *
 * The connection is the fast path, not the source of truth: when it closes, or
 * if it never opens at all, the caller re-fetches the document. A dropped stream
 * on a government network then costs a moment, not correctness.
 *
 * Events carry a `label_key`, never a sentence, so the wording comes from the
 * locale files and switching language changes nothing on the server.
 */

export interface CheckProgress {
  name: string;
  labelKey: string;
  state: 'running' | 'done' | 'failed';
  durationMs?: number;
  findings?: number;
}

export interface ProgressState {
  phase: 'connecting' | 'reading' | 'checking' | 'complete';
  checks: CheckProgress[];
}

export const INITIAL_PROGRESS: ProgressState = {phase: 'connecting', checks: []};

type Payload = {
  kind: string;
  name?: string;
  label_key?: string;
  duration_ms?: number;
  findings?: number;
  status?: string;
};

/** Fold one event into the progress state. Pure, so it can be reasoned about. */
export function reduceProgress(state: ProgressState, payload: Payload): ProgressState {
  switch (payload.kind) {
    case 'reading':
      return {...state, phase: 'reading'};

    case 'checks_started':
      return {...state, phase: 'checking'};

    case 'check_started': {
      if (!payload.name || !payload.label_key) return state;
      // Replayed events can repeat a check that is already listed.
      if (state.checks.some((c) => c.name === payload.name)) return state;
      return {
        ...state,
        phase: 'checking',
        checks: [
          ...state.checks,
          {name: payload.name, labelKey: payload.label_key, state: 'running'}
        ]
      };
    }

    case 'check_finished':
    case 'check_failed': {
      if (!payload.name) return state;
      const finished: CheckProgress['state'] =
        payload.kind === 'check_failed' ? 'failed' : 'done';
      return {
        ...state,
        checks: state.checks.map((c) =>
          c.name === payload.name
            ? {...c, state: finished, durationMs: payload.duration_ms, findings: payload.findings}
            : c
        )
      };
    }

    case 'complete':
      return {...state, phase: 'complete'};

    default:
      return state;
  }
}

/**
 * Subscribe to a document's progress.
 *
 * Returns a function that closes the connection. `onComplete` fires once the run
 * has finished — and also when the connection fails, because in both cases the
 * caller's next move is the same: fetch the document and render the result.
 */
export function watchProgress(
  documentId: number,
  onEvent: (payload: Payload) => void,
  onComplete: () => void
): () => void {
  // Same-origin: Next.js proxies /api, so the session cookie is sent and
  // EventSource needs no special handling.
  const source = new EventSource(`/api/documents/${documentId}/events`);
  let closed = false;

  const close = () => {
    if (closed) return;
    closed = true;
    source.close();
  };

  const handle = (event: MessageEvent) => {
    let payload: Payload;
    try {
      payload = JSON.parse(event.data);
    } catch {
      return;
    }
    onEvent(payload);
    if (payload.kind === 'complete') {
      close();
      onComplete();
    }
  };

  for (const name of [
    'status',
    'reading',
    'checks_started',
    'check_started',
    'check_finished',
    'check_failed',
    'complete'
  ]) {
    source.addEventListener(name, handle as EventListener);
  }

  source.onerror = () => {
    // EventSource retries by itself, but a run is short: rather than reconnect
    // into a finished run, close and let the caller fetch the document.
    close();
    onComplete();
  };

  return close;
}
