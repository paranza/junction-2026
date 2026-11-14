import React, { useEffect, useMemo, useRef, useState } from 'react';
import './InspectorPanel.css';

// Takeoff, tender estimate and code checks for the open drawing (GET /api/documents/:id/inspection).
// Quantities come from the drawing; unit costs and carbon factors are editable placeholders.

const endpoint = (id, options) => {
  const query = new URLSearchParams(Object.entries(options).filter(([, v]) => v !== '' && v != null));
  return `/api/documents/${encodeURIComponent(id)}/inspection?${query}`;
};
const money = value => value.toLocaleString(undefined, { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 });
const kg = value => `${Math.round(value).toLocaleString()} kg CO₂e`;
const CHECK_NAMES = { daylight: 'Daylight (glazing / floor)', turning_circle: 'Wheelchair turning circle', egress: 'Escape route length' };

function csvCell(value) {
  const text = String(value ?? '');
  return /[",\n;]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

export default function InspectorPanel({ documentId, documentName, onOverlay }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [tab, setTab] = useState('takeoff');
  const [options, setOptions] = useState({ ceiling_height_m: '', glazing_height_m: '', egress_limit_m: '', daylight_min_ratio: '' });
  const [rates, setRates] = useState({});
  const [lock, setLock] = useState(null);
  const [lens, setLens] = useState(false);
  const [selected, setSelected] = useState(null);
  const lockKey = `trace-takeoff-lock:${documentId}`;
  const overlay = useRef(onOverlay);
  overlay.current = onOverlay;

  useEffect(() => {
    if (!documentId) return undefined;
    const controller = new AbortController();
    setError('');
    fetch(endpoint(documentId, options), { signal: controller.signal })
      .then(async response => {
        const body = await response.json();
        if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'The inspection could not be computed.');
        return body;
      })
      .then(setData)
      .catch(cause => { if (cause.name !== 'AbortError') setError(cause.message); });
    try { setLock(JSON.parse(localStorage.getItem(lockKey) || 'null')); } catch { setLock(null); }
    return () => controller.abort();
  }, [documentId, options, lockKey]);

  useEffect(() => () => overlay.current?.(null), []);

  const lines = useMemo(() => (data?.boq || []).map(line => {
    const rate = rates[line.key] || {};
    const unitCost = rate.cost ?? line.unit_cost_eur;
    const carbon = rate.carbon ?? line.carbon_kg_per_unit;
    return { ...line, unitCost, carbon, total: line.quantity * unitCost, carbonTotal: line.quantity * carbon };
  }), [data, rates]);
  const totals = lines.reduce((sum, line) => ({ eur: sum.eur + line.total, kg: sum.kg + line.carbonTotal }), { eur: 0, kg: 0 });
  const roomById = useMemo(() => Object.fromEntries((data?.rooms || []).map(room => [room.id, room])), [data]);

  const show = (key, payload) => { setSelected(key); overlay.current?.(payload); };
  const showRooms = ids => ({ rooms: ids.map(id => roomById[id]).filter(room => room?.polygon) });
  const showCheck = check => show(`check:${check.check}:${check.room}`, { ...showRooms(check.evidence || []), path: check.path, circle: check.circle, status: check.status });
  const toggleLens = () => {
    const next = !lens;
    setLens(next);
    overlay.current?.(next ? { lens: (data?.rooms || []).filter(room => room.polygon) } : null);
  };

  const exportCsv = () => {
    const header = ['Item', 'Quantity', 'Unit', 'Unit cost EUR', 'Total EUR', 'kg CO2e per unit', 'kg CO2e', 'Basis'];
    const rows = lines.map(l => [l.item, l.quantity, l.unit, l.unitCost, l.total.toFixed(2), l.carbon, l.carbonTotal.toFixed(1), l.basis]);
    rows.push(['TOTAL', '', '', '', totals.eur.toFixed(2), '', totals.kg.toFixed(1), '']);
    const meta = [['Drawing', documentName || documentId], ['Generated', new Date().toISOString()],
      ['Approved by', lock?.by || 'not approved'], ['Approved at', lock?.at || ''],
      ['Note', 'Quantities measured from the drawing. Unit costs and carbon factors are editable placeholders, not quotes or EPD values.']];
    const csv = [...meta, [], header, ...rows].map(r => r.map(csvCell).join(',')).join('\n');
    const link = document.createElement('a');
    link.href = URL.createObjectURL(new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' }));
    link.download = `${(documentName || 'takeoff').replace(/\.[^.]+$/, '')}-bill-of-quantities.csv`;
    link.click();
    URL.revokeObjectURL(link.href);
  };

  const approve = () => {
    const by = window.prompt('Approve and lock this takeoff. Your name:');
    if (!by) return;
    const record = { by, at: new Date().toISOString(), totals: { eur: Math.round(totals.eur), kg: Math.round(totals.kg) }, lines: lines.length };
    localStorage.setItem(lockKey, JSON.stringify(record));
    setLock(record);
  };
  const unlock = () => { localStorage.removeItem(lockKey); setLock(null); };

  if (!documentId) return null;
  const checks = data?.checks || [];
  const failing = checks.filter(c => c.status !== 'pass').length;
  return <details className="inspector-panel" name="drawing-tools">
    <summary>Takeoff &amp; code check{data ? <span className="inspector-summary"> · {money(totals.eur)} · {failing ? `${failing} to review` : 'all checks pass'}</span> : null}</summary>
    {error && <p className="inspector-error" role="alert">{error}</p>}
    {!data && !error && <p className="inspector-muted">Computing from the drawing…</p>}
    {data && <>
      <div className="inspector-tabs" role="tablist">
        {[['takeoff', 'Bill of quantities'], ['checks', `Checks (${checks.length})`], ['rooms', 'Rooms & translation']].map(([key, label]) =>
          <button key={key} type="button" role="tab" aria-selected={tab === key} className={tab === key ? 'is-active' : ''} onClick={() => setTab(key)}>{label}</button>)}
      </div>
      {data.warnings?.map(w => <p key={w} className="inspector-warning">{w}</p>)}

      {tab === 'takeoff' && <div className="inspector-body">
        <div className="inspector-totals"><div><span>Tender estimate</span><strong>{money(totals.eur)}</strong></div><div><span>Embodied carbon</span><strong>{kg(totals.kg)}</strong></div></div>
        <table className="inspector-table">
          <thead><tr><th>Item</th><th className="num">Qty</th><th className="num">€/unit</th><th className="num">Total</th><th className="num">kg CO₂e/u</th></tr></thead>
          <tbody>{lines.map(line => <tr key={line.key} className={selected === `boq:${line.key}` ? 'is-selected' : ''} onClick={() => show(`boq:${line.key}`, showRooms(line.evidence))} title={line.basis}>
            <td>{line.item}</td><td className="num">{line.quantity.toLocaleString()} {line.unit}</td>
            <td className="num"><input aria-label={`Unit cost for ${line.item}`} type="number" min="0" step="1" disabled={!!lock} value={line.unitCost} onClick={e => e.stopPropagation()} onChange={e => setRates({ ...rates, [line.key]: { ...rates[line.key], cost: Math.max(0, Number(e.target.value) || 0) } })} /></td>
            <td className="num">{money(line.total)}</td>
            <td className="num"><input aria-label={`Carbon factor for ${line.item}`} type="number" min="0" step="0.1" disabled={!!lock} value={line.carbon} onClick={e => e.stopPropagation()} onChange={e => setRates({ ...rates, [line.key]: { ...rates[line.key], carbon: Math.max(0, Number(e.target.value) || 0) } })} /></td>
          </tr>)}</tbody>
        </table>
        <p className="inspector-muted">Quantities are measured from the drawing; click a line to see its rooms. Costs and carbon factors are placeholders: enter your price book and EPD values.</p>
        <div className="inspector-actions">
          <button type="button" className="button" onClick={exportCsv}>Export CSV (Excel / Procore import)</button>
          {lock ? <><span className="inspector-locked">Approved by {lock.by}, {new Date(lock.at).toLocaleString()}</span><button type="button" className="text-button" onClick={unlock}>Unlock</button></>
            : <button type="button" className="button primary" onClick={approve}>Approve &amp; lock takeoff</button>}
        </div>
      </div>}

      {tab === 'checks' && <div className="inspector-body">
        <div className="inspector-options">
          <label>Ceiling height (m)<input type="number" step="0.05" placeholder={data.options.ceiling_height_m} value={options.ceiling_height_m} onChange={e => setOptions({ ...options, ceiling_height_m: e.target.value })} /></label>
          <label>Window glass height (m)<input type="number" step="0.05" placeholder={data.options.glazing_height_m} value={options.glazing_height_m} onChange={e => setOptions({ ...options, glazing_height_m: e.target.value })} /></label>
          <label>Escape route limit (m)<input type="number" step="1" placeholder={data.options.egress_limit_m} value={options.egress_limit_m} onChange={e => setOptions({ ...options, egress_limit_m: e.target.value })} /></label>
          <label>Min. glazing / floor<input type="number" step="0.005" placeholder={data.options.daylight_min_ratio} value={options.daylight_min_ratio} onChange={e => setOptions({ ...options, daylight_min_ratio: e.target.value })} /></label>
        </div>
        {!checks.length && <p className="inspector-muted">No code checks available for this drawing.</p>}
        <ul className="inspector-checks">{[...checks].sort((a, b) => (a.status === 'pass') - (b.status === 'pass')).map(check =>
          <li key={`${check.check}:${check.room}`}><button type="button" className={selected === `check:${check.check}:${check.room}` ? 'is-selected' : ''} onClick={() => showCheck(check)}>
            <span className={`inspector-chip status-${check.status}`}>{check.status.toUpperCase()}</span>
            <span className="inspector-check-text"><strong>{CHECK_NAMES[check.check] || check.check} · {check.label}</strong>
              <small>{check.check === 'daylight' ? `${(check.value * 100).toFixed(1)} % (min ${(check.limit * 100).toFixed(1)} %)` : `${check.value} m (${check.check === 'egress' ? 'max' : 'min'} ${check.limit} m)`} — {check.detail}</small></span>
          </button></li>)}</ul>
        <p className="inspector-muted">Limits are editable defaults; set them to the code that applies to your project.</p>
      </div>}

      {tab === 'rooms' && <div className="inspector-body">
        <label className="inspector-lens"><input type="checkbox" checked={lens} onChange={toggleLens} /> Translation lens on the drawing (hover a room)</label>
        <table className="inspector-table">
          <thead><tr><th>Label on drawing</th><th>Function</th><th>IFC space</th><th className="num">m²</th></tr></thead>
          <tbody>{(data.rooms || []).map(room => <tr key={room.id} className={selected === `room:${room.id}` ? 'is-selected' : ''} onClick={() => show(`room:${room.id}`, showRooms([room.id]))}>
            <td>{room.number ? `${room.number} ` : ''}{room.label}</td><td>{room.english}</td><td>{room.ifc_space_type}</td><td className="num">{room.area_m2 != null ? room.area_m2.toFixed(2) : '—'}</td>
          </tr>)}</tbody>
        </table>
      </div>}
    </>}
  </details>;
}

// Overlay drawn inside the drawing stage (viewBox 0..1000 in both axes).
export function InspectorOverlay({ overlay }) {
  if (!overlay) return null;
  const pts = poly => poly.map(([x, y]) => `${x * 1000},${y * 1000}`).join(' ');
  return <svg className="inspector-shapes" viewBox="0 0 1000 1000" preserveAspectRatio="none">
    {(overlay.rooms || []).map(room => <polygon key={room.id} points={pts(room.polygon)} className="inspector-room" />)}
    {(overlay.lens || []).map(room => <polygon key={room.id} points={pts(room.polygon)} className={`inspector-lens-room function-${room.function}`}>
      <title>{`${room.label}${room.number ? ` (${room.number})` : ''} → ${room.english} · IFC ${room.ifc_space_type}${room.area_m2 != null ? ` · ${room.area_m2.toFixed(2)} m²` : ''}`}</title>
    </polygon>)}
    {overlay.path && <polyline points={pts(overlay.path)} className={`inspector-path status-${overlay.status}`} />}
    {overlay.path && <circle cx={overlay.path[0][0] * 1000} cy={overlay.path[0][1] * 1000} r="5" className="inspector-path-start" />}
    {overlay.circle && <ellipse cx={overlay.circle.centre[0] * 1000} cy={overlay.circle.centre[1] * 1000}
      rx={overlay.circle.radius_x * 1000} ry={overlay.circle.radius_y * 1000} className={`inspector-circle status-${overlay.status}`} />}
  </svg>;
}
