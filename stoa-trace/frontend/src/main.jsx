import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { ArrowDownToLine, ArrowLeft, ArrowRight, ArrowUp, Box, Check, ChevronDown, ChevronLeft, ChevronRight, CircleHelp, Clock3, Crosshair, Eye, EyeOff, FileImage, FileText, FolderOpen, Layers3, LoaderCircle, Maximize, Menu, MessageSquareText, Minus, MousePointer2, PanelLeftClose, Plus, Search, ShieldCheck, SquareDashedMousePointer, Upload, X } from 'lucide-react';
import './styles.css';
import { evidenceBox, evidenceKind, savedAdditions, originalEvidence, reviewEvidence, reviewCount, reviewFingerprint, costText } from './reviewState.js';

const request = async (url, options = {}) => {
  const response = await fetch(url, options);
  const contentType = response.headers.get('content-type') || '';
  const body = contentType.includes('application/json') ? await response.json() : await response.text();
  if (!response.ok) throw new Error(typeof body === 'string' ? body : body.detail?.message || body.detail || body.error || `Request failed (${response.status})`);
  return body;
};
const jsonRequest = (url, body, options = {}) => request(url, { ...options, method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
const arrayOf = value => Array.isArray(value) ? value : [];
const basename = path => String(path || '').split(/[\\/]/).pop();
const documentName = doc => doc?.name || basename(doc?.path) || 'Untitled drawing';
const formatOf = doc => String(doc?.format || documentName(doc).split('.').pop() || '').replace(/^\./, '').toUpperCase();
const shortText = value => value == null ? '' : typeof value === 'object' ? JSON.stringify(value) : String(value);
const readable = value => shortText(value).replaceAll('_', ' ');
const collectionLabel = source => ({ swiss_dwellings: 'Swiss Dwellings', cubicasa5k: 'CubiCasa5K', opening_design: 'Opening Design', habs: 'HABS historic drawings', finna: 'Finna archives', europeana: 'Europeana', wikimedia: 'Wikimedia', ifc_models: 'IFC models', ifc_bench: 'IFC benchmark', uploads: 'Uploaded drawings' }[source] || readable(source));
const documentListUrl = (search, source, offset = 0) => {
  const params = new URLSearchParams({ search, limit: '60', offset: String(offset) });
  if (source) params.set('source', source);
  return `/api/documents?${params}`;
};
const dateText = value => { const date = new Date(typeof value === 'number' && value < 1e12 ? value * 1000 : value); return Number.isNaN(date.getTime()) ? 'Time unavailable' : date.toLocaleString(); };
const scopeText = scope => typeof scope === 'object' ? scope?.label || scope?.description || [scope?.type, scope?.page && `page ${scope.page}`].filter(Boolean).join(' · ') : readable(scope);
const statusLabel = { computed: 'Computed', supported: 'Source supported', extracted: 'Source extracted', visual: 'Visual analysis', needs_review: 'Needs review', insufficient_evidence: 'Evidence insufficient', human_reviewed: 'Human reviewed' };
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
  return <button type="button" className={`icon-button ${className}`} aria-label={label} title={label} {...props}>{children}</button>;
}

function DocumentIcon({ doc, size = 18 }) {
  return formatOf(doc) === 'IFC' ? <Box size={size} /> : ['PNG', 'JPG', 'JPEG', 'SVG'].includes(formatOf(doc)) ? <FileImage size={size} /> : <FileText size={size} />;
}

function DrawingCanvas({ document, page, evidence, selectedEvidence, onSelectEvidence, region, onRegion, focusToken, manualMode, onManualRegion, onCancelManual, imageVersion = 0 }) {
  const viewportRef = useRef(null);
  const dragRef = useRef(null);
  const transformRef = useRef({ x: 0, y: 0, scale: 1 });
  const [size, setSize] = useState({ width: 1000, height: 700 });
  const [viewSize, setViewSize] = useState({ width: 800, height: 600 });
  const [transform, setTransform] = useState(transformRef.current);
  const [imageState, setImageState] = useState('loading');
  const [showEvidence, setShowEvidence] = useState(true);
  const [tool, setTool] = useState('pan');
  const [draftRegion, setDraftRegion] = useState(null);
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
  useEffect(() => { setTool(manualMode ? 'manual' : 'pan'); }, [manualMode]);
  useEffect(() => { fit(); }, [fit, imageUrl]);
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
    dragRef.current = tool === 'region' || tool === 'manual' ? { type: tool, start: pointInDrawing(event) } : { type: 'pan', clientX: event.clientX, clientY: event.clientY, ...transformRef.current };
    if (tool === 'region' || tool === 'manual') { const [x, y] = dragRef.current.start; setDraftRegion([x, y, x, y]); }
  };
  const pointerMove = event => {
    const drag = dragRef.current;
    if (!drag) return;
    if (drag.type === 'pan') applyTransform({ x: drag.x + event.clientX - drag.clientX, y: drag.y + event.clientY - drag.clientY, scale: drag.scale });
    else {
      const [x, y] = pointInDrawing(event);
      setDraftRegion([Math.min(drag.start[0], x), Math.min(drag.start[1], y), Math.max(drag.start[0], x), Math.max(drag.start[1], y)]);
    }
  };
  const pointerUp = event => {
    const drag = dragRef.current;
    if (drag?.type === 'manual') {
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
  useEffect(() => { if (imageState === 'ready') { setShowEvidence(true); focusEvidence(); } }, [focusToken, imageState, focusEvidence]);
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
        <img key={imageUrl} src={imageUrl} alt={`${documentName(document)}, page ${page}`} draggable={false} onLoad={event => { setSize({ width: event.currentTarget.naturalWidth, height: event.currentTarget.naturalHeight }); setImageState('ready'); }} onError={() => setImageState('error')} />
        {showEvidence && <svg className="evidence-shapes" viewBox="0 0 1000 1000" preserveAspectRatio="none" aria-hidden="true">{evidence.map(item => {
          const box = evidenceBBox(item); const isSelected = item._key === selectedEvidence;
          return item.polygon?.length ? <polygon key={item._key} points={item.polygon.map(([x, y]) => `${x * 1000},${y * 1000}`).join(' ')} className={`${isSelected ? 'selected-shape' : ''} ${item._excluded ? 'excluded-shape' : ''} evidence-kind-${evidenceKind(item)}`} /> : box ? <rect key={item._key} x={box[0] * 1000} y={box[1] * 1000} width={(box[2] - box[0]) * 1000} height={(box[3] - box[1]) * 1000} className={`${isSelected ? 'selected-shape' : ''} ${item._excluded ? 'excluded-shape' : ''} evidence-kind-${evidenceKind(item)}`} /> : null;
        })}{activeRegion && <rect className="region-shape" x={activeRegion[0] * 1000} y={activeRegion[1] * 1000} width={(activeRegion[2] - activeRegion[0]) * 1000} height={(activeRegion[3] - activeRegion[1]) * 1000} />}</svg>}
        {showEvidence && evidence.map(item => {
          const box = evidenceBBox(item);
          if (!box) return null;
          return <button key={item._key} type="button" className={`evidence-marker ${item._key === selectedEvidence ? 'is-selected' : ''} ${item._excluded ? 'is-excluded' : ''} evidence-kind-${evidenceKind(item)}`} style={{ left: `${box[0] * 100}%`, top: `${box[1] * 100}%`, transform: `translate(-50%, -50%) scale(${1 / transform.scale})` }} aria-label={`Inspect source ${item._number}: ${item.label || 'Evidence'}`} aria-pressed={item._key === selectedEvidence} onClick={() => onSelectEvidence(item)}>{item._number}</button>;
        })}
      </div>}
      {imageState === 'loading' && <div className="canvas-message"><LoaderCircle className="spin" size={24} /><strong>Preparing drawing</strong><span>Opening the source at full resolution</span></div>}
      {imageState === 'error' && <div className="canvas-message canvas-fallback"><Box size={30} /><strong>{formatOf(document) === 'IFC' ? 'Building model' : 'Preview unavailable'}</strong><span>{formatOf(document) === 'IFC' ? 'Ask about the model’s objects, spaces, and quantities.' : 'You can still inspect the source and ask a question.'}</span>{arrayOf(document?.objects).length > 0 && <div className="native-objects"><strong>Model objects</strong>{document.objects.slice(0, 8).map((item, index) => <div key={item.id || item.guid || index}><span>{item.name || item.label || item.type || 'Element'}</span><small>{item.type || item.ifc_type || ''}</small></div>)}</div>}<a className="button secondary" href={`/api/documents/${encodeURIComponent(document.id)}/original`} target="_blank" rel="noreferrer"><ArrowDownToLine size={15} /> Open original</a></div>}
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
  const initial = answer?.ingestion_usage || usage?.ingestion_usage;
  const callsKnown = Number.isFinite(usage?.model_calls);
  if (!usage) return null;
  return <details className="usage-details"><summary>{usage.cache_hit ? 'Saved answer reused' : usage.inventory_cache_hit ? 'Prepared visual inventory reused' : callsKnown && usage.model_calls === 0 ? 'Native source tools' : 'Model analysis'} · {callsKnown ? `${usage.model_calls} model ${usage.model_calls === 1 ? 'call' : 'calls'}` : 'Call count unavailable'}</summary>
    <dl><dt>This question</dt><dd>{costText(usage)}</dd><dt>Input / output tokens</dt><dd>{Number(usage.input_tokens || 0).toLocaleString()} / {Number(usage.output_tokens || 0).toLocaleString()}</dd>{Number(usage.cached_input_tokens || 0) > 0 && <><dt>Cached input tokens</dt><dd>{Number(usage.cached_input_tokens).toLocaleString()}</dd></>}{answer.model && <><dt>Model</dt><dd>{answer.model}</dd></>}{initial && <><dt>Initial visual extraction</dt><dd>{Number(initial.model_calls || 0)} calls · {costText(initial)}</dd></>}</dl>
    <p>{usage.cost_estimate_usd == null && usage.cost_basis !== 'native' ? 'No token prices are configured. Usage is recorded; dollar cost is unknown.' : usage.cost_basis === 'native' ? 'No model inference was needed. Hosting and storage costs are separate.' : 'Estimate uses configured token rates, not a provider invoice.'}</p>
  </details>;
}

function ReconciliationDetails({ result, onSelect }) {
  if (!result) return null;
  return <section className={`reconciliation reconciliation-${result.status}`} aria-label="Count comparison"><div><strong>{({ agreement: 'Counts agree', disagreement: 'Counts disagree', scope_mismatch: 'Different scopes', unavailable: 'Comparison unavailable' })[result.status] || 'Count comparison'}</strong><span>{readable(result.status)}</span></div>{result.native_value != null && <dl><dt>Native source</dt><dd>{result.native_value} {result.unit || 'count'}</dd><dt>Visual candidates</dt><dd>{result.visual_value == null ? 'Unavailable' : `${result.visual_value} ${result.unit || 'count'}`}</dd></dl>}<p>{result.reason || 'Agreement between methods does not independently prove completeness.'}</p>{arrayOf(result.evidence).length > 0 && <details><summary>Inspect comparison candidates ({result.evidence.length})</summary>{result.evidence.map((item, index) => <button type="button" key={item.id || index} onClick={() => onSelect({ ...item, _key: `comparison-${item.id || index}`, _number: index + 1 })}><Eye size={14} /><span>{item.label || `Candidate ${index + 1}`}</span>{evidenceBBox(item) ? <Crosshair size={13} /> : <span>Record</span>}</button>)}</details>}</section>;
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
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState('');
  const [libraryOpen, setLibraryOpen] = useState(false);
  const [answerOpen, setAnswerOpen] = useState(false);
  const [refreshVersion, setRefreshVersion] = useState(0);
  const fileInputRef = useRef(null);
  const questionRef = useRef(null);
  const documentFilterRef = useRef('');
  const activeAskRef = useRef(null);
  const answerRef = useRef(answer);
  answerRef.current = answer;
  const askSequenceRef = useRef(0);
  const contextRef = useRef(null);
  const manualLabelRef = useRef(null);
  contextRef.current = JSON.stringify({ documentId: selectedId, page, scope, region });
  const selectedDocument = detail || documents.find(doc => String(doc.id) === String(selectedId));
  const evidence = useMemo(() => reviewEvidence(answer, manualAdditions).map((item, index) => ({ ...item, _key: evidenceKey(item, index), _number: index + 1 })), [answer, manualAdditions]);
  const canvasEvidence = [...evidence, ...(comparisonEvidence ? [comparisonEvidence] : []), ...(pendingManual ? [{ id: 'manual-preview', _key: 'manual-preview', _number: '+', label: manualLabel || 'Missing object', document_id: pendingManual.document_id, page: pendingManual.page, bbox: pendingManual.bbox, manual: true }] : [])].filter(item => String(item.document_id ?? answerDocumentId) === String(selectedId) && Number(item.page || 1) === page && evidenceBBox(item)).map(item => ({ ...item, _excluded: excluded.includes(item._key) }));
  const selectedEvidenceItem = evidence.find(item => item._key === selectedEvidence);
  const pageCount = Number(detail?.page_count || detail?.pages?.length || 1);
  const warnings = arrayOf(answer?.warnings);
  const resultStatus = getStatus(answer);
  const reviewedCount = reviewCount(answer, manualAdditions, excluded);
  const hasReviewChanges = !!answer && reviewFingerprint(excluded, manualAdditions, reviewNote) !== reviewFingerprint(savedExclusions(answer), savedAdditions(answer), answer.review?.note || '');
  const cancelAsk = useCallback((showNotice = false) => {
    const active = activeAskRef.current;
    if (!active) return;
    active.controller.abort(); activeAskRef.current = null; askSequenceRef.current += 1; setAsking(false);
    if (showNotice) setAskError('Stopped waiting for this answer. The server may finish an already-started model request.');
  }, []);
  const cancelManual = useCallback(() => { setManualMode(false); setPendingManual(null); setManualError(''); }, []);
  const loadReviewDraft = useCallback(result => {
    setExcluded(savedExclusions(result)); setManualAdditions(savedAdditions(result)); setReviewNote(result.review?.note || ''); setReviewUndo([]); cancelManual(); setComparisonEvidence(null);
  }, [cancelManual]);
  useEffect(() => () => activeAskRef.current?.controller.abort(), []);
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
    cancelAsk(); cancelManual(); setSelectedId(id); setPage(Number(requestedPage) || 1); setRegion(null); setLibraryOpen(false);
    if (!keepAnswer) { setAnswer(null); setSelectedEvidence(null); setAskError(''); setExcluded([]); setManualAdditions([]); setReviewNote(''); setReviewUndo([]); setScope('document'); setComparisonEvidence(null); }
  }, [cancelAsk, cancelManual]);
  const selectEvidence = useCallback(item => {
    cancelAsk(); cancelManual();
    setSelectedEvidence(item._key); setFocusToken(value => value + 1);
    if (String(item._key).startsWith('comparison-')) setComparisonEvidence(item);
    const targetDocument = item.document_id || answerDocumentId;
    if (targetDocument && String(targetDocument) !== String(selectedId)) selectDocument(targetDocument, true, item.page);
    else if (evidenceBBox(item) && item.page && Number(item.page) !== page) { setPage(Number(item.page)); setRegion(null); }
  }, [answerDocumentId, selectedId, page, selectDocument, cancelAsk, cancelManual]);
  const ask = async (event, crossCheck = false) => {
    event?.preventDefault();
    if (!question.trim() || !selectedId || asking) return;
    cancelManual(); setAsking(true); setAskError(''); setAnswerOpen(true);
    const questionText = question.trim(); const documentId = selectedId; const sourceName = documentName(selectedDocument);
    const context = contextRef.current, sequence = ++askSequenceRef.current, controller = new AbortController();
    activeAskRef.current = { sequence, controller, context };
    try {
      const result = await jsonRequest('/api/ask', { document_id: documentId, question: questionText, page, scope: region ? 'page' : scope, ...(region ? { region } : {}), mode: 'auto', cross_check: crossCheck }, { signal: controller.signal });
      if (controller.signal.aborted || activeAskRef.current?.sequence !== sequence || contextRef.current !== context) return;
      activeAskRef.current = null; setAsking(false);
      setAnswer(result); setAnswerDocumentId(documentId); setAnswerQuestion(questionText); setAnswerDocumentName(sourceName); loadReviewDraft(result);
      const primaryEvidence = allEvidence(result).find(item => evidenceBBox(item)) || allEvidence(result)[0];
      setSelectedEvidence(primaryEvidence ? evidenceKey(primaryEvidence, allEvidence(result).indexOf(primaryEvidence)) : null); setFocusToken(value => value + 1);
      if (primaryEvidence?.document_id && String(primaryEvidence.document_id) !== String(documentId)) selectDocument(primaryEvidence.document_id, true, primaryEvidence.page);
      else if (evidenceBBox(primaryEvidence) && primaryEvidence?.page && Number(primaryEvidence.page) !== page) setPage(Number(primaryEvidence.page));
      setHistory(items => mergeHistory(items, [historyItem(result, { question: questionText, documentId, documentName: sourceName, timestamp: Date.now() })]));
    } catch (error) { if (error.name !== 'AbortError' && activeAskRef.current?.sequence === sequence) setAskError(error.message); }
    finally { if (activeAskRef.current?.sequence === sequence) { activeAskRef.current = null; setAsking(false); } }
  };
  const askRegion = next => { cancelAsk(); cancelManual(); setRegion(next); };
  const changeScope = next => { cancelAsk(); cancelManual(); setScope(next); };
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
    if (!answer?.can_review) return;
    const first = evidence[0];
    const category = String(first?.category || first?.type || first?.label || '').toLowerCase();
    setManualCategory(['door', 'window', 'toilet', 'sink', 'bathtub', 'shower', 'room'].find(kind => category.includes(kind)) || 'other');
    setManualLabel(''); setManualNote(''); setManualError('');
    setPendingManual({ document_id: selectedId, page, bbox: [0.45, 0.45, 0.55, 0.55] }); setManualMode(true);
    requestAnimationFrame(() => manualLabelRef.current?.focus());
  };
  const markManual = bbox => { setPendingManual({ document_id: selectedId, page, bbox }); setManualMode(false); setAnswerOpen(true); requestAnimationFrame(() => manualLabelRef.current?.focus()); };
  const addManual = event => {
    event.preventDefault(); const box = pendingManual?.bbox;
    if (!manualLabel.trim()) { setManualError('Name the missing object.'); return; }
    if (!box || box.length !== 4 || !box.every(value => Number.isFinite(value) && value >= 0 && value <= 1) || box[0] >= box[2] || box[1] >= box[3]) { setManualError('Use page coordinates from 0 to 1, with left less than right and top less than bottom.'); return; }
    snapshotReview();
    const id = `manual-${window.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`}`;
    const item = { id, label: manualLabel.trim(), category: manualCategory, ...pendingManual, note: manualNote.trim(), manual: true };
    setManualAdditions(items => [...items, item]); setSelectedEvidence(id); setFocusToken(value => value + 1); cancelManual();
  };
  const review = async () => {
    if (!answer?.id) return;
    const answerId = answer.id;
    setReviewing(true); setAskError('');
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
  const restoreHistory = item => {
    const primaryEvidence = allEvidence(item.answer).find(source => evidenceBBox(source) || source.polygon?.length) || allEvidence(item.answer)[0];
    selectDocument(primaryEvidence?.document_id || item.documentId, true, primaryEvidence?.page || item.answer.provenance?.page);
    setQuestion(item.question); setAnswerQuestion(item.question); setAnswerDocumentName(item.documentName); setAnswer(item.answer); setAnswerDocumentId(item.documentId); loadReviewDraft(item.answer); setFocusToken(value => value + 1);
    setSelectedEvidence(primaryEvidence ? evidenceKey(primaryEvidence, allEvidence(item.answer).indexOf(primaryEvidence)) : null); setAnswerOpen(true);
    requestAnimationFrame(() => questionRef.current?.scrollIntoView({ block: 'start', behavior: 'auto' }));
  };
  const changePage = newPage => { cancelAsk(); cancelManual(); setPage(Math.max(1, Math.min(pageCount, newPage))); setRegion(null); };
  const sourceCredit = detail?.credit || detail?.attribution || detail?.license_credit;

  return <div className="app-shell">
    <header className="app-header"><div className="brand"><div className="brand-symbol" aria-hidden="true"><span /><span /><span /></div><span>trace<span className="brand-period">.</span></span><span className="brand-divider" /><span className="brand-description">Drawing intelligence</span></div><div className="header-right"><span className={`connection-state ${health?.status === 'offline' ? 'is-offline' : ''}`}><span />{health?.status === 'offline' ? 'Reconnecting' : health ? 'Workspace ready' : 'Connecting'}</span><span className="project-label">Junction 2026</span><div className="avatar" aria-label="Team workspace">T</div></div></header>
    <div className="mobile-toolbar"><button type="button" onClick={() => { setLibraryOpen(!libraryOpen); setAnswerOpen(false); }}><FolderOpen size={17} /> Drawings</button><span>{selectedDocument ? formatOf(selectedDocument) : 'Workspace'}</span><button type="button" onClick={() => { setAnswerOpen(!answerOpen); setLibraryOpen(false); }}><MessageSquareText size={17} /> Ask Trace</button></div>
    {(libraryOpen || answerOpen) && <button className="panel-scrim" aria-label="Close panel" onClick={() => { setLibraryOpen(false); setAnswerOpen(false); }} />}
    <div className="workspace-layout">
      <aside className={`document-library ${libraryOpen ? 'is-open' : ''}`} aria-label="Drawing library">
        <div className="library-heading"><div><span className="eyebrow">PROJECT LIBRARY</span><h1>Drawings <span>{total.toLocaleString()}</span></h1></div><IconButton label="Close drawing library" className="mobile-close" onClick={() => setLibraryOpen(false)}><X size={18} /></IconButton></div>
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
        <div className="library-footer"><input ref={fileInputRef} type="file" multiple accept=".pdf,.png,.jpg,.jpeg,.svg,.dxf,.dwg,.ifc" className="sr-only" onChange={event => uploadFiles(event.target.files)} /><button type="button" className="button upload-button" onClick={() => fileInputRef.current?.click()} disabled={uploading}>{uploading ? <LoaderCircle size={16} className="spin" /> : <Upload size={16} />}{uploading ? 'Adding drawings…' : 'Upload drawings'}</button>{uploadMessage && <p className="upload-feedback" role="status">{uploadMessage}</p>}<div className="library-footnote"><Layers3 size={13} /><span>PDF · CAD · BIM · images</span></div></div>
      </aside>
      <main className="main-drawing" aria-label="Selected drawing">
        {selectedDocument ? <><div className="drawing-heading"><div className="drawing-heading-main"><div className="breadcrumb">Project library <ChevronRight size={12} /> <span>{readable(selectedDocument.source || 'Uploaded drawings')}</span></div><h2 title={documentName(selectedDocument)}>{documentName(selectedDocument)}</h2></div><div className="drawing-heading-actions">{detailLoading && <LoaderCircle size={16} className="spin" />}{pageCount > 1 && <div className="page-controls"><IconButton label="Previous page" onClick={() => changePage(page - 1)} disabled={page <= 1}><ChevronLeft size={16} /></IconButton><label><span className="sr-only">Page</span><select aria-label="Page" value={page} onChange={event => changePage(Number(event.target.value))}>{Array.from({ length: pageCount }, (_, i) => <option key={i + 1} value={i + 1}>{i + 1}</option>)}</select><span>/ {pageCount}</span></label><IconButton label="Next page" onClick={() => changePage(page + 1)} disabled={page >= pageCount}><ChevronRight size={16} /></IconButton></div>}<a className="icon-button" href={`/api/documents/${encodeURIComponent(selectedId)}/original`} target="_blank" rel="noreferrer" title="Open original source" aria-label="Open original source"><ArrowDownToLine size={18} /></a></div></div>{detailError && <div className="drawing-warning" role="alert">{detailError}</div>}<DrawingCanvas document={selectedDocument} page={page} evidence={canvasEvidence} selectedEvidence={selectedEvidence} onSelectEvidence={selectEvidence} region={region} onRegion={askRegion} focusToken={focusToken} manualMode={manualMode} onManualRegion={markManual} onCancelManual={cancelManual} imageVersion={refreshVersion} />{sourceCredit && <details className="source-credit"><summary>Source &amp; licence · {readable(selectedDocument.source || 'Original drawing')}</summary><p>{shortText(sourceCredit)}{detail.license ? ` · ${shortText(detail.license)}` : ''}</p></details>}</> : <div className="workspace-empty"><div className="empty-illustration"><Layers3 size={42} /></div><span className="eyebrow">INSPECT THE SOURCE</span><h2>Start with a drawing.</h2><p>Find an answer in the details.<br />Inspect its source records and drawing evidence.</p><button type="button" className="button primary" onClick={() => fileInputRef.current?.click()}><Upload size={16} /> Upload drawings</button></div>}
      </main>
      <aside className={`answer-panel ${answerOpen ? 'is-open' : ''}`} aria-label="Ask Trace and inspect answers">
        <div className="answer-panel-heading"><div><span className="assistant-mark"><Crosshair size={17} /></span><h2>Ask Trace</h2></div><IconButton label="Close answer panel" className="mobile-close" onClick={() => setAnswerOpen(false)}><X size={18} /></IconButton><span className="evidence-badge"><ShieldCheck size={12} /> Evidence first</span></div>
        <div className="answer-panel-scroll">
          <form className="question-form" onSubmit={event => ask(event, crossCheck)}><label className="question-label" htmlFor="question-input">What do you need to know?</label><div className={`question-input-wrap ${asking ? 'is-busy' : ''}`}><textarea ref={questionRef} id="question-input" placeholder="Ask about rooms, quantities, dimensions, or materials…" value={question} onChange={event => setQuestion(event.target.value)} disabled={asking} onKeyDown={event => { if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) ask(event, crossCheck); }} rows={3} /><div className="question-input-footer"><span>{region ? 'Selected area' : scope === 'page' ? `Page ${page}` : 'Whole document'}</span><button type="submit" className="ask-button" disabled={!question.trim() || !selectedId || asking} aria-label="Ask question">{asking ? <LoaderCircle size={17} className="spin" /> : <ArrowUp size={18} />}</button></div></div><div className="query-options"><label><span>Search scope</span><select value={scope} onChange={event => changeScope(event.target.value)} disabled={!!region || asking}><option value="document">Whole document</option><option value="page">Current page</option></select></label><span className="keyboard-hint">⌘ ↵ to ask</span></div><label className="cross-check-option"><input type="checkbox" checked={crossCheck} onChange={event => setCrossCheck(event.target.checked)} disabled={asking} /><span>Compare native and visual counts<small>Optional. May use a model request; scopes must match.</small></span></label></form>
          {askError && <div className="inline-error query-error" role="alert"><strong>Couldn’t complete the question</strong><span>{askError}</span><button type="button" onClick={event => ask(event, crossCheck)} disabled={asking}>Try again</button></div>}
          {asking && <div className="analysis-progress" role="status" aria-live="polite"><div><LoaderCircle size={17} className="spin" /><strong>Tracing the answer</strong><span>{elapsed}s</span></div><p>Waiting for the server response. Detailed drawings may take longer.</p><button type="button" className="button cancel-analysis" onClick={() => cancelAsk(true)}>Stop waiting</button></div>}
          {!answer && !asking && <section className="suggestions-section"><div className="section-label"><span>START WITH A QUESTION</span><CircleHelp size={14} /></div>{suggestions.length ? <div className="question-suggestions">{suggestions.slice(0, 5).map((item, i) => <button key={`${item}-${i}`} type="button" onClick={() => { setQuestion(item); questionRef.current?.focus(); }}><span>{item}</span><ArrowUp size={14} /></button>)}</div> : <div className="question-empty"><div className="subtle-target"><Crosshair size={22} /></div><strong>From question to source.</strong><p>Ask in your own words. Trace will find the relevant objects or drawing regions and show its work.</p><div className="workflow-steps"><span><span>1</span> Ask a question</span><span><span>2</span> Inspect the evidence</span><span><span>3</span> Verify the result</span></div></div>}</section>}
          {answer && !asking && <section className="answer-result" aria-live="polite">
            <div className="result-topline"><span className={`answer-status status-${resultStatus}`}>{['computed', 'extracted', 'supported'].includes(resultStatus) ? <Check size={12} /> : <CircleHelp size={12} />}{statusLabel[resultStatus] || readable(resultStatus)}</span><IconButton label="Download answer with evidence" onClick={downloadAnswer}><ArrowDownToLine size={15} /></IconButton></div>
            {answer.human_reviewed && <div className="reviewed-badge"><ShieldCheck size={13} /> Review saved{answer.review?.revision ? ` · revision ${answer.review.revision}` : ''}</div>}
            <div className="answer-source-context"><strong>{answerQuestion}</strong><span>{answerDocumentName}{answer.provenance?.scope === 'page' ? ` · page ${answer.provenance.page}` : ''}{answer.provenance?.region ? ' · selected region' : ''}</span></div>
            {answer.value != null && <div className="answer-value">{shortText(answer.value)}{answer.unit && <span>{answer.unit}</span>}</div>}
            <p className="answer-text">{shortText(answer.answer || answer.message || 'No answer was returned.')}</p>
            <div className="answer-metadata"><span>{readable(answer.method || 'Source analysis')}</span><span>{scopeText(answer.scope) || 'Requested source scope'}</span>{answer.duration_ms != null && <span>{(Number(answer.duration_ms) / 1000).toFixed(1)}s</span>}</div>
            <UsageDetails answer={answer} />
            {answer.calculation && <div className="calculation"><span>Calculation</span><code>{calculationText(answer.calculation, answer)}</code></div>}
            {warnings.length > 0 && <div className="answer-warnings">{warnings.map((warning, i) => <p key={i}><CircleHelp size={14} /><span>{shortText(warning.message || warning)}</span></p>)}</div>}
            <ReconciliationDetails result={answer.reconciliation} onSelect={selectEvidence} />
            <div className="evidence-section">
              <div className="section-label"><span>SOURCE EVIDENCE</span><span>{evidence.length} {evidence.length === 1 ? 'source item' : 'source items'}</span></div>
              <div className="evidence-legend"><span><i className="native-key" /> Native source</span><span><i className="visual-key" /> Visual candidate</span><span><i className="manual-key" /> Added in review</span></div>
              {evidence.length > 0 && evidence.some(item => !evidenceBBox(item)) && <p className="evidence-coverage">{evidence.every(item => !evidenceBBox(item)) ? 'These records have no linked drawing location. Inspect their element IDs and properties.' : 'Some records have no linked drawing location. Inspect their element IDs and properties.'}</p>}
              {evidence.length ? <div className="evidence-list" aria-label="Answer source items">{evidence.map(item => <div key={item._key} className={`evidence-item evidence-kind-${evidenceKind(item)} ${item._key === selectedEvidence ? 'is-selected' : ''} ${excluded.includes(item._key) ? 'is-excluded' : ''}`}>
                <button type="button" className="evidence-select" onClick={() => selectEvidence(item)} aria-pressed={item._key === selectedEvidence}><span className="evidence-number">{item._number}</span><span><strong>{item.label || item.name || `Source ${item._number}`}</strong><small>{evidenceBBox(item) && item.page ? `Page ${item.page}` : item.guid ? 'Model element' : 'Source record'}{item.guid ? ` · ${item.guid.slice(0, 12)}…` : ''}</small><small className="evidence-origin">{({ native: 'Native source record', visual: 'Visual candidate · check interpretation', manual: 'Manually added during review' })[evidenceKind(item)]}</small></span><ChevronRight size={14} /></button>
                {answer.can_review && <label className="evidence-review"><input type="checkbox" checked={!excluded.includes(item._key)} disabled={reviewing} onChange={event => toggleIncluded(item._key, event.target.checked)} /><span>Include in count</span></label>}
                {item._key === selectedEvidence && <div className="evidence-detail">{item.description && <p>{item.description}</p>}{item.quoted_text && <blockquote>{item.quoted_text}</blockquote>}<EvidenceProperties properties={item.properties} />{item.note && <p>Review note: {item.note}</p>}{item.guid && <div className="element-reference">Element <code>{item.guid}</code></div>}{item.source && <small>{basename(item.source)}</small>}</div>}
              </div>)}</div> : <div className="no-evidence">{resultStatus === 'insufficient_evidence' ? 'Try a more specific question or select the relevant drawing area.' : 'This answer did not include a locatable source region.'}</div>}
              {answer.can_review && <div className="review-workspace">
                <div className="review-counts"><span>Original count<strong>{answer.original_value ?? answer.value}</strong></span><span>{hasReviewChanges ? 'Draft count' : answer.human_reviewed ? 'Reviewed count' : 'Included count'}<strong>{reviewedCount}</strong></span></div>
                <p className="review-help">Review changes the included set. Detection completeness remains unverified.</p>
                <div className="review-actions"><button type="button" className="button" onClick={startManual} disabled={reviewing || !selectedId}><Plus size={15} /> Add missed object</button><IconButton label="Undo last object change" onClick={undoReview} disabled={!reviewUndo.length || reviewing}><ArrowLeft size={16} /></IconButton><button type="button" className="text-button" onClick={restoreOriginal} disabled={reviewing || (!excluded.length && !manualAdditions.length && !reviewNote)}>Restore original</button></div>
                {pendingManual && <form className="manual-object-form" onSubmit={addManual} aria-label="Add a missed object">
                  <div><strong>Mark a missed object</strong><button type="button" onClick={cancelManual} aria-label="Cancel missing object"><X size={16} /></button></div>
                  <p>Drag a box or click the drawing. You can also enter page coordinates below.</p>
                  <label>Object label<input ref={manualLabelRef} value={manualLabel} maxLength={160} onChange={event => setManualLabel(event.target.value)} placeholder="For example, window beside room 5.11" required /></label>
                  <label>Category<select value={manualCategory} onChange={event => setManualCategory(event.target.value)}>{['door', 'window', 'toilet', 'sink', 'bathtub', 'shower', 'room', 'other'].map(kind => <option key={kind} value={kind}>{kind[0].toUpperCase() + kind.slice(1)}</option>)}</select></label>
                  <fieldset><legend>Object bounds · page coordinates from 0 to 1</legend><div>{['Left', 'Top', 'Right', 'Bottom'].map((label, index) => <label key={label}>{label}<input type="number" min="0" max="1" step="0.001" value={pendingManual.bbox[index]} onChange={event => setPendingManual(current => ({ ...current, bbox: current.bbox.map((value, i) => i === index ? Number(event.target.value) : value) }))} required /></label>)}</div></fieldset>
                  <label>Object note (optional)<input value={manualNote} maxLength={500} onChange={event => setManualNote(event.target.value)} /></label>
                  {manualError && <p className="manual-error" role="alert">{manualError}</p>}
                  <div className="manual-form-actions"><button type="button" className="button" onClick={() => { setManualMode(true); setAnswerOpen(false); }}><SquareDashedMousePointer size={15} /> Mark on drawing</button><button type="submit" className="button primary"><Plus size={15} /> Add to count</button></div>
                </form>}
                <label className="review-note">Review note (optional)<textarea rows={2} value={reviewNote} maxLength={2000} disabled={reviewing} onChange={event => setReviewNote(event.target.value)} placeholder="Explain what you changed and why." /></label>
                <button type="button" className="button primary review-button" onClick={review} disabled={reviewing || (!hasReviewChanges && answer.human_reviewed)}>{reviewing ? <LoaderCircle size={15} className="spin" /> : <ShieldCheck size={15} />}{reviewing ? 'Saving review…' : 'Save reviewed count'}</button>
                <div className="review-save-state" role="status">{hasReviewChanges ? 'Unsaved review changes' : answer.review?.reviewed_at ? `Saved ${dateText(answer.review.reviewed_at)}` : 'Original answer is preserved when you save a review.'}</div>
                {answer.review && <details className="review-summary"><summary>Saved review changes</summary><p>{answer.review.original_value ?? answer.original_value} original → {answer.review.reviewed_value ?? answer.value} reviewed</p><p>{answer.review.added_count || 0} added · {answer.review.excluded_count || 0} excluded</p>{answer.review.note && <p>{answer.review.note}</p>}</details>}
              </div>}
            </div>
          </section>}
          {history.length > 0 && !asking && <section className="recent-questions"><div className="section-label"><span>RECENT QUESTIONS</span><Clock3 size={13} /></div>{history.map(item => <button type="button" key={item.id || item.timestamp} title={`${item.question} · ${item.documentName}`} onClick={() => restoreHistory(item)}><MessageSquareText size={14} /><span><strong>{item.question}</strong><small>{item.documentName}</small></span><ChevronRight size={13} /></button>)}</section>}
        </div>
        <footer className="answer-panel-footer"><ShieldCheck size={14} /><span>Inspect sources before making site decisions.</span></footer>
      </aside>
    </div>
  </div>;
}

createRoot(document.getElementById('root')).render(<App />);
