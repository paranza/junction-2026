import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { ArrowDownToLine, ArrowLeft, ArrowUp, Box, Check, ChevronDown, ChevronLeft, ChevronRight, CircleHelp, Crosshair, Eye, EyeOff, FileImage, FileText, FolderOpen, Layers3, LoaderCircle, Maximize, Menu, MessageSquareText, Minus, MousePointer2, Plus, Search, ShieldCheck, SquareDashedMousePointer, Upload, X } from 'lucide-react';
import './styles.css';
import MeasurementPanel from './MeasurementPanel.jsx';
import ChatThread, { useConversation } from './ChatThread.jsx';
import EvidenceCloseup from './EvidenceCloseup.jsx';
import InferenceCost, { MessageInferenceCost } from './InferenceCost.jsx';
import useSessionUsage from './useSessionUsage.js';
import { messageCost, requestFailure } from './inferenceUsage.js';
import { Button as BoardButton } from './boardui/primitives.jsx';
import { evidenceBox, evidenceKind, savedAdditions, originalEvidence, reviewEvidence, reviewCount, reviewFingerprint, costText, aggregateUsage, countedCategory, allowedCountCategories, reviewCategories, usageLabel, evidenceVerificationText, canResolveComparison, formatQuantityValue } from './reviewState.js';

