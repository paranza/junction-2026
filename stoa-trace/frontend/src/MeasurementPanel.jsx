import React, { useEffect, useRef, useState } from 'react';
import { measurementDraft, parseMeasurementPoints, validMeasurementPoints } from './measurementState.js';
import './MeasurementPanel.css';

const endpoint = (documentId, page) => `/api/documents/${encodeURIComponent(documentId)}/measurement-context?page=${page}`;

async function responseJson(response) {
  let body;
  try { body = await response.json(); } catch { throw new Error('The measurement service returned an unreadable response.'); }
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'The measurement could not be saved. Check the reference and outline.');
  return body;
}

export default function MeasurementPanel({ documentId, page, captureMode, points = [], onCaptureModeChange,
  onClearPoints, onAnswer, disabled = false }) {
  const [context, setContext] = useState(null);
  const [reference, setReference] = useState([]);
  const [value, setValue] = useState('');
  const [unit, setUnit] = useState('m');
  const [kind, setKind] = useState('area');
  const [manualReference, setManualReference] = useState('');
  const [manualGeometry, setManualGeometry] = useState('');
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');
  const [busy, setBusy] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const identity = `${documentId || ''}:${page}`;
  const currentIdentity = useRef(identity);
  currentIdentity.current = identity;
  const actions = useRef({ onCaptureModeChange, onClearPoints, onAnswer });
  actions.current = { onCaptureModeChange, onClearPoints, onAnswer };
  const measurementRequest = useRef(null);
  const requestSequence = useRef(0);

  useEffect(() => {
    const controller = new AbortController();
    let live = true;
    requestSequence.current += 1;
    measurementRequest.current?.abort();
    setContext(null); setReference([]); setValue(''); setManualReference(''); setManualGeometry('');
    setError(''); setStatus(''); setBusy(false);
    actions.current.onClearPoints?.();
    actions.current.onCaptureModeChange?.(null);
    if (documentId) {
      fetch(endpoint(documentId, page), { signal: controller.signal })
        .then(responseJson)
        .then(body => { if (live && currentIdentity.current === identity) setContext(body); })
        .catch(cause => { if (live && cause.name !== 'AbortError') setError(cause.message); });
    }
    return () => { live = false; controller.abort(); measurementRequest.current?.abort(); };
  }, [documentId, page, identity, refresh]);

  const parsedReference = parseMeasurementPoints(manualReference);
  const parsedGeometry = parseMeasurementPoints(manualGeometry);
  const selectedReference = manualReference.trim() ? parsedReference.points : reference;
  const selectedGeometry = manualGeometry.trim() ? parsedGeometry.points
    : (captureMode === (kind === 'area' ? 'polygon' : 'segment') ? points : []);
  const draft = measurementDraft({ documentId, page, context, reference: selectedReference,
    geometry: selectedGeometry, value, unit, kind });
  const locked = disabled || busy;
  const referenceReady = validMeasurementPoints(selectedReference, 2, true);
  const editingError = parsedReference.error || parsedGeometry.error;

  function capture(mode) {
    setError(''); setStatus(''); setManualGeometry('');
    if (mode === 'calibration') { setManualReference(''); setReference([]); }
    onClearPoints?.();
    onCaptureModeChange?.(mode);
  }

  function acceptReference() {
    if (!validMeasurementPoints(points, 2, true)) return;
    setReference(points.map(point => [...point]));
    setManualReference(''); setError(''); setStatus('Reference line marked. Enter its real length, then mark what to measure.');
    onClearPoints?.(); onCaptureModeChange?.(null);
  }

  function editCoordinates(setter, text) {
    setError(''); setStatus(''); setter(text);
    onClearPoints?.(); onCaptureModeChange?.(null);
  }

  async function submit(event) {
    event.preventDefault();
    if (draft.error || editingError || locked) { setError(editingError || draft.error); return; }
    const controller = new AbortController();
    measurementRequest.current?.abort(); measurementRequest.current = controller;
    const sequence = ++requestSequence.current;
    const requestIdentity = identity;
    setBusy(true); setError(''); setStatus('Calculating from your reference…');
    try {
      const response = await fetch(`/api/documents/${encodeURIComponent(documentId)}/measurement`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(draft.payload), signal: controller.signal,
      });
      const answer = await responseJson(response);
      if (controller.signal.aborted || sequence !== requestSequence.current || currentIdentity.current !== requestIdentity) return;
      onAnswer?.(answer); onClearPoints?.(); onCaptureModeChange?.(null);
      setStatus('Measurement saved. Inspect the answer and its selected geometry.');
    } catch (cause) {
      if (cause.name !== 'AbortError' && sequence === requestSequence.current && currentIdentity.current === requestIdentity) {
        setError(cause.message); setStatus('');
      }
    } finally {
      if (sequence === requestSequence.current && currentIdentity.current === requestIdentity) setBusy(false);
    }
  }

  return <details className="measurement-panel" onPointerDown={event => event.stopPropagation()}
    onClick={event => event.stopPropagation()} onToggle={event => {
      if (!event.currentTarget.open) onCaptureModeChange?.(null);
    }}>
    <summary>Measure with a known length</summary>
    <form onSubmit={submit} aria-label="Measure using a known reference length">
      <p>Mark a known length, then a line or outline on this page. No image scale is assumed.</p>
      <fieldset disabled={locked}>
        <legend>1. Set the reference</legend>
        <div className="measurement-value-row">
          <label>Known length<input type="number" min="0" step="any" value={value} onChange={event => { setValue(event.target.value); setError(''); }} inputMode="decimal" placeholder="For example, 5" /></label>
          <label>Unit<select value={unit} onChange={event => { setUnit(event.target.value); setError(''); }}>
            <option value="m">m</option><option value="cm">cm</option><option value="mm">mm</option><option value="ft">ft</option><option value="in">in</option>
          </select></label>
        </div>
        <div className="measurement-actions">
          <button type="button" className="button" onClick={() => capture('calibration')} disabled={!context} aria-pressed={captureMode === 'calibration'}>{referenceReady ? 'Redraw reference' : 'Mark reference line'}</button>
          {captureMode === 'calibration' && <button type="button" className="button" onClick={acceptReference} disabled={!validMeasurementPoints(points, 2, true)}>Use reference</button>}
        </div>
        <p className="measurement-hint">{captureMode === 'calibration' ? `${Math.min(points.length, 2)}/2 endpoints marked. Click both ends of the known length.` : referenceReady ? 'Reference line is ready.' : 'Use a printed dimension or a length you have verified.'}</p>
      </fieldset>
      <fieldset disabled={locked}>
        <legend>2. Mark the measurement</legend>
        <label>Measure<select value={kind} onChange={event => { setKind(event.target.value); setManualGeometry(''); onClearPoints?.(); onCaptureModeChange?.(null); setError(''); }}>
          <option value="area">Area inside an outline</option><option value="length">Length between two points</option>
        </select></label>
        <div className="measurement-actions">
          <button type="button" className="button" onClick={() => capture(kind === 'area' ? 'polygon' : 'segment')} disabled={!context || !referenceReady} aria-pressed={captureMode === (kind === 'area' ? 'polygon' : 'segment')}>{kind === 'area' ? 'Mark outline' : 'Mark measured line'}</button>
          <button type="button" className="text-button" onClick={() => { onClearPoints?.(); setManualGeometry(''); setError(''); }} disabled={!points.length && !manualGeometry}>Clear marks</button>
        </div>
        <p className="measurement-hint">{kind === 'area' ? `${selectedGeometry.length} vertices. Click around the boundary, then calculate.` : `${selectedGeometry.length}/2 endpoints for the measured line.`}</p>
      </fieldset>
      <details className="measurement-coordinate-entry">
        <summary>Enter coordinates instead</summary>
        <p>Use normalized x, y pairs from 0 to 1, one pair per line.</p>
        <label>Reference endpoints<textarea rows={2} maxLength={1000} disabled={locked} value={manualReference} onChange={event => editCoordinates(setManualReference, event.target.value)} placeholder={'0.1, 0.5\n0.9, 0.5'} spellCheck="false" /></label>
        <label>{kind === 'area' ? 'Outline vertices' : 'Measured line endpoints'}<textarea rows={3} maxLength={16000} disabled={locked} value={manualGeometry} onChange={event => editCoordinates(setManualGeometry, event.target.value)} placeholder={'0.1, 0.1\n0.9, 0.1\n0.9, 0.8\n0.1, 0.8'} spellCheck="false" /></label>
      </details>
      {(error || editingError) && <p className="measurement-error" role="alert">{error || editingError}</p>}
      <button type="submit" className="button primary" disabled={locked || !!draft.error || !!editingError}>{busy ? 'Calculating…' : `Calculate ${kind}`}</button>
      <button type="button" className="text-button" disabled={busy} onClick={() => { onClearPoints?.(); onCaptureModeChange?.(null); setRefresh(current => current + 1); }}>Reset measurement</button>
      {status && <p className="measurement-hint" role="status">{status}</p>}
      <p className="measurement-hint">Your outline defines the result. Review its boundary and reference length before using it.</p>
    </form>
  </details>;
}
