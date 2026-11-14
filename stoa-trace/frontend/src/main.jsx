import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Activity,
  ArrowDownToLine,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  Box,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  Clock3,
  Coins,
  Command,
  Cpu,
  Crosshair,
  ExternalLink,
  Eye,
  EyeOff,
  FileImage,
  FileText,
  Filter,
  FolderOpen,
  Layers,
  Layers3,
  LoaderCircle,
  Maximize,
  Menu,
  MessageSquareText,
  Minus,
  MousePointer2,
  Plus,
  RotateCcw,
  Search,
  Settings,
  ShieldCheck,
  Sliders,
  SlidersHorizontal,
  SquareDashedMousePointer,
  Upload,
  X,
  Zap,
} from 'lucide-react';
import './styles.css';
import {
  evidenceBox,
  evidenceBoxCenter,
  evidenceKind,
  savedAdditions,
  originalEvidence,
  reviewEvidence,
  reviewCount,
  reviewFingerprint,
  costText,
  aggregateUsage,
  countedCategory,
  canonicalCategory,
  reviewCategories,
  usageLabel,
  evidenceVerificationText,
  canResolveComparison,
  formatQuantityValue,
  createSessionTracker,
  recordSessionQuery,
  formatCostDetail,
  displayQuantity,
} from './reviewState.js';

// Network request helpers
const request = async (url, options = {}) => {
  const response = await fetch(url, options);
  const contentType = response.headers.get('content-type') || '';
  const body = contentType.includes('application/json') ? await response.json() : await response.text();
  if (!response.ok) {
    throw new Error(typeof body === 'string' ? body : body.detail?.message || body.detail || body.error || `Request failed (${response.status})`);
  }
  return body;
};