const request = async (url, options = {}) => {
  const response = await fetch(url, options);
  const contentType = response.headers.get('content-type') || '';
  const body = contentType.includes('application/json') ? await response.json() : await response.text();
  if (!response.ok) throw requestFailure(body, response.status);
  return body;
};
const jsonRequest = (url, body, options = {}) => request(url, { ...options, method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
const arrayOf = value => Array.isArray(value) ? value : [];
const basename = path => String(path || '').split(/[\\/]/).pop();
const documentName = doc => doc?.name || basename(doc?.path) || 'Untitled drawing';
const formatOf = doc => String(doc?.format || documentName(doc).split('.').pop() || '').replace(/^\./, '').toUpperCase();
const shortText = value => value == null ? '' : typeof value === 'object' ? JSON.stringify(value) : String(value);
const readable = value => shortText(value).replaceAll('_', ' ');
const quantityUnit = answer => {
  if (answer.unit !== 'count') return answer.unit;
  const categories = allowedCountCategories(answer);
  if (categories.length !== 1) return 'items';
  const category = categories[0];
  const label = { wc_room: 'WC room', sanitary_fixture: 'fixture' }[category] || readable(category);
  return answer.value === 1 ? label : `${label}s`;
};
const collectionLabel = source => ({ swiss_dwellings: 'Swiss Dwellings', cubicasa5k: 'CubiCasa5K', opening_design: 'Opening Design', habs: 'HABS historic drawings', finna: 'Finna archives', europeana: 'Europeana', wikimedia: 'Wikimedia', ifc_models: 'IFC models', ifc_bench: 'IFC benchmark', uploads: 'Uploaded drawings' }[source] || readable(source));
const documentListUrl = (search, source, offset = 0) => {
  const params = new URLSearchParams({ search, limit: '60', offset: String(offset) });
  if (source) params.set('source', source);
  return `/api/documents?${params}`;
};
const dateText = value => { const date = new Date(typeof value === 'number' && value < 1e12 ? value * 1000 : value); return Number.isNaN(date.getTime()) ? 'Time unavailable' : date.toLocaleString(); };
const scopeText = scope => typeof scope === 'object' ? scope?.label || scope?.description || [scope?.type, scope?.page && `page ${scope.page}`].filter(Boolean).join(' · ') : readable(scope);
const statusLabel = { computed: 'Calculated', supported: 'Source calculation', extracted: 'Source extracted', visual: 'Visual candidates', needs_review: 'Review needed', insufficient_evidence: 'Evidence insufficient', human_reviewed: 'Review saved' };
const getStatus = answer => answer?.status || 'needs_review';
const allEvidence = answer => arrayOf(answer?.evidence);
const evidenceKey = (e, i) => String(e.id ?? `evidence-${i}`);
const evidenceBBox = evidenceBox;
const normalizeDetails = payload => payload?.document ? { ...payload.document, pages: payload.pages || payload.document.pages, objects: payload.objects || payload.document.objects, warnings: payload.warnings || payload.document.warnings } : payload;
const calculationText = (calculation, answer) => {
  if (typeof calculation !== 'object') return shortText(calculation);
  if (calculation.formula || calculation.expression) return calculation.formula || calculation.expression;
  if (String(calculation.operation).includes('count')) {
    const nativeClass = arrayOf(calculation.classes).find(item => String(item).startsWith('Ifc'));
    const kind = nativeClass ? nativeClass.replace(/^Ifc/, '').replace(/([a-z])([A-Z])/g, '$1 $2').toLowerCase() : 'model';
    return `${calculation.count ?? answer.value} unique ${kind} elements`;
  }
  return Object.entries(calculation).filter(([key]) => key !== 'operation').map(([key, value]) => `${readable(key)}: ${shortText(value)}`).join(' · ');
};
const savedExclusions = answer => {
  const explicit = arrayOf(answer?.excluded_evidence_ids || answer?.review?.excluded_evidence_ids || answer?.human_review?.excluded_evidence_ids).map(String);
  const flagged = allEvidence(answer).flatMap((item, index) => item.excluded === true || item.included === false || item.status === 'excluded' ? [evidenceKey(item, index)] : []);
  return [...new Set([...explicit, ...flagged])];
};
const historyItem = (answer, fallback = {}) => {
  const savedTime = answer.created_at || answer.updated_at;
  const parsedTime = typeof savedTime === 'number' ? savedTime < 1e12 ? savedTime * 1000 : savedTime : Date.parse(savedTime);
  return {
    id: answer.id || fallback.id,
    question: answer.question || fallback.question || 'Drawing question',
    documentId: answer.document_id || answer.document?.id || fallback.documentId,
    documentName: answer.document?.name || fallback.documentName || basename(answer.provenance?.source_path) || 'Drawing',
    answer,
    timestamp: Number.isFinite(parsedTime) ? parsedTime : fallback.timestamp || Date.now(),
  };
};
const mergeHistory = (current, incoming) => {
  const merged = new Map();
  [...current, ...incoming].forEach(item => {
    if (!item?.documentId) return;
    merged.set(item.id || `${item.documentId}:${item.timestamp}:${item.question}`, item);
  });
  return [...merged.values()].sort((a, b) => b.timestamp - a.timestamp).slice(0, 12);
};

function IconButton({ label, children, className = '', ...props }) {
  return <BoardButton variant="ghost" size="small" className={`icon-button ${className}`} aria-label={label} title={label} {...props}>{children}</BoardButton>;
}

function DocumentIcon({ doc, size = 18 }) {
  return formatOf(doc) === 'IFC' ? <Box size={size} /> : ['PNG', 'JPG', 'JPEG', 'SVG', 'WEBP', 'TIFF', 'TIF', 'BMP', 'GIF'].includes(formatOf(doc)) ? <FileImage size={size} /> : <FileText size={size} />;
}

function DrawingCanvas({ document, page, evidence, selectedEvidence, onSelectEvidence, region, onRegion, focusToken, focusTarget, manualMode, onManualRegion, onCancelManual, onMeasuredAnswer, overviewToken, imageVersion = 0 }) {
  const viewportRef = useRef(null);
  const loadedImageRef = useRef(null);
  const dragRef = useRef(null);
  const transformRef = useRef({ x: 0, y: 0, scale: 1 });
  const [size, setSize] = useState({ width: 1000, height: 700 });
  const [viewSize, setViewSize] = useState({ width: 800, height: 600 });
  const [transform, setTransform] = useState(transformRef.current);
  const [imageState, setImageState] = useState('loading');
  const [showEvidence, setShowEvidence] = useState(true);
  const [tool, setTool] = useState('pan');
  const [draftRegion, setDraftRegion] = useState(null);
  const [captureMode, setCaptureMode] = useState(null);
  const [measurementPoints, setMeasurementPoints] = useState([]);
  const clearMeasurementPoints = useCallback(() => setMeasurementPoints([]), []);
  const applyTransform = useCallback(next => { transformRef.current = next; setTransform(next); }, []);
  const imageUrl = document?.id ? `/api/documents/${encodeURIComponent(document.id)}/pages/${page}/image?v=${imageVersion}` : null;
  const fit = useCallback(() => {
    const scale = Math.min((viewSize.width - 64) / size.width, (viewSize.height - 64) / size.height);
    const nextScale = Math.max(0.015, scale);
    applyTransform({ x: (viewSize.width - size.width * nextScale) / 2, y: (viewSize.height - size.height * nextScale) / 2, scale: nextScale });
  }, [viewSize, size, applyTransform]);
  useEffect(() => {
    const element = viewportRef.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => setViewSize({ width: entry.contentRect.width, height: entry.contentRect.height }));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  useEffect(() => { setImageState('loading'); setTool('pan'); }, [imageUrl]);
  useEffect(() => { setTool(captureMode ? 'measure' : manualMode ? 'manual' : 'pan'); }, [manualMode, captureMode]);
  useEffect(() => { setCaptureMode(null); setMeasurementPoints([]); }, [document?.id, page, imageVersion]);
  useEffect(() => { fit(); }, [fit, imageUrl, overviewToken]);
  const zoomAt = useCallback((factor, cx = viewSize.width / 2, cy = viewSize.height / 2) => {
    const current = transformRef.current;
    const scale = Math.min(15, Math.max(0.01, current.scale * factor));
    const ratio = scale / current.scale;
    applyTransform({ x: cx - (cx - current.x) * ratio, y: cy - (cy - current.y) * ratio, scale });
  }, [viewSize, applyTransform]);
  useEffect(() => {
    const element = viewportRef.current;
    if (!element) return;
    const wheel = event => {
      event.preventDefault();
      const rect = element.getBoundingClientRect();
      zoomAt(Math.exp(-event.deltaY * 0.0018), event.clientX - rect.left, event.clientY - rect.top);
    };
    element.addEventListener('wheel', wheel, { passive: false });
    return () => element.removeEventListener('wheel', wheel);
  }, [zoomAt]);
  const pointInDrawing = event => {
    const rect = viewportRef.current.getBoundingClientRect();
    const t = transformRef.current;
    return [Math.max(0, Math.min(1, (event.clientX - rect.left - t.x) / (size.width * t.scale))), Math.max(0, Math.min(1, (event.clientY - rect.top - t.y) / (size.height * t.scale)))];
  };
  const pointerDown = event => {
    if (event.button !== 0 || event.target.closest('button')) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = tool === 'region' || tool === 'manual' || tool === 'measure' ? { type: tool, start: pointInDrawing(event) } : { type: 'pan', clientX: event.clientX, clientY: event.clientY, ...transformRef.current };
    if (tool === 'region' || tool === 'manual') { const [x, y] = dragRef.current.start; setDraftRegion([x, y, x, y]); }
  };
  const pointerMove = event => {
    const drag = dragRef.current;
    if (!drag || drag.type === 'measure') return;
    if (drag.type === 'pan') applyTransform({ x: drag.x + event.clientX - drag.clientX, y: drag.y + event.clientY - drag.clientY, scale: drag.scale });
    else {
      const [x, y] = pointInDrawing(event);
      setDraftRegion([Math.min(drag.start[0], x), Math.min(drag.start[1], y), Math.max(drag.start[0], x), Math.max(drag.start[1], y)]);
    }
  };
  const pointerUp = event => {
    const drag = dragRef.current;
    if (drag?.type === 'measure') {
      const point = event ? pointInDrawing(event) : drag.start;
      setMeasurementPoints(previous => captureMode === 'polygon' ? [...previous, point].slice(0, 512) : previous.length >= 2 ? [point] : [...previous, point]);
    } else if (drag?.type === 'manual') {
      const end = event ? pointInDrawing(event) : drag.start;
      let box = draftRegion;
      if (!box || box[2] - box[0] < 0.003 || box[3] - box[1] < 0.003) {
        const x = end[0], y = end[1], half = 0.008;
        box = [Math.max(0, x - half), Math.max(0, y - half), Math.min(1, x + half), Math.min(1, y + half)];
      }
      onManualRegion(box);
    } else if (drag?.type === 'region' && draftRegion && draftRegion[2] - draftRegion[0] > 0.005 && draftRegion[3] - draftRegion[1] > 0.005) onRegion(draftRegion);
    setDraftRegion(null); dragRef.current = null;
  };
  const focusedBoxKey = JSON.stringify(evidenceBBox(evidence.find(item => item._key === selectedEvidence)));
  const focusEvidence = useCallback(() => {
    const box = JSON.parse(focusedBoxKey);
    if (!box) return;
    const width = Math.max(0.025, box[2] - box[0]) * size.width;
    const height = Math.max(0.025, box[3] - box[1]) * size.height;
    const scale = Math.min(8, Math.min(viewSize.width * 0.65 / width, viewSize.height * 0.65 / height));
    applyTransform({ scale, x: viewSize.width / 2 - (box[0] + box[2]) / 2 * size.width * scale, y: viewSize.height / 2 - (box[1] + box[3]) / 2 * size.height * scale });
  }, [focusedBoxKey, size.width, size.height, viewSize.width, viewSize.height, applyTransform]);
  const lastFocusToken = useRef(0);
  useEffect(() => {
    if (!focusToken) { lastFocusToken.current = 0; return; }
    if (focusToken === lastFocusToken.current || imageState !== 'ready' || loadedImageRef.current !== imageUrl
        || String(focusTarget?.documentId) !== String(document?.id) || Number(focusTarget?.page || 1) !== page
        || !viewportRef.current?.clientWidth || !viewportRef.current?.clientHeight) return;
    lastFocusToken.current = focusToken; setShowEvidence(true); focusEvidence();
  }, [focusToken, imageState, imageUrl, focusEvidence, focusTarget?.documentId, focusTarget?.page, document?.id, page]);
  const activeRegion = draftRegion || region;
  const spatialEvidenceCount = evidence.filter(item => evidenceBBox(item) || item.polygon?.length).length;
  return <div className="drawing-workspace">
    <div className="canvas-toolbar">
      <div className="segmented-tools">
        <IconButton label="Pan drawing" className={tool === 'pan' ? 'is-active' : ''} aria-pressed={tool === 'pan'} onClick={() => setTool('pan')}><MousePointer2 size={17} /></IconButton>
        <IconButton label="Select an area to ask about" className={tool === 'region' ? 'is-active' : ''} aria-pressed={tool === 'region'} onClick={() => setTool('region')} disabled={imageState !== 'ready'}><SquareDashedMousePointer size={18} /></IconButton>
      </div>
      <div className="canvas-toolbar-center"><span className="canvas-type">{formatOf(document)}</span><span>{document?.source ? readable(document.source) : 'Drawing'}</span></div>
      <div className="toolbar-actions">
        <IconButton label={showEvidence ? 'Hide evidence' : 'Show evidence'} aria-pressed={showEvidence} onClick={() => setShowEvidence(!showEvidence)}>{showEvidence ? <Eye size={18} /> : <EyeOff size={18} />}</IconButton>
        <IconButton label="Focus selected evidence" onClick={focusEvidence} disabled={focusedBoxKey === 'null'}><Crosshair size={18} /></IconButton>
      </div>
    </div>
    <div ref={viewportRef} className={`canvas-viewport tool-${tool}`} tabIndex={0} role="region" aria-label={manualMode ? 'Mark a missing object. Drag a box or click a point on the drawing.' : 'Drawing viewer. Drag to pan, scroll to zoom. Use plus, minus, or zero to fit.'} onPointerDown={pointerDown} onPointerMove={pointerMove} onPointerUp={pointerUp} onPointerCancel={() => { setDraftRegion(null); dragRef.current = null; }} onKeyDown={event => { if (event.key === '+' || event.key === '=') { event.preventDefault(); zoomAt(1.25); } if (event.key === '-') { event.preventDefault(); zoomAt(0.8); } if (event.key === '0') { event.preventDefault(); fit(); } }}>
      {imageUrl && <div className={`drawing-stage ${imageState === 'ready' ? 'is-ready' : ''}`} style={{ width: size.width, height: size.height, transform: `translate(${transform.x}px, ${transform.y}px) scale(${transform.scale})` }}>
        <img key={imageUrl} src={imageUrl} alt={`${documentName(document)}, page ${page}`} draggable={false} onLoad={event => { loadedImageRef.current = imageUrl; setSize({ width: event.currentTarget.naturalWidth, height: event.currentTarget.naturalHeight }); setImageState('ready'); }} onError={() => setImageState('error')} />
        {showEvidence && <svg className="evidence-shapes" viewBox="0 0 1000 1000" preserveAspectRatio="none" aria-hidden="true">{evidence.map(item => {
          const box = evidenceBBox(item); const isSelected = item._key === selectedEvidence;
          return item.polygon?.length ? <polygon key={item._key} points={item.polygon.map(([x, y]) => `${x * 1000},${y * 1000}`).join(' ')} className={`${isSelected ? 'selected-shape' : ''} ${item._excluded ? 'excluded-shape' : ''} evidence-kind-${evidenceKind(item)}`} /> : box ? <rect key={item._key} x={box[0] * 1000} y={box[1] * 1000} width={(box[2] - box[0]) * 1000} height={(box[3] - box[1]) * 1000} className={`${isSelected ? 'selected-shape' : ''} ${item._excluded ? 'excluded-shape' : ''} evidence-kind-${evidenceKind(item)}`} /> : null;
        })}{activeRegion && <rect className="region-shape" x={activeRegion[0] * 1000} y={activeRegion[1] * 1000} width={(activeRegion[2] - activeRegion[0]) * 1000} height={(activeRegion[3] - activeRegion[1]) * 1000} />}</svg>}
        {captureMode && measurementPoints.length > 0 && <svg className="evidence-shapes measurement-shapes" viewBox="0 0 1000 1000" preserveAspectRatio="none" aria-hidden="true"><polyline points={measurementPoints.map(([x, y]) => `${x * 1000},${y * 1000}`).join(' ')} fill={captureMode === 'polygon' ? 'rgba(34,125,75,.12)' : 'none'} stroke="#247d4b" strokeWidth="3" vectorEffect="non-scaling-stroke" />{measurementPoints.map(([x, y], index) => <circle key={index} cx={x * 1000} cy={y * 1000} r={4 / transform.scale} fill="#247d4b" />)}</svg>}
        {showEvidence && evidence.map(item => {
          const box = evidenceBBox(item);
          if (!box) return null;
          return <button key={item._key} type="button" className={`evidence-marker ${item._key === selectedEvidence ? 'is-selected' : ''} ${item._excluded ? 'is-excluded' : ''} evidence-kind-${evidenceKind(item)}`} style={{ left: `${box[0] * 100}%`, top: `${box[1] * 100}%`, transform: `translate(-50%, -50%) scale(${1 / transform.scale})` }} aria-label={`Inspect source ${item._number}: ${item.label || 'Evidence'}`} aria-pressed={item._key === selectedEvidence} onClick={() => onSelectEvidence(item)}>{item._number}</button>;
        })}
      </div>}
      {imageState === 'loading' && <div className="canvas-message"><LoaderCircle className="spin" size={24} /><strong>Preparing drawing</strong><span>Opening the source at full resolution</span></div>}
      {imageState === 'error' && <div className="canvas-message canvas-fallback"><Box size={30} /><strong>{formatOf(document) === 'IFC' ? 'Building model' : 'Preview unavailable'}</strong><span>{formatOf(document) === 'IFC' ? 'Ask about the model’s objects, spaces, and quantities.' : 'You can still inspect the source and ask a question.'}</span>{arrayOf(document?.objects).length > 0 && <div className="native-objects"><strong>Model objects</strong>{document.objects.slice(0, 8).map((item, index) => <div key={item.id || item.guid || index}><span>{item.name || item.label || item.type || 'Element'}</span><small>{item.type || item.ifc_type || ''}</small></div>)}</div>}<a className="button secondary" href={`/api/documents/${encodeURIComponent(document.id)}/original`} target="_blank" rel="noreferrer"><ArrowDownToLine size={15} /> Open original</a></div>}
      {captureMode && <div className="manual-notice">Click {captureMode === 'calibration' ? 'two reference endpoints' : captureMode === 'polygon' ? 'each boundary corner' : 'two segment endpoints'}. <button type="button" onClick={() => setCaptureMode(null)}>Stop marking</button></div>}
      {imageState === 'ready' && <MeasurementPanel documentId={document?.id} page={page} captureMode={captureMode} points={measurementPoints} onCaptureModeChange={setCaptureMode} onClearPoints={clearMeasurementPoints} onAnswer={onMeasuredAnswer} disabled={manualMode} />}
      {manualMode && <div className="manual-notice"><Plus size={14} /> Drag a box or click the missed object.<button type="button" onClick={onCancelManual}>Cancel marking</button></div>}
      {region && <div className="region-notice"><SquareDashedMousePointer size={14} /> Selected area <button type="button" onClick={() => onRegion(null)} aria-label="Clear selected area"><X size={14} /></button></div>}
    </div>
    <footer className="canvas-footer"><span><span className="source-dot" /> Original source{showEvidence && spatialEvidenceCount > 0 ? ` + ${spatialEvidenceCount} evidence regions` : ''}</span><div className="zoom-controls"><IconButton label="Zoom out" onClick={() => zoomAt(0.8)}><Minus size={15} /></IconButton><span>{Math.round(transform.scale * 100)}%</span><IconButton label="Zoom in" onClick={() => zoomAt(1.25)}><Plus size={15} /></IconButton><span className="control-divider" /><IconButton label="Fit drawing" onClick={fit}><Maximize size={15} /></IconButton></div></footer>
  </div>;
}

function EvidenceProperties({ properties }) {
  if (!properties || typeof properties !== 'object') return null;
  const hiddenProperties = ['projection_mean_error', 'extraction_version', 'coordinate_system'];
  const entries = Object.entries(properties).filter(([name, value]) => value != null && typeof value !== 'object' && !hiddenProperties.includes(name)).slice(0, 10);
  if (!entries.length) return null;
  return <dl className="property-list">{entries.map(([name, value]) => <React.Fragment key={name}><dt>{name === 'native_source_path' ? 'Native source' : readable(name)}</dt><dd>{name.endsWith('_path') ? basename(value) : typeof value === 'boolean' ? value ? 'Yes' : 'No' : shortText(value)}</dd></React.Fragment>)}</dl>;
}

function UsageDetails({ answer }) {
  const usage = answer?.usage;
  const initial = aggregateUsage(answer?.ingestion_usage || usage?.ingestion_usage);
  const callsKnown = Number.isFinite(usage?.model_calls);
  if (!usage) return null;
  return <details className="usage-details"><summary>{usageLabel(answer)} · {callsKnown ? `${usage.model_calls} model ${usage.model_calls === 1 ? 'call' : 'calls'}` : 'Call count unavailable'}</summary>
    <dl><dt>This question</dt><dd>{costText(usage)}</dd><dt>Input / output tokens</dt><dd>{Number(usage.input_tokens || 0).toLocaleString()} / {Number(usage.output_tokens || 0).toLocaleString()}</dd>{Number(usage.cached_input_tokens || 0) > 0 && <><dt>Cached input tokens</dt><dd>{Number(usage.cached_input_tokens).toLocaleString()}</dd></>}{answer.model && <><dt>Model</dt><dd>{answer.model}</dd></>}{initial && <><dt>Initial visual extraction</dt><dd>{Number(initial.model_calls || 0)} calls · {costText(initial)}</dd></>}</dl>
    <p>{usage.usage_incomplete ? 'The provider did not report all token usage. Any known cost is a subtotal.' : usage.cost_estimate_usd == null && usage.cost_basis !== 'native' ? 'A price is unavailable for some model usage. Any known cost is a subtotal.' : usage.model_calls === 0 ? 'No model inference was needed. Hosting and storage costs are separate.' : 'Estimate uses published or explicitly configured token rates before credits. It is not a provider invoice.'}</p>
  </details>;
}

function ReconciliationDetails({ answer, onSelect, onResolve, resolving, disabled }) {
  const result = answer?.reconciliation;
  const working = answer?.working_quantity;
  const [choice, setChoice] = useState(working?.selected_source || 'native');
  const [reason, setReason] = useState(working?.note || '');
  useEffect(() => { setChoice(working?.selected_source || 'native'); setReason(working?.note || ''); }, [answer?.id, working?.reviewed_at]);
  if (!result) return null;
  const nativeLabel = result.native_label || 'Native source';
  const comparisonLabel = result.visual_label || 'Visual candidates';
  return <section className={`reconciliation reconciliation-${result.status}`} aria-label="Quantity comparison">
    <div><strong>{({ agreement: 'Quantities agree', disagreement: 'Quantities disagree', scope_mismatch: 'Different scopes', unavailable: 'Comparison unavailable' })[result.status] || 'Quantity comparison'}</strong><span>{readable(result.status)}</span></div>
    {result.native_value != null && <dl><dt>{nativeLabel}</dt><dd>{formatQuantityValue(result.native_value, result.unit)} {result.unit || 'count'}</dd><dt>{comparisonLabel}</dt><dd>{result.visual_value == null ? 'Unavailable' : `${formatQuantityValue(result.visual_value, result.unit)} ${result.unit || 'count'}`}</dd></dl>}
    <p>{result.reason || 'Agreement between methods does not independently prove completeness.'}</p>
    {arrayOf(result.evidence).length > 0 && !answer.source_changed && <details><summary>Inspect comparison candidates ({result.evidence.length})</summary>{result.evidence.map((item, index) => <button type="button" key={item.id || index} onClick={() => onSelect({ ...item, _key: `comparison-${item.id || index}`, _number: index + 1 })}><Eye size={14} /><span>{item.label || `Candidate ${index + 1}`}</span>{evidenceBBox(item) ? <Crosshair size={13} /> : <span>Record</span>}</button>)}</details>}
    {working && <div className="working-quantity" role="status"><strong>{answer.source_changed ? 'Recorded working quantity' : 'Saved working quantity'}: {formatQuantityValue(working.value, working.unit)} {working.unit}</strong><span>{working.source_label || readable(working.selected_source)}</span><p>{working.note}</p><small>{dateText(working.reviewed_at)} · Your review judgment; the machine answer is preserved.</small></div>}
    {answer.resolution_superseded && <p className="resolution-superseded" role="status">The previous working quantity was superseded. {answer.resolution_superseded.reason || 'The reviewed count changed. Compare the current evidence before saving a new choice.'}</p>}
    {canResolveComparison(answer) && <form className="resolution-form" onSubmit={event => { event.preventDefault(); if (reason.trim().length >= 3) onResolve({ choice, note: reason.trim() }); }}>
      <fieldset disabled={resolving || disabled}><legend>Choose a working quantity</legend><label><input type="radio" name={`resolution-${answer.id}`} value="native" checked={choice === 'native'} onChange={() => setChoice('native')} /><span>{nativeLabel}<strong>{formatQuantityValue(result.native_value, result.unit)} {result.unit || 'count'}</strong></span></label><label><input type="radio" name={`resolution-${answer.id}`} value="comparison" checked={choice === 'comparison'} onChange={() => setChoice('comparison')} /><span>{comparisonLabel}<strong>{formatQuantityValue(result.visual_value, result.unit)} {result.unit || 'count'}</strong></span></label><label className="resolution-note">Reason for this choice<textarea rows={2} minLength={3} maxLength={2000} value={reason} onChange={event => setReason(event.target.value)} placeholder="Explain which evidence supports your working quantity." required /></label><button type="submit" className="button" disabled={reason.trim().length < 3 || resolving || disabled}>{resolving ? <LoaderCircle size={14} className="spin" /> : <ShieldCheck size={14} />}{resolving ? 'Saving choice…' : 'Save working quantity'}</button></fieldset>
      <p>{disabled ? 'Finish or cancel pending count review changes before choosing a working quantity. ' : ''}This records your review choice. It does not automatically verify the quantity or replace the machine answer.</p>
    </form>}
    {arrayOf(answer.resolution_history).length > 0 && <details className="resolution-history"><summary>Working quantity history ({answer.resolution_history.length})</summary>{answer.resolution_history.map((item, index) => <div key={`${item.reviewed_at}-${index}`}><strong>{formatQuantityValue(item.value, item.unit)} {item.unit} · {item.source_label || readable(item.selected_source)}</strong><p>{item.note}</p><small>{dateText(item.reviewed_at)}</small></div>)}</details>}
  </section>;
}

function App() {
  const [health, setHealth] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [collections, setCollections] = useState([]);
  const [collection, setCollection] = useState('');
  const [documentsLoading, setDocumentsLoading] = useState(true);
  const [documentsError, setDocumentsError] = useState('');
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState('');
  const [page, setPage] = useState(1);
  const [scope, setScope] = useState('document');
  const [crossCheck, setCrossCheck] = useState(false);
  const [verifyVisual, setVerifyVisual] = useState(false);
  const [region, setRegion] = useState(null);
  const [question, setQuestion] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [answer, setAnswer] = useState(null);
  const [answerDocumentId, setAnswerDocumentId] = useState(null);
  const [answerQuestion, setAnswerQuestion] = useState('');
  const [answerDocumentName, setAnswerDocumentName] = useState('');
  const [selectedEvidence, setSelectedEvidence] = useState(null);
  const [asking, setAsking] = useState(false);
  const [askError, setAskError] = useState('');
  const [askErrorUsage, setAskErrorUsage] = useState(undefined);
  const sessionUsage = useSessionUsage(request, asking);
  const [elapsed, setElapsed] = useState(0);
  const [history, setHistory] = useState([]);
  const [excluded, setExcluded] = useState([]);
  const [manualAdditions, setManualAdditions] = useState([]);
  const [reviewNote, setReviewNote] = useState('');
  const [reviewUndo, setReviewUndo] = useState([]);
  const [manualMode, setManualMode] = useState(false);
  const [pendingManual, setPendingManual] = useState(null);
  const [manualLabel, setManualLabel] = useState('');
  const [manualCategory, setManualCategory] = useState('other');
  const [manualNote, setManualNote] = useState('');
  const [manualError, setManualError] = useState('');
  const [focusToken, setFocusToken] = useState(0);
  const [comparisonEvidence, setComparisonEvidence] = useState(null);
  const [reviewing, setReviewing] = useState(false);
  const [resolving, setResolving] = useState(false);
  const [restoringHistory, setRestoringHistory] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState('');
  const [libraryOpen, setLibraryOpen] = useState(false);
  const [answerOpen, setAnswerOpen] = useState(true);
  const [pendingQuestion, setPendingQuestion] = useState(null);
  const initialConversationRestore = useRef(false);
  const conversationEndRef = useRef(null);
  const [refreshVersion, setRefreshVersion] = useState(0);
  const fileInputRef = useRef(null);
  const questionRef = useRef(null);
  const documentFilterRef = useRef('');
  const activeAskRef = useRef(null);
  const activeHistoryRef = useRef(null);
  const answerRef = useRef(answer);
  answerRef.current = answer;
  const askSequenceRef = useRef(0);
  const contextRef = useRef(null);
  const manualLabelRef = useRef(null);
  contextRef.current = JSON.stringify({ documentId: selectedId, page, scope, region });
  const selectedDocument = detail || documents.find(doc => String(doc.id) === String(selectedId));
  const evidence = useMemo(() => reviewEvidence(answer, manualAdditions).map((item, index) => ({ ...item, _key: evidenceKey(item, index), _number: index + 1 })), [answer, manualAdditions]);
  const canvasEvidence = answer?.source_changed ? [] : [...evidence, ...(comparisonEvidence ? [comparisonEvidence] : []), ...(pendingManual ? [{ id: 'manual-preview', _key: 'manual-preview', _number: '+', label: manualLabel || 'Missing object', document_id: pendingManual.document_id, page: pendingManual.page, bbox: pendingManual.bbox, manual: true }] : [])].filter(item => String(item.document_id ?? answerDocumentId) === String(selectedId) && Number(item.page || 1) === page && evidenceBBox(item)).map(item => ({ ...item, _excluded: excluded.includes(item._key) }));
  const selectedEvidenceItem = evidence.find(item => item._key === selectedEvidence);
  const focusEvidenceItem = selectedEvidenceItem || (comparisonEvidence?._key === selectedEvidence ? comparisonEvidence : null);
  const pageCount = Number(detail?.page_count || detail?.pages?.length || 1);
  const warnings = arrayOf(answer?.warnings);
  const resultStatus = getStatus(answer);
  const reviewedCount = reviewCount(answer, manualAdditions, excluded);
  const manualCategories = allowedCountCategories(answer);
  const knownManualCategory = manualCategories.length === 1 ? manualCategories[0] : null;
  const hasReviewChanges = !!answer && reviewFingerprint(excluded, manualAdditions, reviewNote) !== reviewFingerprint(savedExclusions(answer), savedAdditions(answer), answer.review?.note || '');
  const cancelAsk = useCallback((showNotice = false) => {
    const active = activeAskRef.current;
    if (!active) return;
    active.controller.abort(); activeAskRef.current = null; askSequenceRef.current += 1; setAsking(false);
    if (showNotice) { setAskError('Stopped waiting for this answer. The server may finish an already-started model request.'); setAskErrorUsage(undefined); }
  }, []);
  const cancelHistory = useCallback(() => { activeHistoryRef.current?.abort(); activeHistoryRef.current = null; setRestoringHistory(false); }, []);
  const cancelManual = useCallback(() => { setManualMode(false); setPendingManual(null); setManualError(''); }, []);
  const loadReviewDraft = useCallback(result => {
    setExcluded(savedExclusions(result)); setManualAdditions(savedAdditions(result)); setReviewNote(result.review?.note || ''); setReviewUndo([]); cancelManual(); setComparisonEvidence(null);
  }, [cancelManual]);
  useEffect(() => () => { activeAskRef.current?.controller.abort(); activeHistoryRef.current?.abort(); }, []);
  useEffect(() => {
    if (!libraryOpen) return;
    const panel = window.document.querySelector('.document-library');
    const previous = window.document.activeElement;
    panel?.querySelector('input[type="search"]')?.focus();
    const keydown = event => {
      if (event.key === 'Escape') { event.preventDefault(); event.stopImmediatePropagation(); setLibraryOpen(false); return; }
      if (event.key !== 'Tab') return;
      const controls = [...(panel?.querySelectorAll('button:not([disabled]), input:not([disabled]):not([tabindex="-1"]), select:not([disabled]), a[href]') || [])];
      if (!controls.length) return;
      const first = controls[0], last = controls[controls.length - 1];
      if (event.shiftKey && (window.document.activeElement === first || !panel.contains(window.document.activeElement))) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && (window.document.activeElement === last || !panel.contains(window.document.activeElement))) { event.preventDefault(); first.focus(); }
    };
    window.addEventListener('keydown', keydown);
    return () => { window.removeEventListener('keydown', keydown); if (previous?.isConnected) previous.focus(); };
  }, [libraryOpen]);
  useEffect(() => {
    if (!manualMode && !pendingManual) return;
    const escape = event => { if (event.key === 'Escape') { event.preventDefault(); cancelManual(); } };
    window.addEventListener('keydown', escape); return () => window.removeEventListener('keydown', escape);
  }, [manualMode, pendingManual, cancelManual]);

  useEffect(() => { request('/api/health').then(setHealth).catch(() => setHealth({ status: 'offline' })); }, [refreshVersion]);
  useEffect(() => {
    const controller = new AbortController();
    request('/api/answers?limit=12', { signal: controller.signal }).then(data => {
      const saved = arrayOf(data.answers || data).map(item => historyItem(item));
      setHistory(current => mergeHistory(saved, current));
    }).catch(() => {});
    return () => controller.abort();
  }, [refreshVersion]);
  useEffect(() => { const timer = setTimeout(() => setSearchTerm(search), 220); return () => clearTimeout(timer); }, [search]);
  useEffect(() => {
    const controller = new AbortController();
    documentFilterRef.current = `${collection}\u0000${searchTerm}`;
    setDocumentsLoading(true); setDocumentsError('');
    request(documentListUrl(searchTerm, collection), { signal: controller.signal }).then(data => {
      const docs = arrayOf(data.documents || data);
      setDocuments(docs); setTotal(data.total ?? docs.length);
      if (Array.isArray(data.sources)) setCollections(data.sources);
      setSelectedId(current => current || docs[0]?.id || null);
    }).catch(error => { if (error.name !== 'AbortError') setDocumentsError(error.message); }).finally(() => { if (!controller.signal.aborted) setDocumentsLoading(false); });
    return () => controller.abort();
  }, [searchTerm, collection, refreshVersion]);
  useEffect(() => {
    if (!selectedId) return;
    const controller = new AbortController();
    setDetailLoading(true); setDetailError(''); setDetail(null); setSuggestions([]);
    request(`/api/documents/${encodeURIComponent(selectedId)}`, { signal: controller.signal }).then(data => setDetail(normalizeDetails(data))).catch(error => { if (error.name !== 'AbortError') setDetailError(error.message); }).finally(() => { if (!controller.signal.aborted) setDetailLoading(false); });
    request(`/api/questions/${encodeURIComponent(selectedId)}`, { signal: controller.signal }).then(data => setSuggestions(arrayOf(data.questions || data.suggestions || data).map(item => typeof item === 'string' ? item : item.question).filter(Boolean))).catch(() => {});
    return () => controller.abort();
  }, [selectedId, refreshVersion]);
  useEffect(() => { if (!asking) return; setElapsed(0); const timer = setInterval(() => setElapsed(value => value + 1), 1000); return () => clearInterval(timer); }, [asking]);
  const selectDocument = useCallback((id, keepAnswer = false, requestedPage = 1) => {
    initialConversationRestore.current = true;
    cancelAsk(); cancelHistory(); cancelManual(); setSelectedId(id); setPage(Number(requestedPage) || 1); setRegion(null); setLibraryOpen(false);
    if (!keepAnswer) { setFocusToken(0); setAnswer(null); setSelectedEvidence(null); setAskError(''); setAskErrorUsage(undefined); setExcluded([]); setManualAdditions([]); setReviewNote(''); setReviewUndo([]); setScope('document'); setComparisonEvidence(null); }
  }, [cancelAsk, cancelHistory, cancelManual]);
  const selectEvidence = useCallback(item => {
    if (answerRef.current?.source_changed) return;
    setAnswerOpen(false);
    cancelAsk(); cancelHistory(); cancelManual();
    setSelectedEvidence(item._key); setFocusToken(value => value + 1);
    if (String(item._key).startsWith('comparison-')) setComparisonEvidence(item);
    const targetDocument = item.document_id || answerDocumentId;
    if (targetDocument && String(targetDocument) !== String(selectedId)) selectDocument(targetDocument, true, item.page);
    else if (evidenceBBox(item) && item.page && Number(item.page) !== page) { setPage(Number(item.page)); setRegion(null); }
  }, [answerDocumentId, selectedId, page, selectDocument, cancelAsk, cancelHistory, cancelManual]);
  const ask = async (event, crossCheck = false) => {
    event?.preventDefault();
    if (!question.trim() || !selectedId || asking) return;
    initialConversationRestore.current = true;
    cancelHistory(); cancelManual(); setAsking(true); setAskError(''); setAskErrorUsage(undefined); setAnswerOpen(true); sessionUsage.trackRequest();
    const questionText = question.trim(); const documentId = selectedId; const sourceName = documentName(selectedDocument);
    setPendingQuestion({ question: questionText, documentName: sourceName }); setQuestion('');
    const context = contextRef.current, sequence = ++askSequenceRef.current, controller = new AbortController();
    activeAskRef.current = { sequence, controller, context };
    try {
      const result = await jsonRequest('/api/ask', { session_id: sessionUsage.sessionId, document_id: documentId, question: questionText, page, scope: region ? 'page' : scope, ...(region ? { region } : {}), mode: 'auto', cross_check: crossCheck, verify_visual: verifyVisual }, { signal: controller.signal });
      if (controller.signal.aborted || activeAskRef.current?.sequence !== sequence || contextRef.current !== context) return;
      activeAskRef.current = null; setAsking(false);
      setFocusToken(0); setAnswer(result); setAnswerDocumentId(documentId); setAnswerQuestion(questionText); setAnswerDocumentName(sourceName); loadReviewDraft(result);
      const primaryEvidence = allEvidence(result).find(item => evidenceBBox(item)) || allEvidence(result)[0];
      setSelectedEvidence(primaryEvidence ? evidenceKey(primaryEvidence, allEvidence(result).indexOf(primaryEvidence)) : null);
      // Open the relevant source page, while retaining a whole-page view.
      if (primaryEvidence?.document_id && String(primaryEvidence.document_id) !== String(documentId)) selectDocument(primaryEvidence.document_id, true, primaryEvidence.page);
      else if (evidenceBBox(primaryEvidence) && primaryEvidence?.page && Number(primaryEvidence.page) !== page) setPage(Number(primaryEvidence.page));
      setHistory(items => mergeHistory(items, [historyItem(result, { question: questionText, documentId, documentName: sourceName, timestamp: Date.now() })]));
    } catch (error) { if (error.name !== 'AbortError' && activeAskRef.current?.sequence === sequence) { setAskError(error.message); setAskErrorUsage(error.usage ?? null); } }
    finally { sessionUsage.refresh(); if (activeAskRef.current?.sequence === sequence) { activeAskRef.current = null; setAsking(false); } }
  };
  const acceptMeasuredAnswer = useCallback(result => {
    if (String(result.document_id) !== String(selectedId)) return;
    cancelAsk(); cancelHistory(); cancelManual();
    setFocusToken(0); setAnswer(result); setAnswerDocumentId(result.document_id); setAnswerQuestion(result.question); setQuestion('');
    setAnswerDocumentName(documentName(result.document)); loadReviewDraft(result); setAskError(''); setAskErrorUsage(undefined); setAnswerOpen(true);
    const primary = arrayOf(result.evidence)[0];
    setSelectedEvidence(primary ? evidenceKey(primary, 0) : null);
    setHistory(items => mergeHistory(items, [historyItem(result, { timestamp: Date.now() })]));
  }, [selectedId, cancelAsk, cancelHistory, cancelManual, loadReviewDraft]);
  const askRegion = next => { cancelAsk(); cancelHistory(); cancelManual(); setRegion(next); };
  const changeScope = next => { cancelAsk(); cancelHistory(); cancelManual(); setScope(next); };
  const uploadFiles = async files => {
    if (!files?.length) return;
    const form = new FormData(); Array.from(files).forEach(file => form.append('files', file));
    setUploading(true); setUploadMessage('');
    try {
      const data = await request('/api/upload', { method: 'POST', body: form });
      const uploaded = arrayOf(data.documents || data);
      setUploadMessage(`${uploaded.length || files.length} ${uploaded.length === 1 ? 'file' : 'files'} added`);
      setSearch(''); setCollection(''); setRefreshVersion(value => value + 1);
      if (uploaded[0]?.id) selectDocument(uploaded[0].id);
    } catch (error) { setUploadMessage(error.message); } finally { setUploading(false); if (fileInputRef.current) fileInputRef.current.value = ''; }
  };
  const loadMore = async () => {
    const filterKey = `${collection}\u0000${searchTerm}`;
    setDocumentsLoading(true);
    try {
      const data = await request(documentListUrl(searchTerm, collection, documents.length));
      if (documentFilterRef.current === filterKey) setDocuments(items => [...items, ...arrayOf(data.documents)]);
    } catch (error) { if (documentFilterRef.current === filterKey) setDocumentsError(error.message); }
    finally { if (documentFilterRef.current === filterKey) setDocumentsLoading(false); }
  };
  const snapshotReview = () => setReviewUndo(items => [...items.slice(-29), { excluded: [...excluded], additions: manualAdditions.map(item => ({ ...item })), note: reviewNote }]);
  const toggleIncluded = (key, included) => { snapshotReview(); setExcluded(items => included ? items.filter(id => id !== key) : [...new Set([...items, key])]); };
  const undoReview = () => {
    const previous = reviewUndo.at(-1); if (!previous) return;
    setExcluded(previous.excluded); setManualAdditions(previous.additions); setReviewNote(previous.note); setReviewUndo(items => items.slice(0, -1)); cancelManual();
  };
  const restoreOriginal = () => { snapshotReview(); setExcluded([]); setManualAdditions([]); setReviewNote(''); cancelManual(); };
  const startManual = () => {
    if (!answer?.can_review || answer.source_changed) return;
    const category = manualCategories[0] || countedCategory(answer);
    setManualCategory(category || 'other');
    setManualLabel(category ? `Missing ${readable(category)}` : ''); setManualNote(''); setManualError('');
    setPendingManual({ document_id: selectedId, page, bbox: [0.45, 0.45, 0.55, 0.55] }); setManualMode(true);
    requestAnimationFrame(() => manualLabelRef.current?.focus());
  };
  const markManual = bbox => { setPendingManual({ document_id: selectedId, page, bbox }); setManualMode(false); setAnswerOpen(true); requestAnimationFrame(() => manualLabelRef.current?.focus()); };
  const addManual = event => {
    event.preventDefault();
    if (answerRef.current?.source_changed) { cancelManual(); return; }
    const box = pendingManual?.bbox;
    if (!manualLabel.trim()) { setManualError('Name the missing object.'); return; }
    if (!box || box.length !== 4 || !box.every(value => Number.isFinite(value) && value >= 0 && value <= 1) || box[0] >= box[2] || box[1] >= box[3]) { setManualError('Use page coordinates from 0 to 1, with left less than right and top less than bottom.'); return; }
    snapshotReview();
    const id = `manual-${window.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`}`;
    const item = { id, label: manualLabel.trim(), category: knownManualCategory || manualCategory, ...pendingManual, note: manualNote.trim(), manual: true };
    setManualAdditions(items => [...items, item]); setSelectedEvidence(id); setFocusToken(value => value + 1); cancelManual();
  };
  const review = async () => {
    if (!answer?.id || answer.source_changed) return;
    const answerId = answer.id;
    setReviewing(true); setAskError(''); setAskErrorUsage(undefined);
    try {
      const result = await jsonRequest(`/api/answers/${encodeURIComponent(answerId)}/review`, { excluded_evidence_ids: excluded, added_evidence: manualAdditions, note: reviewNote });
      if (answerRef.current?.id === answerId) { setAnswer(result); loadReviewDraft(result); }
      setHistory(items => mergeHistory(items, [historyItem(result, { question: answerQuestion, documentId: answerDocumentId, documentName: answerDocumentName, timestamp: items.find(item => item.id === answerId)?.timestamp || Date.now() })]));
    }
    catch (error) { setAskError(error.message); } finally { setReviewing(false); }
  };
  const downloadAnswer = () => {
    if (!answer) return;
    const blob = new Blob([JSON.stringify({ question: answerQuestion, document: { id: answerDocumentId, name: answerDocumentName }, ...answer, ...(hasReviewChanges ? { unsaved_review: { excluded_evidence_ids: excluded, added_evidence: manualAdditions, note: reviewNote, value: reviewedCount } } : {}) }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob); const link = window.document.createElement('a'); link.href = url; link.download = `trace-answer-${answer.id || Date.now()}.json`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  const resolveComparison = async payload => {
    if (!answer?.id || !canResolveComparison(answer) || resolving || reviewing || hasReviewChanges || pendingManual) return;
    const answerId = answer.id;
    setResolving(true); setAskError(''); setAskErrorUsage(undefined);
    try {
      const result = await jsonRequest(`/api/answers/${encodeURIComponent(answerId)}/resolution`, payload);
      if (answerRef.current?.id === answerId) setAnswer(result);
      setHistory(items => mergeHistory(items, [historyItem(result, { question: answerQuestion, documentId: answerDocumentId, documentName: answerDocumentName, timestamp: items.find(item => item.id === answerId)?.timestamp || Date.now() })]));
    } catch (error) { if (answerRef.current?.id === answerId) setAskError(error.message); }
    finally { setResolving(false); }
  };
  const restoreHistory = async item => {
    if (!item.id) return;
    cancelAsk(); cancelHistory(); cancelManual(); setAskError(''); setAskErrorUsage(undefined); setRestoringHistory(true);
    const controller = new AbortController(); activeHistoryRef.current = controller;
    try {
      const result = await request(`/api/answers/${encodeURIComponent(item.id)}`, { signal: controller.signal });
      if (controller.signal.aborted || activeHistoryRef.current !== controller) return;
      activeHistoryRef.current = null; setRestoringHistory(false);
      const primaryEvidence = result.source_changed ? null : allEvidence(result).find(source => !source.excluded && evidenceBBox(source)) || allEvidence(result)[0];
      const documentId = result.document_id || item.documentId;
      selectDocument(primaryEvidence?.document_id || documentId, true, primaryEvidence?.page || result.provenance?.page);
      setFocusToken(0); setQuestion(''); setPendingQuestion(null); setAnswerQuestion(result.question || item.question); setAnswerDocumentName(result.document?.name || item.documentName); setAnswer(result); setAnswerDocumentId(documentId); loadReviewDraft(result);
      setSelectedEvidence(primaryEvidence ? evidenceKey(primaryEvidence, allEvidence(result).indexOf(primaryEvidence)) : null); setAnswerOpen(true);
      setHistory(items => mergeHistory(items, [historyItem(result, item)]));

    } catch (error) { if (error.name !== 'AbortError' && activeHistoryRef.current === controller) setAskError(`Could not load the saved answer: ${error.message}`); }
    finally { if (activeHistoryRef.current === controller) { activeHistoryRef.current = null; setRestoringHistory(false); } }
  };
  const changePage = newPage => { cancelAsk(); cancelHistory(); cancelManual(); setPage(Math.max(1, Math.min(pageCount, newPage))); setRegion(null); };
  const sourceCredit = detail?.credit || detail?.attribution || detail?.license_credit;
  const conversation = useConversation({ sessionId: sessionUsage.sessionId, snapshot: sessionUsage.snapshot,
    answer, answerQuestion, documentName: answerDocumentName, request });
  useEffect(() => {
    if (initialConversationRestore.current || answer || asking) return;
    const latest = [...conversation.records].reverse().find(item => item.status === 'completed' && item.answerId);
    if (!latest || !conversation.answers[latest.answerId]) return;
    initialConversationRestore.current = true;
    const restored = conversation.answers[latest.answerId];
    restoreHistory({ id: restored.id, question: latest.question, documentId: restored.document_id, documentName: restored.document?.name || latest.documentName });
  }, [conversation.records, conversation.answers, answer, asking]);
  useEffect(() => {
    requestAnimationFrame(() => {
      if (asking) conversationEndRef.current?.scrollIntoView({ block: 'end', behavior: 'auto' });
      else if (answer) conversationEndRef.current?.parentElement?.querySelector('.chat-turn.is-active')?.scrollIntoView({ block: 'start', behavior: 'auto' });
    });
  }, [asking, answer?.id]);
  useEffect(() => {
    const input = questionRef.current;
    if (!input) return;
    input.style.height = 'auto'; input.style.height = `${Math.min(150, Math.max(48, input.scrollHeight))}px`;
  }, [question]);


  return <div className="app-shell" data-mobile-view={answerOpen ? 'conversation' : 'drawing'}>
    <header className="app-header"><div className="header-left"><BoardButton variant="ghost" size="small" className="library-toggle" aria-expanded={libraryOpen} onClick={() => { initialConversationRestore.current = true; setLibraryOpen(value => !value); }}><Menu size={18} /> Drawings</BoardButton><div className="brand"><span>trace<span className="brand-period">.</span></span></div></div><div className="header-right">{health?.status === 'offline' && <span className="connection-state is-offline">Connection unavailable</span>}<InferenceCost snapshot={sessionUsage.snapshot} unavailable={sessionUsage.unavailable} /></div></header>
    <div className="mobile-toolbar" aria-label="Workspace view"><button type="button" aria-pressed={answerOpen} onClick={() => { initialConversationRestore.current = true; setAnswerOpen(true); setLibraryOpen(false); }}><MessageSquareText size={17} /> Conversation</button><button type="button" aria-pressed={!answerOpen} onClick={() => { initialConversationRestore.current = true; setAnswerOpen(false); setLibraryOpen(false); }}><FileImage size={17} /> Drawing</button></div>
    {libraryOpen && <button className="panel-scrim" aria-label="Close drawing library" onClick={() => setLibraryOpen(false)} />}
    <div className="workspace-layout">
      <aside className={`document-library ${libraryOpen ? 'is-open' : ''}`} aria-label="Drawing library" inert={!libraryOpen ? true : undefined}>
        <div className="library-heading"><div><h1>Drawings <span>{total.toLocaleString()}</span></h1></div><IconButton label="Close drawing library" onClick={() => setLibraryOpen(false)}><X size={18} /></IconButton></div>
        <label className="search-field"><Search size={16} /><span className="sr-only">Search drawings</span><input type="search" value={search} onChange={event => setSearch(event.target.value)} placeholder="Find a drawing…" />{search && <button type="button" aria-label="Clear search" onClick={() => setSearch('')}><X size={13} /></button>}</label>
        <label className="collection-filter"><span>Collection</span><select aria-label="Drawing collection" value={collection} onChange={event => setCollection(event.target.value)}><option value="">All collections{collections.length ? ` (${collections.reduce((sum, source) => sum + Number(source.count || 0), 0).toLocaleString()})` : ''}</option>{collections.map(source => <option key={source.source} value={source.source}>{collectionLabel(source.source)} ({Number(source.count || 0).toLocaleString()})</option>)}</select></label>
        <div className="library-list-heading"><span>{searchTerm ? 'Search results' : collection ? collectionLabel(collection) : 'All documents'}</span><span>{documentsLoading ? <LoaderCircle size={12} className="spin" /> : `${documents.length} shown`}</span></div>
        <div className="document-list">
          {documentsError && <div className="inline-error" role="alert"><strong>Couldn’t load drawings</strong><span>{documentsError}</span><button type="button" onClick={() => setRefreshVersion(value => value + 1)}>Try again</button></div>}
          {documentsLoading && documents.length === 0 && Array.from({ length: 8 }, (_, index) => <div className="document-skeleton" key={index}><span /><div><span /><span /></div></div>)}
          {!documentsLoading && !documentsError && documents.length === 0 && <div className="library-empty"><FolderOpen size={24} /><strong>{searchTerm ? 'No matching drawings' : 'Your drawing library starts here'}</strong><span>{searchTerm ? 'Try a filename or source.' : 'Upload a PDF, image, drawing, or building model.'}</span></div>}
          {documents.map(doc => <button key={doc.id} type="button" className={`document-item ${String(doc.id) === String(selectedId) ? 'is-selected' : ''}`} onClick={() => selectDocument(doc.id)} title={documentName(doc)} aria-pressed={String(doc.id) === String(selectedId)}><span className={`document-icon format-${formatOf(doc).toLowerCase()}`}><DocumentIcon doc={doc} /></span><span className="document-item-text"><strong>{documentName(doc)}</strong><span>{formatOf(doc)}<span className="mini-dot" />{readable(doc.source || (doc.indexed ? 'Indexed' : 'Ready to open'))}</span></span>{doc.indexed && <span className="indexed-dot" title="Indexed" aria-label="Indexed" />}</button>)}
          {documents.length < total && <button type="button" className="load-more" onClick={loadMore} disabled={documentsLoading}>{documentsLoading ? 'Loading…' : 'Load more drawings'}<ChevronDown size={14} /></button>}
        </div>
        <div className="library-footer"><input ref={fileInputRef} type="file" tabIndex={-1} multiple accept=".pdf,.png,.jpg,.jpeg,.gif,.webp,.bmp,.tif,.tiff,.svg,.dxf,.dwg,.ifc" className="sr-only" onChange={event => uploadFiles(event.target.files)} /><BoardButton variant="secondary" className="upload-button" onClick={() => fileInputRef.current?.click()} disabled={uploading}>{uploading ? <LoaderCircle size={16} className="spin" /> : <Upload size={16} />}{uploading ? 'Adding drawings…' : 'Upload drawings'}</BoardButton>{uploadMessage && <p className="upload-feedback" role="status">{uploadMessage}</p>}<div className="library-footnote"><Layers3 size={13} /><span>PDF · CAD · BIM · images</span></div></div>
      </aside>
      <main className="main-drawing" aria-label="Selected drawing">
        {selectedDocument ? <><div className="drawing-heading"><div className="drawing-heading-main"><div className="breadcrumb">Project library <ChevronRight size={12} /> <span>{readable(selectedDocument.source || 'Uploaded drawings')}</span></div><h2 title={documentName(selectedDocument)}>{documentName(selectedDocument)}</h2></div><div className="drawing-heading-actions">{detailLoading && <LoaderCircle size={16} className="spin" />}{pageCount > 1 && <div className="page-controls"><IconButton label="Previous page" onClick={() => changePage(page - 1)} disabled={page <= 1}><ChevronLeft size={16} /></IconButton><label><span className="sr-only">Page</span><select aria-label="Page" value={page} onChange={event => changePage(Number(event.target.value))}>{Array.from({ length: pageCount }, (_, i) => <option key={i + 1} value={i + 1}>{i + 1}</option>)}</select><span>/ {pageCount}</span></label><IconButton label="Next page" onClick={() => changePage(page + 1)} disabled={page >= pageCount}><ChevronRight size={16} /></IconButton></div>}<a className="icon-button" href={`/api/documents/${encodeURIComponent(selectedId)}/original`} target="_blank" rel="noreferrer" title="Open original source" aria-label="Open original source"><ArrowDownToLine size={18} /></a></div></div>{detailError && <div className="drawing-warning" role="alert">{detailError}</div>}<DrawingCanvas document={selectedDocument} page={page} evidence={canvasEvidence} selectedEvidence={selectedEvidence} onSelectEvidence={selectEvidence} region={region} onRegion={askRegion} focusToken={focusToken} focusTarget={focusEvidenceItem ? { documentId: focusEvidenceItem.document_id || answerDocumentId, page: focusEvidenceItem.page || 1 } : null} manualMode={manualMode && !answer?.source_changed} onManualRegion={markManual} onCancelManual={cancelManual} onMeasuredAnswer={acceptMeasuredAnswer} imageVersion={refreshVersion} overviewToken={answer?.id} />{sourceCredit && <details className="source-credit"><summary>Source &amp; licence · {readable(selectedDocument.source || 'Original drawing')}</summary><p>{shortText(sourceCredit)}{detail.license ? ` · ${shortText(detail.license)}` : ''}</p></details>}</> : <div className="workspace-empty"><h2>Open a drawing</h2><p>Choose a project file or upload a plan.<br />Ask a quantity question and inspect its source.</p><button type="button" className="button primary" onClick={() => fileInputRef.current?.click()}><Upload size={16} /> Upload drawings</button></div>}
      </main>
      <aside className={`answer-panel ${answerOpen ? 'is-open' : ''}`} aria-label="Ask Trace and inspect answers">
        <div className="answer-panel-heading"><div><h1>Conversation</h1><p>Ask, inspect, then verify.</p></div><BoardButton variant="ghost" size="small" className="conversation-library-button" onClick={() => { initialConversationRestore.current = true; setLibraryOpen(true); }}><FolderOpen size={16} /> Change drawing</BoardButton></div>
        <div className="answer-panel-scroll">

          {!answer && !asking && !conversation.records.length && <section className="chat-empty"><span className="chat-assistant-label">Trace</span><h2>What do you need from this drawing?</h2><p>Ask about quantities, dimensions or rooms. Open the evidence to inspect the source.</p>{!selectedDocument && <BoardButton onClick={() => fileInputRef.current?.click()}><Upload size={16} /> Upload a drawing</BoardButton>}<div className="question-suggestions">{(suggestions.length ? suggestions : ['How many doors are shown?', 'What is the area of the largest labelled room?', 'Highlight the windows.']).slice(0, 3).map((item, i) => <button key={`${item}-${i}`} type="button" onClick={() => { setQuestion(item); questionRef.current?.focus(); }}><span>{item}</span><ArrowUp size={15} /></button>)}</div></section>}
          <ChatThread conversation={conversation} activeAnswer={answer} asking={asking} onInspect={restoreHistory} quantityUnit={quantityUnit}>
          {answer && !asking && <section className="answer-result chat-assistant-message" aria-live="polite">
            <div className="result-topline"><span className="chat-assistant-label">Trace</span><span className={`answer-status status-${resultStatus}`}>{['computed', 'extracted', 'supported'].includes(resultStatus) ? <Check size={12} /> : <CircleHelp size={12} />}{statusLabel[resultStatus] || readable(resultStatus)}</span><IconButton label="Download answer with evidence" onClick={downloadAnswer}><ArrowDownToLine size={15} /></IconButton></div>
            {answer.source_changed && <div className="source-changed-warning" role="alert"><strong>The source changed after this answer was saved.</strong><p>Old overlays and corrections are disabled. Recompute the answer against the current source.</p><button type="button" className="button" onClick={() => { const originalId = answerDocumentId; const originalQuestion = answerQuestion; const originalPage = answer.provenance?.page || 1; selectDocument(originalId, false, originalPage); setQuestion(originalQuestion); }}>Open source to recompute</button></div>}
            {answer.human_reviewed && <div className="reviewed-badge"><ShieldCheck size={13} /> Review saved{answer.review?.revision ? ` · revision ${answer.review.revision}` : ''}</div>}

            {answer.value != null && <div className="answer-value">{formatQuantityValue(answer.value, answer.unit)}{answer.unit && <span>{quantityUnit(answer)}</span>}</div>}
            <p className="answer-text">{shortText(answer.answer || answer.message || 'No answer was returned.')}</p>
            <div className="answer-metadata"><span>{readable(answer.method || 'Source analysis')}</span><span>{scopeText(answer.scope) || 'Requested source scope'}</span>{answer.duration_ms != null && <span>{(Number(answer.duration_ms) / 1000).toFixed(1)}s</span>}</div>
            <MessageInferenceCost usage={answer.usage} />
            <details className="answer-section-details"><summary>Calculation and usage</summary><UsageDetails answer={answer} />
            {answer.calculation && <div className="calculation"><span>Calculation</span><code>{calculationText(answer.calculation, answer)}</code></div>}
            </details>
            {warnings.length > 0 && <details className="answer-warnings"><summary><CircleHelp size={15} />{warnings.length} {warnings.length === 1 ? 'source note' : 'source notes'} to check</summary>{warnings.map((warning, i) => <p key={i}><span>{shortText(warning.message || warning)}</span></p>)}</details>}
            <ReconciliationDetails answer={answer} onSelect={selectEvidence} onResolve={resolveComparison} resolving={resolving} disabled={reviewing || hasReviewChanges || !!pendingManual} />
            <div className="evidence-section">
              <div className="section-label"><span>Source evidence</span><span>{evidence.length} {evidence.length === 1 ? 'source item' : 'source items'}</span></div>
              <div className="evidence-legend"><span><i className="native-key" /> Native source</span><span><i className="visual-key" /> Visual candidate</span><span><i className="manual-key" /> Added in review</span></div>
              {evidence.length > 0 && evidence.some(item => !evidenceBBox(item)) && <p className="evidence-coverage">{evidence.every(item => !evidenceBBox(item)) ? 'These records have no linked drawing location. Inspect their element IDs and properties.' : 'Some records have no linked drawing location. Inspect their element IDs and properties.'}</p>}
              {evidence.length ? <div className="evidence-list" aria-label="Answer source items">{evidence.map(item => <div key={item._key} className={`evidence-item evidence-kind-${evidenceKind(item)} ${item._key === selectedEvidence ? 'is-selected' : ''} ${excluded.includes(item._key) ? 'is-excluded' : ''}`}>
                <button type="button" className="evidence-select" disabled={answer.source_changed} onClick={() => selectEvidence(item)} aria-pressed={item._key === selectedEvidence}><span className="evidence-number">{item._number}</span><span><strong>{item.label || item.name || `Source ${item._number}`}</strong><small>{evidenceBBox(item) && item.page ? `Page ${item.page}` : item.guid ? 'Model element' : 'Source record'}{item.guid ? ` · ${item.guid.slice(0, 12)}…` : ''}</small><small className="evidence-origin">{({ native: 'Native source record', visual: 'Visual candidate · check interpretation', manual: answer.method?.startsWith('calibrated_') ? 'Your calibrated measurement' : 'Manually added during review' })[evidenceKind(item)]}</small></span><ChevronRight size={14} /></button>
                {answer.can_review && !answer.source_changed && <label className="evidence-review"><input type="checkbox" checked={!excluded.includes(item._key)} disabled={reviewing || resolving} onChange={event => toggleIncluded(item._key, event.target.checked)} /><span>Include in count</span></label>}
                {item._key === selectedEvidence && <div className="evidence-detail">{item.description && <p>{item.description}</p>}{item.quoted_text && <blockquote>{item.quoted_text}</blockquote>}<EvidenceProperties properties={item.properties} />{item.verification && <div className="evidence-verification"><strong>Source checks</strong>{evidenceVerificationText(item).map(message => <p key={message}>{message}</p>)}</div>}{item.note && <p>Review note: {item.note}</p>}{item.guid && <div className="element-reference">Element <code>{item.guid}</code></div>}{item.source && <small>{basename(item.source)}</small>}<EvidenceCloseup answer={answer} evidence={item} request={request} /></div>}
              </div>)}</div> : <div className="no-evidence">{resultStatus === 'insufficient_evidence' ? 'Try a more specific question or select the relevant drawing area.' : 'This answer did not include a locatable source region.'}</div>}
              {answer.can_review && !answer.source_changed && <details className="review-workspace" open={hasReviewChanges || !!pendingManual || undefined}><summary>Review this count{hasReviewChanges ? ' · unsaved changes' : ''}</summary>
                <div className="review-counts"><span>Original count<strong>{answer.original_value ?? answer.value}</strong></span><span>{hasReviewChanges ? 'Draft count' : answer.human_reviewed ? 'Reviewed count' : 'Included count'}<strong>{reviewedCount}</strong></span></div>
                <p className="review-help">Review changes the included set. Detection completeness remains unverified.</p>
                <div className="review-actions"><button type="button" className="button" onClick={startManual} disabled={reviewing || resolving || !selectedId}><Plus size={15} /> Add missed object</button><IconButton label="Undo last object change" onClick={undoReview} disabled={!reviewUndo.length || reviewing || resolving}><ArrowLeft size={16} /></IconButton><button type="button" className="text-button" onClick={restoreOriginal} disabled={reviewing || resolving || (!excluded.length && !manualAdditions.length && !reviewNote)}>Restore original</button></div>
                {pendingManual && <form className="manual-object-form" onSubmit={addManual} aria-label="Add a missed object">
                  <div><strong>Mark a missed object</strong><button type="button" onClick={cancelManual} aria-label="Cancel missing object"><X size={16} /></button></div>
                  <p>Drag a box or click the drawing. You can also enter page coordinates below.</p>
                  <label>Object label<input ref={manualLabelRef} value={manualLabel} maxLength={160} onChange={event => setManualLabel(event.target.value)} placeholder="For example, window beside room 5.11" required /></label>
                  <label>Count category{knownManualCategory ? <><input value={readable(knownManualCategory)} readOnly aria-label="Count category, fixed by original answer" /><small>Matches the original count. Add an object of this category.</small></> : <select value={manualCategory} onChange={event => setManualCategory(event.target.value)}>{(manualCategories.length ? manualCategories : [...reviewCategories, 'other']).map(kind => <option key={kind} value={kind}>{readable(kind)[0].toUpperCase() + readable(kind).slice(1)}</option>)}</select>}</label>
                  <fieldset><legend>Object bounds · page coordinates from 0 to 1</legend><div>{['Left', 'Top', 'Right', 'Bottom'].map((label, index) => <label key={label}>{label}<input type="number" min="0" max="1" step="0.001" value={pendingManual.bbox[index]} onChange={event => setPendingManual(current => ({ ...current, bbox: current.bbox.map((value, i) => i === index ? Number(event.target.value) : value) }))} required /></label>)}</div></fieldset>
                  <label>Object note (optional)<input value={manualNote} maxLength={500} onChange={event => setManualNote(event.target.value)} /></label>
                  {manualError && <p className="manual-error" role="alert">{manualError}</p>}
                  <div className="manual-form-actions"><button type="button" className="button" onClick={() => { setManualMode(true); setAnswerOpen(false); }}><SquareDashedMousePointer size={15} /> Mark on drawing</button><button type="submit" className="button primary"><Plus size={15} /> Add to count</button></div>
                </form>}
                <label className="review-note">Review note (optional)<textarea rows={2} value={reviewNote} maxLength={2000} disabled={reviewing || resolving} onChange={event => setReviewNote(event.target.value)} placeholder="Explain what you changed and why." /></label>
                <button type="button" className="button primary review-button" onClick={review} disabled={reviewing || resolving || (!hasReviewChanges && answer.human_reviewed)}>{reviewing ? <LoaderCircle size={15} className="spin" /> : <ShieldCheck size={15} />}{reviewing ? 'Saving review…' : 'Save reviewed count'}</button>
                <div className="review-save-state" role="status">{hasReviewChanges ? 'Unsaved review changes' : answer.review?.reviewed_at ? `Saved ${dateText(answer.review.reviewed_at)}` : 'Original answer is preserved when you save a review.'}</div>
                {answer.review && <details className="review-summary"><summary>Saved review changes</summary><p>{answer.review.original_value ?? answer.original_value} original → {answer.review.reviewed_value ?? answer.value} reviewed</p><p>{answer.review.added_count || 0} added · {answer.review.excluded_count || 0} excluded</p>{answer.review.note && <p>{answer.review.note}</p>}</details>}
              </details>}
            </div>
          </section>}
          </ChatThread>
          {askError && <div className="inline-error query-error" role="alert"><strong>{askError.startsWith('Stopped waiting') ? 'Stopped waiting' : 'Couldn’t complete the question'}</strong><span>{askError}</span>{askErrorUsage !== undefined && <MessageInferenceCost usage={askErrorUsage} label="Failed message" />}<button type="button" onClick={event => { setQuestion(pendingQuestion?.question || answerQuestion); questionRef.current?.focus(); }} disabled={asking}>Edit and retry</button></div>}
          {asking && <div className="chat-pending-question"><span className="chat-user-label">You</span><p>{pendingQuestion?.question}</p><span className="chat-user-context">{pendingQuestion?.documentName}</span></div>}
          {asking && <div className="analysis-progress" role="status" aria-live="polite"><div><LoaderCircle size={17} className="spin" /><strong>Tracing the answer</strong><span>{elapsed}s</span></div><p>Waiting for the server response. Detailed drawings may take longer.</p><button type="button" className="button cancel-analysis" onClick={() => cancelAsk(true)}>Stop waiting</button></div>}

          <div ref={conversationEndRef} className="conversation-end" />
          {restoringHistory && <p className="history-loading" role="status"><LoaderCircle size={14} className="spin" /> Checking the saved answer and source…</p>}
          {history.length > 0 && !asking && <details className="recent-questions"><summary>Saved answers</summary>{history.map(item => <button type="button" key={item.id || item.timestamp} title={`${item.question} · ${item.documentName}`} onClick={() => restoreHistory(item)}><MessageSquareText size={14} /><span><strong>{item.question}</strong><small>{item.documentName}</small><small className="history-cost">{messageCost(item.answer?.usage)}</small></span><ChevronRight size={13} /></button>)}</details>}
        </div>
        <form className="question-form" onSubmit={event => ask(event, crossCheck)}>
          <div className="composer-context"><FileText size={14} /><span title={documentName(selectedDocument)}>{selectedDocument ? documentName(selectedDocument) : 'Choose a drawing to start'}</span>{selectedDocument && <small>{region ? 'Selected area' : scope === 'page' ? `Page ${page}` : 'Whole drawing'}</small>}</div>
          <label className="sr-only" htmlFor="question-input">What do you need to know?</label>
          <div className={`question-input-wrap ${asking ? 'is-busy' : ''}`}><textarea ref={questionRef} id="question-input" placeholder="Ask a question about this drawing…" value={question} onChange={event => { initialConversationRestore.current = true; setQuestion(event.target.value); }} disabled={asking} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); ask(event, crossCheck); } }} rows={1} /><div className="composer-actions"><IconButton label="Upload drawings" onClick={() => fileInputRef.current?.click()} disabled={uploading}><Plus size={18} /></IconButton><span>Enter to send · Shift + Enter for a new line</span><button type="submit" className="ask-button" disabled={!question.trim() || !selectedId || asking} aria-label="Ask question">{asking ? <LoaderCircle size={18} className="spin" /> : <ArrowUp size={18} />}</button></div></div>
          <details className="analysis-options"><summary>Analysis options{region ? ' · selected area' : crossCheck || verifyVisual ? ' · custom' : ''}<ChevronDown size={14} /></summary><div className="analysis-options-body"><label className="query-options"><span>Search scope</span><select value={scope} onChange={event => changeScope(event.target.value)} disabled={!!region || asking}><option value="document">Whole document</option><option value="page">Current page</option></select></label><label className="cross-check-option"><input type="checkbox" checked={crossCheck} onChange={event => setCrossCheck(event.target.checked)} disabled={asking} /><span>Compare native and visual counts<small>May use a model request; scopes must match.</small></span></label><label className="cross-check-option"><input type="checkbox" checked={verifyVisual} onChange={event => setVerifyVisual(event.target.checked)} disabled={asking} /><span>Recheck visual counts<small>One extra model pass. May change or withhold the count.</small></span></label></div></details>
        </form>
      </aside>
    </div>
  </div>;
}

createRoot(document.getElementById('root')).render(<App />);
