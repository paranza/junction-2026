import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
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
  Command,
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
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  SquareDashedMousePointer,
  Upload,
  X,
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
  visual: 'AI Vision Analysis',
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
    <div className={`canvas-wrapper ${spotlightMode ? 'spotlight-active' : ''}`}>
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
          <Sparkles size={15} />
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
                    } ${item._excluded ? 'is-excluded' : ''}`}
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
                      {area && <span>Area: {typeof area === 'number' ? `${area.toFixed(1)} m²` : area}</span>}
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
          evidenceBox(item)
      )
      .map(item => ({ ...item, _excluded: excluded.includes(item._key) }));
  }, [evidence, comparisonEvidence, pendingManual, manualLabel, answerDocumentId, selectedId, page, excluded, answer]);

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
        setSelectedId(current => current || docs[0]?.id || null);
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
    if (!selectedId) return;
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
          cross_check: crossCheckParam,
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

  return (
    <div className="app-shell">
      {/* Sleek Vercel Dark Header */}
      <header className="app-header">
        <div className="brand">
          <div className="brand-icon">T</div>
          <span className="brand-text">Trace</span>
          <span className="brand-badge">Blueprint Intelligence</span>
        </div>

        {selectedDocument && (
          <div className="header-center">
            <div className="doc-pill">
              <span className={`format-tag format-${formatOf(selectedDocument).toLowerCase()}`}>
                {formatOf(selectedDocument)}
              </span>
              <span>{documentName(selectedDocument)}</span>
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

      {/* 3-Pane Responsive Layout */}
      <div className="workspace-layout">
        {/* Pane 1: Document Library */}
        <aside className="document-library" aria-label="Drawing library">
          <div className="library-heading">
            <div>
              <span className="eyebrow">Project Library</span>
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
              onChange={e => setSearch(e.target.value)}
              placeholder="Find drawing... (⌘K)"
            />
            {search && (
              <button type="button" onClick={() => setSearch('')}>
                <X size={12} />
              </button>
            )}
          </label>

          <div className="collection-filter">
            <select aria-label="Drawing collection" value={collection} onChange={e => setCollection(e.target.value)}>
              <option value="">All Collections ({total.toLocaleString()})</option>
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
                Load More Drawings ({documents.length} / {total})
              </button>
            )}
          </div>

          <div className="library-footer">
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.png,.jpg,.jpeg,.svg,.dxf,.dwg,.ifc"
              className="sr-only"
              onChange={e => uploadFiles(e.target.files)}
            />
            <button
              type="button"
              className="btn-upload"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              {uploading ? <LoaderCircle size={14} className="spin" /> : <Upload size={14} />}
              {uploading ? 'Adding drawings...' : 'Upload Drawing'}
            </button>
          </div>
        </aside>

        {/* Pane 2: The Drawing & Shape Interactive Plant Viewer */}
        <main className="main-drawing" aria-label="Selected drawing canvas">
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
                      <button
                        type="button"
                        className="icon-btn"
                        disabled={page <= 1}
                        onClick={() => setPage(p => Math.max(1, p - 1))}
                      >
                        <ChevronLeft size={14} />
                      </button>
                      <span>
                        {page} / {pageCount}
                      </span>
                      <button
                        type="button"
                        className="icon-btn"
                        disabled={page >= pageCount}
                        onClick={() => setPage(p => Math.min(pageCount, p + 1))}
                      >
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
              />
            </>
          ) : (
            <div className="canvas-message">
              <Layers3 size={36} color="#94a3b8" />
              <strong>Select a Drawing</strong>
              <span>Pick a construction drawing from the library or upload a file to begin.</span>
            </div>
          )}
        </main>

        {/* Pane 3: Ask Trace & Intelligence Panel */}
        <aside className="answer-panel" aria-label="Ask Trace and inspect answers">
          <div className="answer-panel-heading">
            <div className="panel-title">
              <h2>Ask Trace</h2>
              <span className="ai-pill">CAD + Vision</span>
            </div>
            {answer && (
              <button type="button" className="icon-btn" title="Download Answer JSON" onClick={downloadAnswer}>
                <ArrowDownToLine size={15} />
              </button>
            )}
          </div>

          <div className="answer-panel-scroll">
            {/* Question Box */}
            <form onSubmit={e => ask(e, crossCheck)}>
              <div className={`question-box ${asking ? 'is-busy' : ''}`}>
                <textarea
                  ref={questionRef}
                  className="question-textarea"
                  placeholder="Ask about rooms, quantities, dimensions, or materials..."
                  value={question}
                  onChange={e => setQuestion(e.target.value)}
                  disabled={asking}
                  onKeyDown={e => {
                    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                      ask(e, crossCheck);
                    }
                  }}
                  rows={2}
                />

                <div className="question-box-footer">
                  <span className="scope-indicator">
                    {region ? 'Selected Area' : scope === 'page' ? `Page ${page}` : 'Whole Document'}
                  </span>
                  <button
                    type="submit"
                    className="btn-ask"
                    disabled={!question.trim() || !selectedId || asking}
                    title="Run query (⌘ + Enter)"
                  >
                    {asking ? <LoaderCircle size={15} className="spin" /> : <ArrowUp size={15} />}
                  </button>
                </div>
              </div>

              <div className="query-controls">
                <label>
                  <span>Scope:</span>
                  <select value={scope} onChange={e => setScope(e.target.value)} disabled={!!region || asking}>
                    <option value="document">Whole Document</option>
                    <option value="page">Current Page</option>
                  </select>
                </label>
                <span className="kbd-badge">⌘ + ↵</span>
              </div>
            </form>

            {askError && (
              <div className="inline-error" style={{ marginTop: 12 }}>
                <strong>Query could not complete</strong>
                <span>{askError}</span>
              </div>
            )}

            {/* Prompt Suggestions */}
            {!answer && !asking && suggestions.length > 0 && (
              <div className="suggestions-container">
                <div className="section-label">Suggested Questions</div>
                <div className="suggestion-chips">
                  {suggestions.slice(0, 5).map((item, i) => (
                    <button
                      key={i}
                      type="button"
                      className="suggestion-chip"
                      onClick={() => {
                        setQuestion(item);
                        ask(null, crossCheck, item);
                      }}
                    >
                      <span>{item}</span>
                      <ArrowUp size={12} />
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Answer Display */}
            {answer && !asking && (
              <div className="answer-card">
                <div className="result-status-row">
                  <span className={`status-pill status-${resultStatus}`}>
                    {['computed', 'extracted', 'supported'].includes(resultStatus) ? (
                      <Check size={12} />
                    ) : (
                      <CircleHelp size={12} />
                    )}
                    {statusLabel[resultStatus] || readable(resultStatus)}
                  </span>
                  <span className="doc-meta">{readable(answer.method || 'Source analysis')}</span>
                </div>

                {answer.value != null && (
                  <div className="answer-metric">
                    {shortText(answer.value)}
                    {answer.unit && <span>{answer.unit}</span>}
                  </div>
                )}

                {/* Tab 3: Review & Working Quantity */}
                {activeTab === 'review' && (
                  <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        padding: '8px 12px',
                        background: '#f4f4f5',
                        borderRadius: 6,
                        fontSize: 11,
                      }}
                    >
                      <span>
                        Original: <strong>{answer.original_value ?? answer.value}</strong>
                      </span>
                      <span>
                        Included / Reviewed: <strong style={{ color: '#0070f3' }}>{reviewedCount}</strong>
                      </span>
                    </div>

                    {answer.can_review && !answer.source_changed && (
                      <div style={{ display: 'flex', gap: 8 }}>
                        <button type="button" className="btn-primary" style={{ flex: 1 }} onClick={startManual}>
                          <Plus size={13} /> Add Missed Object
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
                        <strong style={{ color: '#166534' }}>Mark Missing Plant Object</strong>
                        <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                          <span>Label:</span>
                          <input
                            type="text"
                            value={manualLabel}
                            onChange={e => setManualLabel(e.target.value)}
                            placeholder="e.g. Window beside room 5.11"
                            required
                            style={{ padding: '6px 8px', border: '1px solid #d4d4d8', borderRadius: 4 }}
                          />
                        </label>
                        {manualError && <span style={{ color: '#dc2626' }}>{manualError}</span>}
                        <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                          <button type="submit" className="btn-primary" style={{ flex: 1 }}>
                            Add to Count
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
                          Review Note:
                          <input
                            type="text"
                            value={reviewNote}
                            onChange={e => setReviewNote(e.target.value)}
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
                          Save Reviewed Count
                        </button>
                      </div>
                    )}

                    {history.length > 0 && (
                      <div style={{ marginTop: 14, borderTop: '1px solid #e4e4e7', paddingTop: 10 }}>
                        <div className="section-label">Recent Questions ({history.length})</div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                          {history.map(item => (
                            <button
                              key={item.id || item.timestamp}
                              type="button"
                              className="suggestion-chip"
                              onClick={() => restoreHistory(item)}
                            >
                              <span>{item.question}</span>
                              <Clock3 size={11} color="#a1a1aa" />
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                <p className="answer-explanation">
                  {shortText(answer.answer || answer.message || 'No answer returned.')}
                </p>

                {/* Navigation Tabs */}
                <div className="tabs-header">
                  <button
                    type="button"
                    className={`tab-btn ${activeTab === 'evidence' ? 'is-active' : ''}`}
                    onClick={() => setActiveTab('evidence')}
                  >
                    Evidence ({evidence.length})
                  </button>
                  <button
                    type="button"
                    className={`tab-btn ${activeTab === 'analysis' ? 'is-active' : ''}`}
                    onClick={() => setActiveTab('analysis')}
                  >
                    Analysis &amp; Formula
                  </button>
                  <button
                    type="button"
                    className={`tab-btn ${activeTab === 'review' ? 'is-active' : ''}`}
                    onClick={() => setActiveTab('review')}
                  >
                    Review ({reviewedCount})
                  </button>
                </div>

                {/* Tab 1: Interactive Evidence Cards */}
                {activeTab === 'evidence' && (
                  <div className="evidence-list">
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
                          <button
                            type="button"
                            className="evidence-card-main"
                            onClick={() => selectEvidence(item)}
                          >
                            <span className="evidence-index">{item._number}</span>
                            <div className="evidence-content">
                              <span className="evidence-title">
                                {item.label || item.name || `Source Item #${item._number}`}
                              </span>
                              <span className="evidence-sub">
                                {evidenceBox(item) && item.page
                                  ? `Page ${item.page}`
                                  : item.guid
                                  ? `Element: ${item.guid.slice(0, 10)}...`
                                  : 'Source Record'}{' '}
                                · {kind === 'native' ? 'Native CAD' : kind === 'visual' ? 'Vision' : 'Manual'}
                              </span>
                            </div>
                            <ChevronRight size={14} color="#a1a1aa" />
                          </button>

                          <div className="evidence-card-footer">
                            <label className="evidence-checkbox-label">
                              <input
                                type="checkbox"
                                checked={!excluded.includes(item._key)}
                                onChange={e => toggleIncluded(item._key, e.target.checked)}
                              />
                              <span>Include in count</span>
                            </label>

                            <button
                              type="button"
                              className="icon-btn"
                              title="Focus shape on drawing"
                              onClick={() => selectEvidence(item)}
                            >
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
                                    .map(([k, v]) => (
                                      <React.Fragment key={k}>
                                        <dt>{readable(k)}</dt>
                                        <dd>{shortText(v)}</dd>
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

                {/* Tab 3: Review & Working Quantity */}
                {activeTab === 'review' && (
                  <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        padding: '8px 12px',
                        background: '#f4f4f5',
                        borderRadius: 6,
                        fontSize: 11,
                      }}
                    >
                      <span>
                        Original: <strong>{answer.original_value ?? answer.value}</strong>
                      </span>
                      <span>
                        Included / Reviewed: <strong style={{ color: '#0070f3' }}>{reviewedCount}</strong>
                      </span>
                    </div>

                    {answer.can_review && !answer.source_changed && (
                      <div style={{ display: 'flex', gap: 8 }}>
                        <button type="button" className="btn-primary" style={{ flex: 1 }} onClick={startManual}>
                          <Plus size={13} /> Add Missed Object
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
                        <strong style={{ color: '#166534' }}>Mark Missing Plant Object</strong>
                        <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                          <span>Label:</span>
                          <input
                            type="text"
                            value={manualLabel}
                            onChange={e => setManualLabel(e.target.value)}
                            placeholder="e.g. Window beside room 5.11"
                            required
                            style={{ padding: '6px 8px', border: '1px solid #d4d4d8', borderRadius: 4 }}
                          />
                        </label>
                        {manualError && <span style={{ color: '#dc2626' }}>{manualError}</span>}
                        <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                          <button type="submit" className="btn-primary" style={{ flex: 1 }}>
                            Add to Count
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
                          Review Note:
                          <input
                            type="text"
                            value={reviewNote}
                            onChange={e => setReviewNote(e.target.value)}
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
                          Save Reviewed Count
                        </button>
                      </div>
                    )}

                    {history.length > 0 && (
                      <div style={{ marginTop: 14, borderTop: '1px solid #e4e4e7', paddingTop: 10 }}>
                        <div className="section-label">Recent Questions ({history.length})</div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                          {history.map(item => (
                            <button
                              key={item.id || item.timestamp}
                              type="button"
                              className="suggestion-chip"
                              onClick={() => restoreHistory(item)}
                            >
                              <span>{item.question}</span>
                              <Clock3 size={11} color="#a1a1aa" />
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Tab 2: Analysis & Formula */}
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
                      {answer.usage && (
                        <div>
                          <strong>Usage:</strong> {usageLabel(answer)} ({answer.usage.model_calls || 0} calls,{' '}
                          {costText(answer.usage)})
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Tab 3: Review & Working Quantity */}
                {activeTab === 'review' && (
                  <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        padding: '8px 12px',
                        background: '#f4f4f5',
                        borderRadius: 6,
                        fontSize: 11,
                      }}
                    >
                      <span>
                        Original: <strong>{answer.original_value ?? answer.value}</strong>
                      </span>
                      <span>
                        Included / Reviewed: <strong style={{ color: '#0070f3' }}>{reviewedCount}</strong>
                      </span>
                    </div>

                    {answer.can_review && !answer.source_changed && (
                      <div style={{ display: 'flex', gap: 8 }}>
                        <button type="button" className="btn-primary" style={{ flex: 1 }} onClick={startManual}>
                          <Plus size={13} /> Add Missed Object
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
                        <strong style={{ color: '#166534' }}>Mark Missing Plant Object</strong>
                        <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                          <span>Label:</span>
                          <input
                            type="text"
                            value={manualLabel}
                            onChange={e => setManualLabel(e.target.value)}
                            placeholder="e.g. Window beside room 5.11"
                            required
                            style={{ padding: '6px 8px', border: '1px solid #d4d4d8', borderRadius: 4 }}
                          />
                        </label>
                        {manualError && <span style={{ color: '#dc2626' }}>{manualError}</span>}
                        <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                          <button type="submit" className="btn-primary" style={{ flex: 1 }}>
                            Add to Count
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
                          Review Note:
                          <input
                            type="text"
                            value={reviewNote}
                            onChange={e => setReviewNote(e.target.value)}
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
                          Save Reviewed Count
                        </button>
                      </div>
                    )}

                    {history.length > 0 && (
                      <div style={{ marginTop: 14, borderTop: '1px solid #e4e4e7', paddingTop: 10 }}>
                        <div className="section-label">Recent Questions ({history.length})</div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                          {history.map(item => (
                            <button
                              key={item.id || item.timestamp}
                              type="button"
                              className="suggestion-chip"
                              onClick={() => restoreHistory(item)}
                            >
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