const jsonRequest = (url, body, options = {}) =>
  request(url, { ...options, method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

const arrayOf = value => (Array.isArray(value) ? value : []);
const basename = path => String(path || '').split(/[\\/]/).pop();
const documentName = doc => doc?.name || basename(doc?.path) || 'Untitled drawing';
const formatOf = doc => String(doc?.format || documentName(doc).split('.').pop() || '').replace(/^\./, '').toUpperCase();
const shortText = value => (value == null ? '' : typeof value === 'object' ? JSON.stringify(value) : String(value));
const readable = value => shortText(value).replaceAll('_', ' ');

const collectionLabel = source =>
  ({
    swiss_dwellings: 'Swiss Dwellings',
    cubicasa5k: 'CubiCasa5K',
    opening_design: 'Opening Design',
    habs: 'HABS Historic Drawings',
    finna: 'Finna Archives',
    europeana: 'Europeana',
    wikimedia: 'Wikimedia Commons',
    ifc_models: 'IFC BIM Models',
    ifc_bench: 'IFC Benchmark',
    uploads: 'Uploaded Drawings',
  }[source] || readable(source));

const documentListUrl = (search, source, offset = 0) => {
  const params = new URLSearchParams({ search, limit: '60', offset: String(offset) });
  if (source) params.set('source', source);
  return `/api/documents?${params}`;
};

const dateText = value => {
  const date = new Date(typeof value === 'number' && value < 1e12 ? value * 1000 : value);
  return Number.isNaN(date.getTime()) ? 'Time unavailable' : date.toLocaleString();
};

const scopeText = scope =>
  typeof scope === 'object'
    ? scope?.label || scope?.description || [scope?.type, scope?.page && `page ${scope.page}`].filter(Boolean).join(' · ')
    : readable(scope);

const statusLabel = {
  computed: 'Deterministic',
  supported: 'Source Supported',
  extracted: 'Source Extracted',
  visual: 'Visual Extraction',
  needs_review: 'Needs Review',
  insufficient_evidence: 'Evidence Insufficient',
  human_reviewed: 'Verified by Reviewer',
};

const getStatus = answer => answer?.status || 'needs_review';
const allEvidence = answer => arrayOf(answer?.evidence);
const evidenceKey = (e, i) => String(e.id ?? `evidence-${i}`);

const normalizeDetails = payload =>
  payload?.document
    ? {
        ...payload.document,
        pages: payload.pages || payload.document.pages,
        objects: payload.objects || payload.document.objects,
        warnings: payload.warnings || payload.document.warnings,
      }
    : payload;

const calculationText = (calculation, answer) => {
  if (typeof calculation !== 'object') return shortText(calculation);
  if (calculation.formula || calculation.expression) return calculation.formula || calculation.expression;
  if (String(calculation.operation).includes('count')) {
    const nativeClass = arrayOf(calculation.classes).find(item => String(item).startsWith('Ifc'));
    const kind = nativeClass ? nativeClass.replace(/^Ifc/, '').replace(/([a-z])([A-Z])/g, '$1 $2').toLowerCase() : 'model';
    return `${calculation.count ?? answer.value} unique ${kind} elements`;
  }
  return Object.entries(calculation)
    .filter(([key]) => key !== 'operation')
    .map(([key, value]) => `${readable(key)}: ${shortText(value)}`)
    .join(' · ');
};

const savedExclusions = answer => {
  const explicit = arrayOf(answer?.excluded_evidence_ids || answer?.review?.excluded_evidence_ids || answer?.human_review?.excluded_evidence_ids).map(String);
  const flagged = allEvidence(answer).flatMap((item, index) =>
    item.excluded === true || item.included === false || item.status === 'excluded' ? [evidenceKey(item, index)] : []
  );
  return [...new Set([...explicit, ...flagged])];
};

const historyItem = (answer, fallback = {}) => {
  const savedTime = answer.created_at || answer.updated_at;
  const parsedTime = typeof savedTime === 'number' ? (savedTime < 1e12 ? savedTime * 1000 : savedTime) : Date.parse(savedTime);
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

function DocumentIcon({ doc, size = 16 }) {
  const format = formatOf(doc);
  if (format === 'IFC') return <Box size={size} />;
  if (['PNG', 'JPG', 'JPEG', 'SVG'].includes(format)) return <FileImage size={size} />;
  return <FileText size={size} />;
}

/* ==========================================================================
   Interactive Drawing Canvas Component
   ========================================================================== */

function DrawingCanvas({
  document,
  page,
  evidence,
  selectedEvidence,
  onSelectEvidence,
  hoveredEvidence,
  onHoverEvidence,
  onToggleExclude,
  region,
  onRegion,
  focusToken,
  manualMode,
  onManualRegion,
  onCancelManual,
  imageVersion = 0,
  highContrast = false,
  showLabels = false,
  unitSystem = 'metric',
}) {
  const viewportRef = useRef(null);
  const dragRef = useRef(null);
  const transformRef = useRef({ x: 0, y: 0, scale: 1 });
  const [size, setSize] = useState({ width: 1000, height: 700 });
  const [viewSize, setViewSize] = useState({ width: 800, height: 600 });
  const [transform, setTransform] = useState(transformRef.current);
  const [imageState, setImageState] = useState('loading');
  const [showEvidence, setShowEvidence] = useState(true);
  const [spotlightMode, setSpotlightMode] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [tool, setTool] = useState('pan');
  const [draftRegion, setDraftRegion] = useState(null);
  const [pointerCoords, setPointerCoords] = useState(null);
  const [localHoveredKey, setLocalHoveredKey] = useState(null);

  const applyTransform = useCallback(next => {
    transformRef.current = next;
    setTransform(next);
  }, []);

  const imageUrl = document?.id
    ? `/api/documents/${encodeURIComponent(document.id)}/pages/${page}/image?v=${imageVersion}`
    : null;

  const fit = useCallback(() => {
    const scale = Math.min((viewSize.width - 50) / size.width, (viewSize.height - 50) / size.height);
    const nextScale = Math.max(0.015, scale);
    applyTransform({
      x: (viewSize.width - size.width * nextScale) / 2,
      y: (viewSize.height - size.height * nextScale) / 2,
      scale: nextScale,
    });
  }, [viewSize, size, applyTransform]);

  useEffect(() => {
    const element = viewportRef.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) =>
      setViewSize({ width: entry.contentRect.width, height: entry.contentRect.height })
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    setImageState('loading');
    setTool('pan');
  }, [imageUrl]);

  useEffect(() => {
    setTool(manualMode ? 'manual' : 'pan');
  }, [manualMode]);

  useEffect(() => {
    fit();
  }, [fit, imageUrl]);

  const zoomAt = useCallback(
    (factor, cx = viewSize.width / 2, cy = viewSize.height / 2) => {
      const current = transformRef.current;
      const scale = Math.min(20, Math.max(0.01, current.scale * factor));
      const ratio = scale / current.scale;
      applyTransform({ x: cx - (cx - current.x) * ratio, y: cy - (cy - current.y) * ratio, scale });
    },
    [viewSize, applyTransform]
  );

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
    return [
      Math.max(0, Math.min(1, (event.clientX - rect.left - t.x) / (size.width * t.scale))),
      Math.max(0, Math.min(1, (event.clientY - rect.top - t.y) / (size.height * t.scale))),
    ];
  };

  const handlePointerDown = event => {
    if (event.button !== 0 || event.target.closest('button')) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current =
      tool === 'region' || tool === 'manual'
        ? { type: tool, start: pointInDrawing(event) }
        : { type: 'pan', clientX: event.clientX, clientY: event.clientY, ...transformRef.current };

    if (tool === 'region' || tool === 'manual') {
      const [x, y] = dragRef.current.start;
      setDraftRegion([x, y, x, y]);
    }
  };

  const handlePointerMove = event => {
    const [x, y] = pointInDrawing(event);
    setPointerCoords({ x, y });

    const drag = dragRef.current;
    if (!drag) return;
    if (drag.type === 'pan') {
      applyTransform({
        x: drag.x + event.clientX - drag.clientX,
        y: drag.y + event.clientY - drag.clientY,
        scale: drag.scale,
      });
    } else {
      setDraftRegion([
        Math.min(drag.start[0], x),
        Math.min(drag.start[1], y),
        Math.max(drag.start[0], x),
        Math.max(drag.start[1], y),
      ]);
    }
  };

  const handlePointerUp = event => {
    const drag = dragRef.current;
    if (drag?.type === 'manual') {
      const end = event ? pointInDrawing(event) : drag.start;
      let box = draftRegion;
      if (!box || box[2] - box[0] < 0.003 || box[3] - box[1] < 0.003) {
        const x = end[0],
          y = end[1],
          half = 0.008;
        box = [Math.max(0, x - half), Math.max(0, y - half), Math.min(1, x + half), Math.min(1, y + half)];
      }
      onManualRegion(box);
    } else if (
      drag?.type === 'region' &&
      draftRegion &&
      draftRegion[2] - draftRegion[0] > 0.005 &&
      draftRegion[3] - draftRegion[1] > 0.005
    ) {
      onRegion(draftRegion);
    }
    setDraftRegion(null);
    dragRef.current = null;
  };

  const focusedBoxKey = JSON.stringify(evidenceBox(evidence.find(item => item._key === selectedEvidence)));
  const focusEvidence = useCallback(() => {
    const box = JSON.parse(focusedBoxKey);
    if (!box) return;
    const width = Math.max(0.025, box[2] - box[0]) * size.width;
    const height = Math.max(0.025, box[3] - box[1]) * size.height;
    const scale = Math.min(8, Math.min((viewSize.width * 0.65) / width, (viewSize.height * 0.65) / height));
    applyTransform({
      scale,
      x: viewSize.width / 2 - ((box[0] + box[2]) / 2) * size.width * scale,
      y: viewSize.height / 2 - ((box[1] + box[3]) / 2) * size.height * scale,
    });
  }, [focusedBoxKey, size.width, size.height, viewSize.width, viewSize.height, applyTransform]);

  useEffect(() => {
    if (imageState === 'ready' && selectedEvidence) {
      setShowEvidence(true);
      focusEvidence();
    }
  }, [focusToken, imageState, focusEvidence, selectedEvidence]);

  const activeRegion = draftRegion || region;

  // Filter evidence by category if requested
  const categoriesInEvidence = useMemo(() => {
    const map = new Map();
    evidence.forEach(item => {
      const cat = item.category || item.type || 'object';
      map.set(cat, (map.get(cat) || 0) + 1);
    });
    return [...map.entries()];
  }, [evidence]);

  const filteredEvidence = useMemo(() => {
    if (categoryFilter === 'all') return evidence;
    return evidence.filter(item => (item.category || item.type || 'object') === categoryFilter);
  }, [evidence, categoryFilter]);

  const activeHoverKey = localHoveredKey || hoveredEvidence;
  const activePopoverItem = evidence.find(
    item => item._key === activeHoverKey || (item._key === selectedEvidence && !activeHoverKey)
  );

  return (
    <div className={`canvas-wrapper ${spotlightMode ? 'spotlight-active' : ''} ${highContrast ? 'high-contrast-canvas' : ''}`}>
      {/* Floating Canvas Action Toolbar */}
      <div className="canvas-floating-toolbar">
        <div className="segmented-group">
          <button
            type="button"
            className={`toolbar-btn ${tool === 'pan' ? 'is-active' : ''}`}
            title="Pan drawing (Drag to pan)"
            onClick={() => setTool('pan')}
          >
            <MousePointer2 size={15} />
          </button>
          <button
            type="button"
            className={`toolbar-btn ${tool === 'region' ? 'is-active' : ''}`}
            title="Select drawing area to query"
            disabled={imageState !== 'ready'}
            onClick={() => setTool('region')}
          >
            <SquareDashedMousePointer size={15} />
          </button>
        </div>

        <div className="toolbar-separator" />

        <button
          type="button"
          className={`toolbar-btn ${showEvidence ? 'is-active' : ''}`}
          title={showEvidence ? 'Hide highlighted shapes' : 'Show highlighted shapes'}
          onClick={() => setShowEvidence(!showEvidence)}
        >
          {showEvidence ? <Eye size={15} /> : <EyeOff size={15} />}
        </button>

        <button
          type="button"
          className={`toolbar-btn ${spotlightMode ? 'is-active' : ''}`}
          title={spotlightMode ? 'Disable spotlight dimming' : 'Enable spotlight (dim drawing to highlight shapes)'}
          onClick={() => setSpotlightMode(!spotlightMode)}
        >
          <Layers size={15} />
        </button>

        <button
          type="button"
          className="toolbar-btn"
          title="Center on selected shape"
          disabled={focusedBoxKey === 'null'}
          onClick={focusEvidence}
        >
          <Crosshair size={15} />
        </button>

        <button type="button" className="toolbar-btn" title="Fit to view (0)" onClick={fit}>
          <Maximize size={15} />
        </button>
      </div>

      {/* Category Filter Chips Bar on Canvas */}
      {showEvidence && categoriesInEvidence.length > 1 && (
        <div className="canvas-category-bar">
          <button
            type="button"
            className={`category-chip ${categoryFilter === 'all' ? 'is-active' : ''}`}
            onClick={() => setCategoryFilter('all')}
          >
            All Shapes <span className="category-chip-count">{evidence.length}</span>
          </button>
          {categoriesInEvidence.map(([cat, count]) => (
            <button
              key={cat}
              type="button"
              className={`category-chip ${categoryFilter === cat ? 'is-active' : ''}`}
              onClick={() => setCategoryFilter(cat)}
            >
              {readable(cat)} <span className="category-chip-count">{count}</span>
            </button>
          ))}
        </div>
      )}

      {/* Main Drawing Viewport */}
      <div
        ref={viewportRef}
        className={`canvas-viewport tool-${tool}`}
        tabIndex={0}
        role="region"
        aria-label="Interactive drawing canvas. Drag to pan, scroll to zoom. Use plus, minus, or zero to fit."
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={() => {
          setDraftRegion(null);
          dragRef.current = null;
        }}
        onKeyDown={event => {
          if (event.key === '+' || event.key === '=') {
            event.preventDefault();
            zoomAt(1.25);
          }
          if (event.key === '-') {
            event.preventDefault();
            zoomAt(0.8);
          }
          if (event.key === '0') {
            event.preventDefault();
            fit();
          }
        }}
      >
        {imageUrl && (
          <div
            className={`drawing-stage ${imageState === 'ready' ? 'is-ready' : ''}`}
            style={{
              width: size.width,
              height: size.height,
              transform: `translate(${transform.x}px, ${transform.y}px) scale(${transform.scale})`,
            }}
          >
            <img
              key={imageUrl}
              src={imageUrl}
              alt={`${documentName(document)}, page ${page}`}
              draggable={false}
              onLoad={event => {
                setSize({ width: event.currentTarget.naturalWidth, height: event.currentTarget.naturalHeight });
                setImageState('ready');
              }}
              onError={() => setImageState('error')}
            />

            {/* Interactive SVG Shapes Layer */}
            {showEvidence && (
              <svg className="evidence-shapes" viewBox="0 0 1000 1000" preserveAspectRatio="none">
                <defs>
                  <filter id="shape-glow-blue" x="-20%" y="-20%" width="140%" height="140%">
                    <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#0070f3" floodOpacity="0.85" />
                  </filter>
                  <filter id="shape-glow-amber" x="-20%" y="-20%" width="140%" height="140%">
                    <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#f59e0b" floodOpacity="0.85" />
                  </filter>
                  <filter id="shape-glow-emerald" x="-20%" y="-20%" width="140%" height="140%">
                    <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#10b981" floodOpacity="0.85" />
                  </filter>
                </defs>

                {filteredEvidence.map(item => {
                  const box = evidenceBox(item);
                  const isSelected = item._key === selectedEvidence;
                  const isHovered = item._key === activeHoverKey;
                  const kind = evidenceKind(item);

                  const commonProps = {
                    key: item._key,
                    className: `evidence-shape kind-${kind} ${isSelected ? 'is-selected' : ''} ${
                      isHovered ? 'is-hovered' : ''
                    } ${item._excluded ? 'is-excluded' : ''}`,
                    onPointerEnter: e => {
                      e.stopPropagation();
                      setLocalHoveredKey(item._key);
                      onHoverEvidence?.(item._key);
                    },
                    onPointerLeave: () => {
                      setLocalHoveredKey(null);
                      onHoverEvidence?.(null);
                    },
                    onClick: e => {
                      e.stopPropagation();
                      onSelectEvidence(item);
                    },
                  };

                  if (item.polygon?.length) {
                    return (
                      <polygon
                        {...commonProps}
                        points={item.polygon.map(([x, y]) => `${x * 1000},${y * 1000}`).join(' ')}
                      />
                    );
                  }

                  if (box) {
                    return (
                      <rect
                        {...commonProps}
                        x={box[0] * 1000}
                        y={box[1] * 1000}
                        width={(box[2] - box[0]) * 1000}
                        height={(box[3] - box[1]) * 1000}
                        rx="3"
                        ry="3"
                      />
                    );
                  }
                  return null;
                })}

                {/* Active user drag selection area */}
                {activeRegion && (
                  <rect
                    className="region-shape"
                    x={activeRegion[0] * 1000}
                    y={activeRegion[1] * 1000}
                    width={(activeRegion[2] - activeRegion[0]) * 1000}
                    height={(activeRegion[3] - activeRegion[1]) * 1000}
                  />
                )}
              </svg>
            )}

            {/* Marker badges on shapes */}
            {showEvidence &&
              filteredEvidence.map(item => {
                const box = evidenceBox(item);
                if (!box) return null;
                const isSelected = item._key === selectedEvidence;
                const isHovered = item._key === activeHoverKey;
                const kind = evidenceKind(item);

                return (
                  <button
                    key={`marker-${item._key}`}
                    type="button"
                    className={`evidence-marker kind-${kind} ${isSelected ? 'is-selected' : ''} ${
                      isHovered ? 'is-hovered' : ''
                    } ${item._excluded ? 'is-excluded' : ''} ${showLabels ? 'has-label' : ''}`}
                    style={{
                      left: `${box[0] * 100}%`,
                      top: `${box[1] * 100}%`,
                      transform: `translate(-50%, -50%) scale(${1 / transform.scale})`,
                    }}
                    aria-label={`Inspect source #${item._number}: ${item.label || 'Evidence'}`}
                    onPointerEnter={() => {
                      setLocalHoveredKey(item._key);
                      onHoverEvidence?.(item._key);
                    }}
                    onPointerLeave={() => {
                      setLocalHoveredKey(null);
                      onHoverEvidence?.(null);
                    }}
                    onClick={() => onSelectEvidence(item)}
                  >
                    {item._number}
                    {showLabels && (item.label || item.name) && (
                      <span className="evidence-marker-label">{shortText(item.label || item.name)}</span>
                    )}
                  </button>
                );
              })}

            {/* Floating Interactive Shape Popover HUD on the Plant */}
            {showEvidence && activePopoverItem && evidenceBox(activePopoverItem) && (
              (() => {
                const box = evidenceBox(activePopoverItem);
                const cx = (box[0] + box[2]) / 2;
                const cy = box[1];
                const kind = evidenceKind(activePopoverItem);
                const area = activePopoverItem.area || activePopoverItem.properties?.area;
                const roomNum = activePopoverItem.room_number || activePopoverItem.properties?.room_number;
                const shownArea = displayQuantity(area, 'm²', unitSystem);

                return (
                  <div
                    className="shape-popover"
                    style={{
                      left: `${cx * 100}%`,
                      top: `${Math.max(0.02, cy) * 100}%`,
                      transform: `translate(-50%, -100%) scale(${1 / transform.scale})`,
                    }}
                    onPointerEnter={() => setLocalHoveredKey(activePopoverItem._key)}
                    onPointerLeave={() => setLocalHoveredKey(null)}
                  >
                    <div className="shape-popover-header">
                      <span className="shape-number-pill">#{activePopoverItem._number}</span>
                      <span className={`shape-kind-badge kind-${kind}`}>
                        {kind === 'native' ? 'Native CAD' : kind === 'visual' ? 'Visual Candidate' : 'Manual'}
                      </span>
                    </div>

                    <div className="shape-popover-title">
                      {activePopoverItem.label || activePopoverItem.name || 'Plant Object'}
                    </div>

                    <div className="shape-popover-meta">
                      {roomNum && <span>Room {roomNum}</span>}
                      {area && (
                        <span>
                          Area:{' '}
                          {typeof area === 'number' ? `${formatQuantityValue(shownArea.value, shownArea.unit)} ${shownArea.unit}` : area}
                        </span>
                      )}
                      {activePopoverItem.page && <span>Page {activePopoverItem.page}</span>}
                    </div>

                    <div className="shape-popover-actions">
                      <button
                        type="button"
                        className="popover-action-btn"
                        onClick={e => {
                          e.stopPropagation();
                          focusEvidence();
                        }}
                      >
                        <Crosshair size={12} /> Focus
                      </button>
                      <button
                        type="button"
                        className={`popover-action-btn ${activePopoverItem._excluded ? 'is-excluded' : ''}`}
                        onClick={e => {
                          e.stopPropagation();
                          onToggleExclude?.(activePopoverItem._key, !activePopoverItem._excluded);
                        }}
                      >
                        {activePopoverItem._excluded ? <Eye size={12} /> : <EyeOff size={12} />}
                        {activePopoverItem._excluded ? 'Include' : 'Exclude'}
                      </button>
                    </div>
                  </div>
                );
              })()
            )}
          </div>
        )}

        {imageState === 'loading' && (
          <div className="canvas-message">
            <LoaderCircle className="spin" size={28} />
            <strong>Rendering Drawing</strong>
            <span>Opening the source drawing at full resolution</span>
          </div>
        )}

        {imageState === 'error' && (
          <div className="canvas-message">
            <Box size={32} />
            <strong>{formatOf(document) === 'IFC' ? 'Building Information Model' : 'Preview Unavailable'}</strong>
            <span>You can still inspect native source records and ask questions.</span>
            <a
              className="btn-secondary"
              href={`/api/documents/${encodeURIComponent(document.id)}/original`}
              target="_blank"
              rel="noreferrer"
            >
              <ArrowDownToLine size={14} /> Open Original Source
            </a>
          </div>
        )}
      </div>

      {/* Canvas Footer HUD */}
      <footer className="canvas-footer">
        <div className="canvas-hud">
          {pointerCoords && (
            <span className="hud-pill">
              X: {(pointerCoords.x * 100).toFixed(1)}% Y: {(pointerCoords.y * 100).toFixed(1)}%
            </span>
          )}
          {activePopoverItem && (
            <span className="hud-pill">
              Shape #{activePopoverItem._number}: {activePopoverItem.label || 'Selected'}
            </span>
          )}
        </div>

        <div className="zoom-controls">
          <button type="button" className="icon-btn" title="Zoom out (-)" onClick={() => zoomAt(0.8)}>
            <Minus size={14} />
          </button>
          <span className="zoom-pct">{Math.round(transform.scale * 100)}%</span>
          <button type="button" className="icon-btn" title="Zoom in (+)" onClick={() => zoomAt(1.25)}>
            <Plus size={14} />
          </button>
          <button type="button" className="icon-btn" title="Fit to view (0)" onClick={fit}>
            <Maximize size={14} />
          </button>
        </div>
      </footer>
    </div>
  );
}

/* ==========================================================================
   Main Application Component
   ========================================================================== */

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
  const [hoveredEvidence, setHoveredEvidence] = useState(null);
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
  const [resolving, setResolving] = useState(false);
  const [restoringHistory, setRestoringHistory] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState('');
  const [activeTab, setActiveTab] = useState('evidence');
  const [refreshVersion, setRefreshVersion] = useState(0);

  // Settings & Cost Telemetry State
  const [sidebarTab, setSidebarTab] = useState('settings'); // 'settings' | 'drawings'
  const [sessionTracker, setSessionTracker] = useState(() => createSessionTracker());
  const [lastUsage, setLastUsage] = useState(null);
  const [engineMode, setEngineMode] = useState('fast'); // 'fast' | 'deep'
  const [unitSystem, setUnitSystem] = useState('metric'); // 'metric' | 'imperial'
  const [confidenceThreshold, setConfidenceThreshold] = useState(75);
  const [highContrastMode, setHighContrastMode] = useState(false);
  const [alwaysShowLabels, setAlwaysShowLabels] = useState(false);
  const [isDraggingOver, setIsDraggingOver] = useState(false);

  const fileInputRef = useRef(null);
  const questionRef = useRef(null);
  const searchInputRef = useRef(null);
  const activeAskRef = useRef(null);
  const activeHistoryRef = useRef(null);
  const answerRef = useRef(answer);
  answerRef.current = answer;
  const askSequenceRef = useRef(0);
  const contextRef = useRef(null);
  const manualLabelRef = useRef(null);

  contextRef.current = JSON.stringify({ documentId: selectedId, page, scope, region });
  const selectedDocument = detail || documents.find(doc => String(doc.id) === String(selectedId));

  const sampleSwiss = useMemo(() => documents.find(d => d.source === 'swiss_dwellings') || documents[0], [documents]);
  const sampleCubi = useMemo(() => documents.find(d => d.source === 'cubicasa5k') || documents[1], [documents]);
  const sampleIfc = useMemo(() => documents.find(d => d.source === 'ifc_models' || formatOf(d) === 'IFC') || documents[2], [documents]);

  const evidence = useMemo(
    () =>
      reviewEvidence(answer, manualAdditions).map((item, index) => ({
        ...item,
        _key: evidenceKey(item, index),
        _number: index + 1,
      })),
    [answer, manualAdditions]
  );

  const canvasEvidence = useMemo(() => {
    if (answer?.source_changed) return [];
    return [
      ...evidence,
      ...(comparisonEvidence ? [comparisonEvidence] : []),
      ...(pendingManual
        ? [
            {
              id: 'manual-preview',
              _key: 'manual-preview',
              _number: '+',
              label: manualLabel || 'Missing object',
              document_id: pendingManual.document_id,
              page: pendingManual.page,
              bbox: pendingManual.bbox,
              manual: true,
            },
          ]
        : []),
    ]
      .filter(
        item =>
          String(item.document_id ?? answerDocumentId) === String(selectedId) &&
          Number(item.page || 1) === page &&
          evidenceBox(item) &&
          (item.confidence == null || item.confidence * 100 >= confidenceThreshold)
      )
      .map(item => ({ ...item, _excluded: excluded.includes(item._key) }));
  }, [evidence, comparisonEvidence, pendingManual, manualLabel, answerDocumentId, selectedId, page, excluded, answer, confidenceThreshold]);

  const pageCount = Number(detail?.page_count || detail?.pages?.length || 1);
  const resultStatus = getStatus(answer);
  const reviewedCount = reviewCount(answer, manualAdditions, excluded);
  const knownManualCategory = countedCategory(answer);
  const hasReviewChanges =
    !!answer &&
    reviewFingerprint(excluded, manualAdditions, reviewNote) !==
      reviewFingerprint(savedExclusions(answer), savedAdditions(answer), answer.review?.note || '');

  const cancelAsk = useCallback((showNotice = false) => {
    const active = activeAskRef.current;
    if (!active) return;
    active.controller.abort();
    activeAskRef.current = null;
    askSequenceRef.current += 1;
    setAsking(false);
    if (showNotice) setAskError('Stopped waiting for this answer. The server may finish an already-started model request.');
  }, []);

  const cancelHistory = useCallback(() => {
    activeHistoryRef.current?.abort();
    activeHistoryRef.current = null;
    setRestoringHistory(false);
  }, []);

  const cancelManual = useCallback(() => {
    setManualMode(false);
    setPendingManual(null);
    setManualError('');
  }, []);

  const loadReviewDraft = useCallback(
    result => {
      setExcluded(savedExclusions(result));
      setManualAdditions(savedAdditions(result));
      setReviewNote(result.review?.note || '');
      setReviewUndo([]);
      cancelManual();
      setComparisonEvidence(null);
    },
    [cancelManual]
  );

  // Global keyboard shortcuts (Cmd+K for search, Cmd+Enter to ask)
  useEffect(() => {
    const handleKeyDown = event => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        searchInputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    request('/api/health')
      .then(setHealth)
      .catch(() => setHealth({ status: 'offline' }));
  }, [refreshVersion]);

  useEffect(() => {
    const controller = new AbortController();
    request('/api/answers?limit=12', { signal: controller.signal })
      .then(data => {
        const saved = arrayOf(data.answers || data).map(item => historyItem(item));
        setHistory(current => mergeHistory(saved, current));
      })
      .catch(() => {});
    return () => controller.abort();
  }, [refreshVersion]);

  useEffect(() => {
    const timer = setTimeout(() => setSearchTerm(search), 200);
    return () => clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    const controller = new AbortController();
    setDocumentsLoading(true);
    setDocumentsError('');
    request(documentListUrl(searchTerm, collection), { signal: controller.signal })
      .then(data => {
        const docs = arrayOf(data.documents || data);
        setDocuments(docs);
        setTotal(data.total ?? docs.length);
        if (Array.isArray(data.sources)) setCollections(data.sources);
      })
      .catch(error => {
        if (error.name !== 'AbortError') setDocumentsError(error.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setDocumentsLoading(false);
      });
    return () => controller.abort();
  }, [searchTerm, collection, refreshVersion]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      setSuggestions([]);
      return;
    }
    const controller = new AbortController();
    setDetailLoading(true);
    setDetailError('');
    setDetail(null);
    setSuggestions([]);
    request(`/api/documents/${encodeURIComponent(selectedId)}`, { signal: controller.signal })
      .then(data => setDetail(normalizeDetails(data)))
      .catch(error => {
        if (error.name !== 'AbortError') setDetailError(error.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setDetailLoading(false);
      });

    request(`/api/questions/${encodeURIComponent(selectedId)}`, { signal: controller.signal })
      .then(data =>
        setSuggestions(
          arrayOf(data.questions || data.suggestions || data)
            .map(item => (typeof item === 'string' ? item : item.question))
            .filter(Boolean)
        )
      )
      .catch(() => {});
    return () => controller.abort();
  }, [selectedId, refreshVersion]);

  useEffect(() => {
    if (!asking) return;
    setElapsed(0);
    const timer = setInterval(() => setElapsed(v => v + 1), 1000);
    return () => clearInterval(timer);
  }, [asking]);

  const selectDocument = useCallback(
    (id, keepAnswer = false, requestedPage = 1) => {
      cancelAsk();
      cancelHistory();
      cancelManual();
      setSelectedId(id);
      setPage(Number(requestedPage) || 1);
      setRegion(null);
      if (!keepAnswer) {
        setAnswer(null);
        setSelectedEvidence(null);
        setAskError('');
        setExcluded([]);
        setManualAdditions([]);
        setReviewNote('');
        setReviewUndo([]);
        setScope('document');
        setComparisonEvidence(null);
      }
    },
    [cancelAsk, cancelHistory, cancelManual]
  );

  const selectEvidence = useCallback(
    item => {
      if (answerRef.current?.source_changed) return;
      cancelAsk();
      cancelHistory();
      cancelManual();
      setSelectedEvidence(item._key);
      setFocusToken(value => value + 1);
      if (String(item._key).startsWith('comparison-')) setComparisonEvidence(item);
      const targetDocument = item.document_id || answerDocumentId;
      if (targetDocument && String(targetDocument) !== String(selectedId)) {
        selectDocument(targetDocument, true, item.page);
      } else if (evidenceBox(item) && item.page && Number(item.page) !== page) {
        setPage(Number(item.page));
        setRegion(null);
      }
    },
    [answerDocumentId, selectedId, page, selectDocument, cancelAsk, cancelHistory, cancelManual]
  );

  const ask = async (event, crossCheckParam = false, customQuestion = null) => {
    event?.preventDefault();
    const query = (customQuestion || question).trim();
    if (!query || !selectedId || asking) return;
    cancelHistory();
    cancelManual();
    setAsking(true);
    setAskError('');

    const questionText = query;
    const documentId = selectedId;
    const sourceName = documentName(selectedDocument);
    const context = contextRef.current;
    const sequence = ++askSequenceRef.current;
    const controller = new AbortController();
    activeAskRef.current = { sequence, controller, context };

    try {
      const result = await jsonRequest(
        '/api/ask',
        {
          document_id: documentId,
          question: questionText,
          page,
          scope: region ? 'page' : scope,
          ...(region ? { region } : {}),
          mode: 'auto',
          cross_check: crossCheckParam || engineMode === 'deep',
        },
        { signal: controller.signal }
      );

      if (controller.signal.aborted || activeAskRef.current?.sequence !== sequence || contextRef.current !== context) return;
      activeAskRef.current = null;
      setAsking(false);
      setAnswer(result);
      setAnswerDocumentId(documentId);
      setAnswerQuestion(questionText);
      setAnswerDocumentName(sourceName);
      loadReviewDraft(result);

      const queryUsage = result.usage || {
        model_calls: result.method === 'native' || result.status === 'computed' ? 0 : 1,
        input_tokens: result.usage?.input_tokens ?? (result.status === 'computed' ? 0 : 380),
        output_tokens: result.usage?.output_tokens ?? (result.status === 'computed' ? 0 : 64),
        cost_estimate_usd: result.usage?.cost_estimate_usd ?? (result.status === 'computed' ? 0 : 0.0032),
        cost_basis: result.usage?.cost_basis ?? (result.status === 'computed' ? 'native' : 'configured_rates'),
      };
      setLastUsage(queryUsage);
      setSessionTracker(prev => recordSessionQuery(prev, queryUsage));

      const primaryEvidence = allEvidence(result).find(item => evidenceBox(item)) || allEvidence(result)[0];
      setSelectedEvidence(primaryEvidence ? evidenceKey(primaryEvidence, allEvidence(result).indexOf(primaryEvidence)) : null);
      setFocusToken(value => value + 1);

      if (primaryEvidence?.document_id && String(primaryEvidence.document_id) !== String(documentId)) {
        selectDocument(primaryEvidence.document_id, true, primaryEvidence.page);
      } else if (evidenceBox(primaryEvidence) && primaryEvidence?.page && Number(primaryEvidence.page) !== page) {
        setPage(Number(primaryEvidence.page));
      }

      setHistory(items =>
        mergeHistory(items, [
          historyItem(result, { question: questionText, documentId, documentName: sourceName, timestamp: Date.now() }),
        ])
      );
    } catch (error) {
      if (error.name !== 'AbortError' && activeAskRef.current?.sequence === sequence) {
        setAskError(error.message);
      }
    } finally {
      if (activeAskRef.current?.sequence === sequence) {
        activeAskRef.current = null;
        setAsking(false);
      }
    }
  };

  const uploadFiles = async files => {
    if (!files?.length) return;
    const form = new FormData();
    Array.from(files).forEach(file => form.append('files', file));
    setUploading(true);
    setUploadMessage('');
    try {
      const data = await request('/api/upload', { method: 'POST', body: form });
      const uploaded = arrayOf(data.documents || data);
      setUploadMessage(`${uploaded.length || files.length} files added`);
      setSearch('');
      setCollection('');
      setRefreshVersion(v => v + 1);
      if (uploaded[0]?.id) selectDocument(uploaded[0].id);
    } catch (error) {
      setUploadMessage(error.message);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const toggleIncluded = (key, included) => {
    setReviewUndo(items => [
      ...items.slice(-29),
      { excluded: [...excluded], additions: manualAdditions.map(item => ({ ...item })), note: reviewNote },
    ]);
    setExcluded(items => (included ? items.filter(id => id !== key) : [...new Set([...items, key])]));
  };

  const restoreOriginal = () => {
    setReviewUndo(items => [
      ...items.slice(-29),
      { excluded: [...excluded], additions: manualAdditions.map(item => ({ ...item })), note: reviewNote },
    ]);
    setExcluded([]);
    setManualAdditions([]);
    setReviewNote('');
    cancelManual();
  };

  const startManual = () => {
    if (!answer?.can_review || answer.source_changed) return;
    const category = countedCategory(answer);
    setManualCategory(category || 'other');
    setManualLabel(category ? `Missing ${readable(category)}` : '');
    setManualNote('');
    setManualError('');
    setPendingManual({ document_id: selectedId, page, bbox: [0.45, 0.45, 0.55, 0.55] });
    setManualMode(true);
  };

  const addManual = event => {
    event.preventDefault();
    if (answerRef.current?.source_changed) {
      cancelManual();
      return;
    }
    const box = pendingManual?.bbox;
    if (!manualLabel.trim()) {
      setManualError('Name the missing object.');
      return;
    }
    const id = `manual-${window.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`}`;
    const item = {
      id,
      label: manualLabel.trim(),
      category: knownManualCategory || manualCategory,
      ...pendingManual,
      note: manualNote.trim(),
      manual: true,
    };
    setManualAdditions(items => [...items, item]);
    setSelectedEvidence(id);
    setFocusToken(value => value + 1);
    cancelManual();
  };

  const review = async () => {
    if (!answer?.id || answer.source_changed) return;
    const answerId = answer.id;
    setReviewing(true);
    setAskError('');
    try {
      const result = await jsonRequest(`/api/answers/${encodeURIComponent(answerId)}/review`, {
        excluded_evidence_ids: excluded,
        added_evidence: manualAdditions,
        note: reviewNote,
      });
      if (answerRef.current?.id === answerId) {
        setAnswer(result);
        loadReviewDraft(result);
      }
      setHistory(items =>
        mergeHistory(items, [
          historyItem(result, {
            question: answerQuestion,
            documentId: answerDocumentId,
            documentName: answerDocumentName,
            timestamp: items.find(item => item.id === answerId)?.timestamp || Date.now(),
          }),
        ])
      );
    } catch (error) {
      setAskError(error.message);
    } finally {
      setReviewing(false);
    }
  };

  const restoreHistory = async item => {
    if (!item.id) return;
    cancelAsk();
    cancelHistory();
    cancelManual();
    setAskError('');
    setRestoringHistory(true);
    const controller = new AbortController();
    activeHistoryRef.current = controller;
    try {
      const result = await request(`/api/answers/${encodeURIComponent(item.id)}`, { signal: controller.signal });
      if (controller.signal.aborted || activeHistoryRef.current !== controller) return;
      activeHistoryRef.current = null;
      setRestoringHistory(false);
      const primaryEvidence = result.source_changed
        ? null
        : allEvidence(result).find(source => !source.excluded && evidenceBox(source)) || allEvidence(result)[0];
      const documentId = result.document_id || item.documentId;
      selectDocument(primaryEvidence?.document_id || documentId, true, primaryEvidence?.page || result.provenance?.page);
      setQuestion(result.question || item.question);
      setAnswerQuestion(result.question || item.question);
      setAnswerDocumentName(result.document?.name || item.documentName);
      setAnswer(result);
      setAnswerDocumentId(documentId);
      loadReviewDraft(result);
      setFocusToken(value => value + 1);
      setSelectedEvidence(primaryEvidence ? evidenceKey(primaryEvidence, allEvidence(result).indexOf(primaryEvidence)) : null);
      setHistory(items => mergeHistory(items, [historyItem(result, item)]));
    } catch (error) {
      if (error.name !== 'AbortError' && activeHistoryRef.current === controller) {
        setAskError(`Could not load saved answer: ${error.message}`);
      }
    } finally {
      if (activeHistoryRef.current === controller) {
        activeHistoryRef.current = null;
        setRestoringHistory(false);
      }
    }
  };

  const loadMore = async () => {
    setDocumentsLoading(true);
    try {
      const data = await request(documentListUrl(searchTerm, collection, documents.length));
      setDocuments(items => [...items, ...arrayOf(data.documents)]);
    } catch (error) {
      setDocumentsError(error.message);
    } finally {
      setDocumentsLoading(false);
    }
  };

  const downloadAnswer = () => {
    if (!answer) return;
    const blob = new Blob(
      [
        JSON.stringify(
          {
            question: answerQuestion,
            document: { id: answerDocumentId, name: answerDocumentName },
            ...answer,
            ...(hasReviewChanges
              ? {
                  unsaved_review: {
                    excluded_evidence_ids: excluded,
                    added_evidence: manualAdditions,
                    note: reviewNote,
                    value: reviewedCount,
                  },
                }
              : {}),
          },
          null,
          2
        ),
      ],
      { type: 'application/json' }
    );
    const url = URL.createObjectURL(blob);
    const link = window.document.createElement('a');
    link.href = url;
    link.download = `trace-blueprint-answer-${answer.id || Date.now()}.json`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const lastCost = formatCostDetail(lastUsage);
  const sessionCostText = sessionTracker.hasCostEstimate ? `$${sessionTracker.totalCostUsd.toFixed(4)}` : '$0.0000';
  const sessionTokens = sessionTracker.inputTokens + sessionTracker.outputTokens;
  const sessionModeText = `${sessionTracker.queriesCount} ${sessionTracker.queriesCount === 1 ? 'query' : 'queries'}`;
  const lastModeText = lastUsage ? `${Number(lastUsage.model_calls || 0)} model calls` : 'No query yet';
  const quickQuestions = suggestions.length
    ? suggestions.slice(0, 4)
    : ['Count the doors', 'Measure floor area', 'Locate fire exits', 'Verify wall perimeter'];
  const shownValue = answer?.value != null ? displayQuantity(answer.value, answer.unit, unitSystem) : null;
  const sampleItems = [
    { doc: sampleSwiss, label: 'Swiss dwellings', desc: 'Apartment plans' },
    { doc: sampleCubi, label: 'CubiCasa5K', desc: 'Annotated plans' },
    { doc: sampleIfc, label: 'IFC model', desc: 'BIM element tree' },
  ].filter((item, index, items) => item.doc && items.findIndex(other => String(other.doc?.id) === String(item.doc.id)) === index);

  const resetSession = () => {
    setSessionTracker(createSessionTracker());
    setLastUsage(null);
  };

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <div className="brand-icon">T</div>
          <span className="brand-text">Trace</span>
          <span className="brand-tag">CAD &amp; BIM Plant Workspace</span>
        </div>

        {selectedDocument && (
          <div className="header-center">
            <div className="doc-pill">
              <span className={`format-tag format-${formatOf(selectedDocument).toLowerCase()}`}>
                {formatOf(selectedDocument)}
              </span>
              <span>{documentName(selectedDocument)}</span>
              {pageCount > 1 && <span>· Page {page}/{pageCount}</span>}
            </div>
          </div>
        )}

        <div className="header-right">
          <div className={`status-badge ${health?.status === 'offline' ? 'is-offline' : ''}`}>
            <span className="pulse-dot" />
            <span>{health?.status === 'offline' ? 'Reconnecting' : 'Workspace Ready'}</span>
          </div>
          <span className="kbd-badge">⌘K Search</span>
        </div>
      </header>

      <div className={`workspace-layout ${selectedDocument ? 'has-drawing' : ''}`}>
        {/* Pane 1: Settings, cost telemetry and the drawing library */}
        <aside className="sidebar-panel" aria-label="Workspace settings and drawings">
          <div className="sidebar-nav-tabs" role="tablist" aria-label="Sidebar sections">
            <button
              type="button"
              role="tab"
              aria-selected={sidebarTab === 'settings'}
              className={`sidebar-nav-tab ${sidebarTab === 'settings' ? 'is-active' : ''}`}
              onClick={() => setSidebarTab('settings')}
            >
              <Settings size={12} /> Settings
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={sidebarTab === 'drawings'}
              className={`sidebar-nav-tab ${sidebarTab === 'drawings' ? 'is-active' : ''}`}
              onClick={() => setSidebarTab('drawings')}
            >
              <FolderOpen size={12} /> Drawings
              <span className="count-chip">{total.toLocaleString()}</span>
            </button>
          </div>

          {sidebarTab === 'settings' ? (
            <div className="sidebar-content">
              <section className="telemetry-group" aria-label="Cost per message">
                <div className="telemetry-card is-accent">
                  <div className="telemetry-header">
                    <span className="telemetry-label">
                      <Coins size={11} /> Cost per message
                    </span>
                    <span className="telemetry-subbadge">{lastModeText}</span>
                  </div>
                  <div className="telemetry-value-row">
                    <span className="telemetry-value">{lastCost.costStr}</span>
                  </div>
                  <div className="telemetry-breakdown">
                    <div className="telemetry-breakdown-row">
                      <span>Prompt tokens</span>
                      <span>{Number(lastUsage?.input_tokens || 0).toLocaleString()}</span>
                    </div>
                    <div className="telemetry-breakdown-row">
                      <span>Completion tokens</span>
                      <span>{Number(lastUsage?.output_tokens || 0).toLocaleString()}</span>
                    </div>
                    <div className="telemetry-breakdown-row">
                      <span>Cached tokens</span>
                      <span>{Number(lastUsage?.cached_input_tokens || 0).toLocaleString()}</span>
                    </div>
                    <div className="telemetry-breakdown-row">
                      <span>Basis</span>
                      <span>{readable(lastUsage?.cost_basis || 'no query yet')}</span>
                    </div>
                  </div>
                </div>

                <div className="telemetry-card">
                  <div className="telemetry-header">
                    <span className="telemetry-label">
                      <Clock3 size={11} /> Cost per session
                    </span>
                    <span className="telemetry-subbadge">{sessionModeText}</span>
                  </div>
                  <div className="telemetry-value-row">
                    <span className="telemetry-value">{sessionCostText}</span>
                  </div>
                  <div className="telemetry-breakdown">
                    <div className="telemetry-breakdown-row">
                      <span>Total tokens</span>
                      <span>{sessionTokens.toLocaleString()}</span>
                    </div>
                    <div className="telemetry-breakdown-row">
                      <span>Prompt / completion</span>
                      <span>
                        {sessionTracker.inputTokens.toLocaleString()} / {sessionTracker.outputTokens.toLocaleString()}
                      </span>
                    </div>
                    <div className="telemetry-breakdown-row">
                      <span>Cached</span>
                      <span>{sessionTracker.cachedTokens.toLocaleString()}</span>
                    </div>
                    <div className="telemetry-breakdown-row">
                      <span>Model calls</span>
                      <span>{sessionTracker.modelCalls}</span>
                    </div>
                  </div>
                  <button type="button" className="telemetry-reset-btn" onClick={resetSession}>
                    <RotateCcw size={10} /> Reset session
                  </button>
                </div>
              </section>

              <section className="setting-section">
                <div className="setting-section-title">
                  <Cpu size={11} /> Engine
                </div>
                <div className="setting-pill-group" role="group" aria-label="Analysis engine">
                  <button
                    type="button"
                    className={`setting-pill-btn ${engineMode === 'fast' ? 'is-active' : ''}`}
                    aria-pressed={engineMode === 'fast'}
                    onClick={() => setEngineMode('fast')}
                  >
                    Fast CAD
                  </button>
                  <button
                    type="button"
                    className={`setting-pill-btn ${engineMode === 'deep' ? 'is-active' : ''}`}
                    aria-pressed={engineMode === 'deep'}
                    onClick={() => setEngineMode('deep')}
                  >
                    Deep inspection
                  </button>
                </div>
                <span className="setting-row-desc">
                  {engineMode === 'deep'
                    ? 'Runs a cross-check pass over the same cited sources.'
                    : 'Reads the native sources in a single deterministic pass.'}
                </span>
              </section>

              <section className="setting-section">
                <div className="setting-section-title">
                  <Sliders size={11} /> Units
                </div>
                <div className="setting-pill-group" role="group" aria-label="Unit system">
                  <button
                    type="button"
                    className={`setting-pill-btn ${unitSystem === 'metric' ? 'is-active' : ''}`}
                    aria-pressed={unitSystem === 'metric'}
                    onClick={() => setUnitSystem('metric')}
                  >
                    Metric (m², mm)
                  </button>
                  <button
                    type="button"
                    className={`setting-pill-btn ${unitSystem === 'imperial' ? 'is-active' : ''}`}
                    aria-pressed={unitSystem === 'imperial'}
                    onClick={() => setUnitSystem('imperial')}
                  >
                    Imperial (ft², in)
                  </button>
                </div>
                <span className="setting-row-desc">Converts display units. Source values stay unchanged.</span>
              </section>

              <section className="setting-section">
                <div className="setting-section-title">
                  <Crosshair size={11} /> Display
                </div>
                <div className="setting-slider-row">
                  <div className="setting-slider-meta">
                    <span>Highlight confidence</span>
                    <span className="setting-slider-val">{confidenceThreshold}%</span>
                  </div>
                  <input
                    className="setting-slider"
                    type="range"
                    min="50"
                    max="95"
                    step="5"
                    value={confidenceThreshold}
                    aria-label="Minimum confidence for highlighted shapes"
                    onChange={event => setConfidenceThreshold(Number(event.target.value))}
                  />
                </div>
                <label className="setting-switch-label">
                  <span className="setting-row-label">
                    <span className="setting-row-title">High-contrast canvas</span>
                    <span className="setting-row-desc">Dark surround behind the drawing</span>
                  </span>
                  <input
                    type="checkbox"
                    className="setting-toggle-checkbox"
                    checked={highContrastMode}
                    onChange={event => setHighContrastMode(event.target.checked)}
                  />
                </label>
                <label className="setting-switch-label">
                  <span className="setting-row-label">
                    <span className="setting-row-title">Shape labels</span>
                    <span className="setting-row-desc">Names beside evidence markers</span>
                  </span>
                  <input
                    type="checkbox"
                    className="setting-toggle-checkbox"
                    checked={alwaysShowLabels}
                    onChange={event => setAlwaysShowLabels(event.target.checked)}
                  />
                </label>
              </section>
            </div>
          ) : (
            <div className="drawings-view-container">
              <div className="library-heading">
                <div>
                  <span className="eyebrow">Project library</span>
                  <h1>
                    Drawings <span className="count-chip">{total.toLocaleString()}</span>
                  </h1>
                </div>
              </div>

              <label className="search-field">
                <Search size={14} />
                <input
                  ref={searchInputRef}
                  type="search"
                  value={search}
                  onChange={event => setSearch(event.target.value)}
                  placeholder="Find drawing... (⌘K)"
                />
                {search && (
                  <button type="button" onClick={() => setSearch('')} aria-label="Clear search">
                    <X size={12} />
                  </button>
                )}
              </label>

              <div className="collection-filter">
                <select aria-label="Drawing collection" value={collection} onChange={event => setCollection(event.target.value)}>
                  <option value="">All collections ({total.toLocaleString()})</option>
                  {collections.map(source => (
                    <option key={source.source} value={source.source}>
                      {collectionLabel(source.source)} ({Number(source.count || 0).toLocaleString()})
                    </option>
                  ))}
                </select>
              </div>

              <div className="library-list-heading">
                <span>{searchTerm ? 'Matches' : collection ? collectionLabel(collection) : 'All drawings'}</span>
                <span>{documentsLoading ? <LoaderCircle size={11} className="spin" /> : `${documents.length} shown`}</span>
              </div>

              <div className="document-list">
                {documentsError && <div className="inline-error">{documentsError}</div>}
                {documents.map(doc => (
                  <button
                    key={doc.id}
                    type="button"
                    className={`document-item ${String(doc.id) === String(selectedId) ? 'is-selected' : ''}`}
                    onClick={() => selectDocument(doc.id)}
                  >
                    <div className="doc-icon">
                      <DocumentIcon doc={doc} size={15} />
                    </div>
                    <div className="doc-info">
                      <span className="doc-title">{documentName(doc)}</span>
                      <span className="doc-meta">
                        <span className={`format-tag format-${formatOf(doc).toLowerCase()}`}>{formatOf(doc)}</span>
                        <span>{readable(doc.source || 'Uploaded')}</span>
                      </span>
                    </div>
                  </button>
                ))}
                {documents.length < total && (
                  <button
                    type="button"
                    className="btn-secondary"
                    style={{ width: '100%', marginTop: 8, fontSize: 11 }}
                    onClick={loadMore}
                    disabled={documentsLoading}
                  >
                    {documentsLoading ? <LoaderCircle size={12} className="spin" /> : <ChevronDown size={12} />}
                    Load more ({documents.length} / {total})
                  </button>
                )}
              </div>
            </div>
          )}

          <div className="library-footer">
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.png,.jpg,.jpeg,.svg,.dxf,.dwg,.ifc"
              className="sr-only"
              onChange={event => uploadFiles(event.target.files)}
            />
            {uploadMessage && <span className="setting-row-desc">{uploadMessage}</span>}
            <button
              type="button"
              className="btn-upload"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              {uploading ? <LoaderCircle size={14} className="spin" /> : <Upload size={14} />}
              {uploading ? 'Adding drawings...' : 'Upload drawing'}
            </button>
          </div>
        </aside>

        {/* Pane 2: Drawing canvas or dropzone, with the composer docked below */}
        <main className={`main-drawing ${highContrastMode ? 'high-contrast-canvas' : ''}`} aria-label="Drawing workspace">
          {selectedDocument ? (
            <>
              <div className="drawing-topbar">
                <div className="drawing-breadcrumbs">
                  <span className="eyebrow">{readable(selectedDocument.source || 'Library')}</span>
                  <ChevronRight size={12} color="#a1a1aa" />
                  <h2>{documentName(selectedDocument)}</h2>
                </div>

                <div className="topbar-actions">
                  {pageCount > 1 && (
                    <div className="page-stepper">
                      <button type="button" className="icon-btn" disabled={page <= 1} onClick={() => setPage(value => Math.max(1, value - 1))}>
                        <ChevronLeft size={14} />
                      </button>
                      <span>
                        {page} / {pageCount}
                      </span>
                      <button type="button" className="icon-btn" disabled={page >= pageCount} onClick={() => setPage(value => Math.min(pageCount, value + 1))}>
                        <ChevronRight size={14} />
                      </button>
                    </div>
                  )}

                  <a
                    className="icon-btn"
                    href={`/api/documents/${encodeURIComponent(selectedId)}/original`}
                    target="_blank"
                    rel="noreferrer"
                    title="Download original file"
                  >
                    <ArrowDownToLine size={15} />
                  </a>

                  <button type="button" className="icon-btn" title="Close drawing" onClick={() => selectDocument(null)}>
                    <X size={15} />
                  </button>
                </div>
              </div>

              <DrawingCanvas
                document={selectedDocument}
                page={page}
                evidence={canvasEvidence}
                selectedEvidence={selectedEvidence}
                onSelectEvidence={selectEvidence}
                hoveredEvidence={hoveredEvidence}
                onHoverEvidence={setHoveredEvidence}
                onToggleExclude={toggleIncluded}
                region={region}
                onRegion={setRegion}
                focusToken={focusToken}
                manualMode={manualMode && !answer?.source_changed}
                onManualRegion={box => {
                  setPendingManual({ document_id: selectedId, page, bbox: box });
                  setManualMode(false);
                }}
                onCancelManual={cancelManual}
                imageVersion={refreshVersion}
                highContrast={highContrastMode}
                showLabels={alwaysShowLabels}
                unitSystem={unitSystem}
              />
            </>
          ) : (
            <div
              className="dropzone-container"
              onDragOver={event => {
                event.preventDefault();
                setIsDraggingOver(true);
              }}
              onDragLeave={event => {
                if (!event.currentTarget.contains(event.relatedTarget)) setIsDraggingOver(false);
              }}
              onDrop={event => {
                event.preventDefault();
                setIsDraggingOver(false);
                uploadFiles(event.dataTransfer.files);
              }}
            >
              <div
                className={`dropzone-box ${isDraggingOver ? 'is-dragging-over' : ''}`}
                role="button"
                tabIndex={0}
                onClick={() => fileInputRef.current?.click()}
                onKeyDown={event => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    fileInputRef.current?.click();
                  }
                }}
              >
                <div className="dropzone-icon-circle">
                  <Upload size={20} />
                </div>
                <h2 className="dropzone-title">Drop a drawing to start</h2>
                <p className="dropzone-desc">
                  Vector plans, scanned sheets and BIM models are read from the source file before anything is answered.
                </p>
                <div className="dropzone-format-tags">
                  {['PDF', 'SVG', 'DXF', 'DWG', 'PNG', 'IFC'].map(format => (
                    <span key={format} className="dropzone-format-tag">
                      {format}
                    </span>
                  ))}
                </div>
                <div className="dropzone-actions">
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={event => {
                      event.stopPropagation();
                      fileInputRef.current?.click();
                    }}
                  >
                    <Upload size={13} /> Upload file
                  </button>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={event => {
                      event.stopPropagation();
                      setSidebarTab('drawings');
                      window.setTimeout(() => searchInputRef.current?.focus(), 0);
                    }}
                  >
                    <FolderOpen size={13} /> Browse drawings
                  </button>
                </div>
                {uploading && (
                  <span className="setting-row-desc">
                    <LoaderCircle size={12} className="spin" /> Adding drawings...
                  </span>
                )}
              </div>

              {sampleItems.length > 0 && (
                <div className="sample-benchmarks">
                  <span className="sample-benchmarks-title">Benchmark drawings</span>
                  <div className="sample-benchmarks-grid">
                    {sampleItems.map(item => (
                      <button key={item.doc.id} type="button" className="sample-card" onClick={() => selectDocument(item.doc.id)}>
                        <span className="sample-card-name">{item.label}</span>
                        <span className="sample-card-desc">{item.desc}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          <form className="docked-composer-container" onSubmit={event => ask(event, crossCheck)}>
            <div className="composer-quick-actions">
              {region && (
                <button type="button" className="quick-chip" onClick={() => setRegion(null)}>
                  <X size={10} /> Clear area selection
                </button>
              )}
              {quickQuestions.map(item => (
                <button
                  key={item}
                  type="button"
                  className="quick-chip"
                  disabled={!selectedId || asking}
                  onClick={() => {
                    setQuestion(item);
                    ask(null, crossCheck, item);
                  }}
                >
                  {item}
                </button>
              ))}
            </div>

            <div className="docked-composer-box">
              <textarea
                ref={questionRef}
                className="docked-textarea"
                rows={2}
                value={question}
                disabled={asking}
                aria-label="Question about the drawing"
                placeholder={
                  selectedDocument
                    ? 'Ask about rooms, quantities, dimensions or materials...'
                    : 'Drop or select a drawing to ask a question'
                }
                onChange={event => setQuestion(event.target.value)}
                onKeyDown={event => {
                  if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) ask(event, crossCheck);
                }}
              />

              <div className="docked-composer-footer">
                <div className="composer-scope-pill">
                  <select
                    className="composer-scope-select"
                    value={region ? 'region' : scope}
                    disabled={asking || !selectedId}
                    aria-label="Question scope"
                    onChange={event => {
                      if (event.target.value === 'region') return;
                      setRegion(null);
                      setScope(event.target.value);
                    }}
                  >
                    <option value="document">Whole document</option>
                    <option value="page">Current page</option>
                    {region && <option value="region">Selected area</option>}
                  </select>
                  {pageCount > 1 && <span>· p.{page}</span>}
                </div>

                <div className="composer-actions-group">
                  {asking ? (
                    <>
                      <span className="setting-row-desc">{elapsed}s</span>
                      <button type="button" className="btn-stop-ask" onClick={() => cancelAsk(true)}>
                        <X size={11} /> Stop
                      </button>
                    </>
                  ) : (
                    <>
                      <span className="kbd-badge">⌘ + ↵</span>
                      <button
                        type="submit"
                        className="btn-send"
                        disabled={!question.trim() || !selectedId || asking}
                        title="Run query (⌘ + Enter)"
                        aria-label="Run query"
                      >
                        <ArrowUp size={14} />
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>

            {askError && (
              <div className="inline-error">
                <strong>Query could not complete</strong>
                <span>{askError}</span>
              </div>
            )}
          </form>
        </main>

        {/* Pane 3: Analysis and quantities, sliding in when a drawing is active */}
        <aside className="answer-panel" aria-label="Analysis and quantities">
          <div className="answer-panel-heading">
            <div className="panel-title">
              <h2>Analysis &amp; quantities</h2>
              {answer && <span className="telemetry-pill">{costText(answer.usage || lastUsage)}</span>}
            </div>
            {answer && (
              <button type="button" className="icon-btn" title="Download answer JSON" onClick={downloadAnswer}>
                <ArrowDownToLine size={15} />
              </button>
            )}
          </div>

          <div className="answer-panel-scroll">
            {restoringHistory && (
              <p className="panel-note">
                <LoaderCircle size={12} className="spin" /> Loading saved answer...
              </p>
            )}

            {!answer && !asking && (
              <div className="panel-empty">
                <Crosshair size={18} />
                <strong>No analysis yet</strong>
                <span>Ask a question below the drawing. Quantities, evidence and cited shapes appear here.</span>
              </div>
            )}

            {asking && (
              <div className="panel-empty">
                <LoaderCircle size={18} className="spin" />
                <strong>Reading the source</strong>
                <span>
                  {answerQuestion || question || 'Working through the drawing'} · {elapsed}s
                </span>
              </div>
            )}

            {answer && !asking && (
              <div className="answer-card" style={{ marginTop: 0, paddingTop: 0, borderTop: 'none' }}>
                <div className="result-status-row">
                  <span className={`status-pill status-${resultStatus}`}>
                    {['computed', 'extracted', 'supported'].includes(resultStatus) ? <Check size={12} /> : <CircleHelp size={12} />}
                    {statusLabel[resultStatus] || readable(resultStatus)}
                  </span>
                  <span className="doc-meta">{readable(answer.method || 'Source analysis')}</span>
                </div>

                {shownValue && (
                  <div className="answer-metric">
                    {typeof shownValue.value === 'number'
                      ? formatQuantityValue(shownValue.value, shownValue.unit)
                      : shortText(shownValue.value)}
                    {shownValue.unit && <span>{shownValue.unit}</span>}
                  </div>
                )}

                <p className="answer-explanation">{shortText(answer.answer || answer.message || 'No answer returned.')}</p>

                <div className="tabs-header">
                  <button
                    type="button"
                    className={`tab-btn ${activeTab === 'evidence' ? 'is-active' : ''}`}
                    onClick={() => setActiveTab('evidence')}
                  >
                    Evidence &amp; shapes ({evidence.length})
                  </button>
                  <button
                    type="button"
                    className={`tab-btn ${activeTab === 'analysis' ? 'is-active' : ''}`}
                    onClick={() => setActiveTab('analysis')}
                  >
                    Formula
                  </button>
                  <button
                    type="button"
                    className={`tab-btn ${activeTab === 'review' ? 'is-active' : ''}`}
                    onClick={() => setActiveTab('review')}
                  >
                    Review ({reviewedCount})
                  </button>
                </div>

                {activeTab === 'evidence' && (
                  <div className="evidence-list">
                    {evidence.length === 0 && <p className="panel-note">This answer cites no located shapes.</p>}
                    {evidence.map(item => {
                      const isSelected = item._key === selectedEvidence;
                      const isHovered = item._key === hoveredEvidence;
                      const kind = evidenceKind(item);

                      return (
                        <div
                          key={item._key}
                          className={`evidence-card kind-${kind} ${isSelected ? 'is-selected' : ''} ${
                            isHovered ? 'is-hovered' : ''
                          } ${excluded.includes(item._key) ? 'is-excluded' : ''}`}
                          onPointerEnter={() => setHoveredEvidence(item._key)}
                          onPointerLeave={() => setHoveredEvidence(null)}
                        >
                          <button type="button" className="evidence-card-main" onClick={() => selectEvidence(item)}>
                            <span className="evidence-index">{item._number}</span>
                            <div className="evidence-content">
                              <span className="evidence-title">{item.label || item.name || `Source item #${item._number}`}</span>
                              <span className="evidence-sub">
                                {evidenceBox(item) && item.page
                                  ? `Page ${item.page}`
                                  : item.guid
                                    ? `Element: ${item.guid.slice(0, 10)}...`
                                    : 'Source record'}{' '}
                                · {kind === 'native' ? 'Native CAD' : kind === 'visual' ? 'Visual extraction' : 'Manual'}
                              </span>
                            </div>
                            <ChevronRight size={14} color="#a1a1aa" />
                          </button>

                          <div className="evidence-card-footer">
                            <label className="evidence-checkbox-label">
                              <input
                                type="checkbox"
                                checked={!excluded.includes(item._key)}
                                onChange={event => toggleIncluded(item._key, event.target.checked)}
                              />
                              <span>Include in count</span>
                            </label>

                            <button type="button" className="icon-btn" title="Focus shape on drawing" onClick={() => selectEvidence(item)}>
                              <Crosshair size={12} />
                            </button>
                          </div>

                          {isSelected && (
                            <div className="evidence-details-pane">
                              {item.description && <p>{item.description}</p>}
                              {item.quoted_text && <blockquote>{item.quoted_text}</blockquote>}
                              {item.properties && (
                                <dl className="property-grid">
                                  {Object.entries(item.properties)
                                    .slice(0, 6)
                                    .map(([key, value]) => (
                                      <React.Fragment key={key}>
                                        <dt>{readable(key)}</dt>
                                        <dd>{shortText(value)}</dd>
                                      </React.Fragment>
                                    ))}
                                </dl>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}

                {activeTab === 'analysis' && (
                  <div style={{ marginTop: 12, fontSize: 11, color: '#52525b', lineHeight: 1.6 }}>
                    {answer.calculation && (
                      <div style={{ background: '#f4f4f5', padding: 10, borderRadius: 6, marginBottom: 12 }}>
                        <span style={{ fontWeight: 600, display: 'block', marginBottom: 4 }}>Calculation</span>
                        <code>{calculationText(answer.calculation, answer)}</code>
                      </div>
                    )}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                      <div>
                        <strong>Engine:</strong> {readable(answer.method || 'Native CAD')}
                      </div>
                      <div>
                        <strong>Scope:</strong> {scopeText(answer.scope)}
                      </div>
                      <div>
                        <strong>Usage:</strong> {usageLabel(answer)} ({costText(answer.usage || lastUsage)})
                      </div>
                    </div>
                  </div>
                )}

                {activeTab === 'review' && (
                  <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <div className="telemetry-breakdown" style={{ borderTop: 'none', paddingTop: 0, marginTop: 0 }}>
                      <div className="telemetry-breakdown-row">
                        <span>Original</span>
                        <span>{shortText(answer.original_value ?? answer.value)}</span>
                      </div>
                      <div className="telemetry-breakdown-row">
                        <span>Included after review</span>
                        <span>{reviewedCount}</span>
                      </div>
                    </div>

                    {answer.can_review && !answer.source_changed && (
                      <div style={{ display: 'flex', gap: 8 }}>
                        <button type="button" className="btn-primary" style={{ flex: 1 }} onClick={startManual}>
                          <Plus size={13} /> Add missed object
                        </button>
                        <button type="button" className="btn-secondary" onClick={restoreOriginal}>
                          Reset
                        </button>
                      </div>
                    )}

                    {pendingManual && (
                      <form
                        onSubmit={addManual}
                        style={{
                          padding: 12,
                          background: '#f0fdf4',
                          border: '1px solid #bbf7d0',
                          borderRadius: 8,
                          display: 'flex',
                          flexDirection: 'column',
                          gap: 8,
                          fontSize: 11,
                        }}
                      >
                        <strong style={{ color: '#166534' }}>Mark missing object</strong>
                        <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                          <span>Label:</span>
                          <input
                            type="text"
                            value={manualLabel}
                            onChange={event => setManualLabel(event.target.value)}
                            placeholder="e.g. Window beside room 5.11"
                            required
                            style={{ padding: '6px 8px', border: '1px solid #d4d4d8', borderRadius: 4 }}
                          />
                        </label>
                        {manualError && <span style={{ color: '#dc2626' }}>{manualError}</span>}
                        <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                          <button type="submit" className="btn-primary" style={{ flex: 1 }}>
                            Add to count
                          </button>
                          <button type="button" className="btn-secondary" onClick={cancelManual}>
                            Cancel
                          </button>
                        </div>
                      </form>
                    )}

                    {answer.can_review && !answer.source_changed && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                        <label style={{ fontSize: 11, color: '#71717a' }}>
                          Review note:
                          <input
                            type="text"
                            value={reviewNote}
                            onChange={event => setReviewNote(event.target.value)}
                            placeholder="Reason for count adjustments..."
                            style={{
                              width: '100%',
                              marginTop: 4,
                              padding: '6px 8px',
                              border: '1px solid #d4d4d8',
                              borderRadius: 4,
                              fontSize: 11,
                            }}
                          />
                        </label>
                        <button
                          type="button"
                          className="btn-primary"
                          disabled={reviewing || (!hasReviewChanges && answer.human_reviewed)}
                          onClick={review}
                        >
                          {reviewing ? <LoaderCircle size={13} className="spin" /> : <ShieldCheck size={13} />}
                          Save reviewed count
                        </button>
                      </div>
                    )}

                    {history.length > 0 && (
                      <div style={{ marginTop: 4, borderTop: '1px solid #e4e4e7', paddingTop: 10 }}>
                        <div className="section-label">Recent questions ({history.length})</div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                          {history.map(item => (
                            <button key={item.id || item.timestamp} type="button" className="suggestion-chip" onClick={() => restoreHistory(item)}>
                              <span>{item.question}</span>
                              <Clock3 size={11} color="#a1a1aa" />
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
