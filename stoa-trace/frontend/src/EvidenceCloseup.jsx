import React, { useEffect, useId, useRef, useState } from 'react';
import { LoaderCircle, X, ZoomIn } from 'lucide-react';
import { Button } from './boardui/primitives.jsx';
import { closeupRequestGate, closeupTarget, protectedCloseupImage } from './evidenceCloseup.js';
import './EvidenceCloseup.css';

function CloseupDialog({ image, label, page, onClose }) {
  const dialog = useRef(null);
  const titleId = useId();
  const [imageFailed, setImageFailed] = useState(false);
  useEffect(() => {
    const opener = document.activeElement;
    dialog.current?.showModal();
    return () => { if (opener?.isConnected) opener.focus(); };
  }, []);
  return <dialog ref={dialog} className="evidence-closeup-dialog" aria-labelledby={titleId} onCancel={event => { event.preventDefault(); onClose(); }} onClose={onClose}>
    <header><div><h2 id={titleId}>{label}</h2><p>Source close-up{page ? ` · page ${page}` : ''}</p></div><Button variant="ghost" size="small" aria-label="Close evidence close-up" onClick={onClose}><X size={20} /></Button></header>
    <div className="evidence-closeup-image">{imageFailed ? <p role="alert">The close-up image could not load. Close this view and try again.</p> : <img src={image.src} width={image.width} height={image.height} alt={`Close-up of ${label}${page ? ` on source page ${page}` : ''}`} onError={() => setImageFailed(true)} />}</div>
    <footer>Selected source region, prepared with Cloudinary.</footer>
  </dialog>;
}

function CloseupControl({ target, label, page, request }) {
  const [available, setAvailable] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [image, setImage] = useState(null);
  const gate = useRef(null);
  const activeRequest = useRef(null);
  if (!gate.current) gate.current = closeupRequestGate();
  useEffect(() => {
    const controller = new AbortController();
    const currentGate = closeupRequestGate();
    gate.current = currentGate;
    request('/api/media/status', { signal: controller.signal }).then(result => {
      if (!controller.signal.aborted) setAvailable(result?.available === true && result.provider === 'cloudinary');
    }).catch(() => { /* Older servers and unavailable media quietly keep the normal viewer. */ });
    return () => { controller.abort(); activeRequest.current?.abort(); currentGate.dispose(); };
  }, [request]);
  const open = async () => {
    const currentGate = gate.current;
    const ticket = currentGate.begin();
    activeRequest.current?.abort();
    const controller = new AbortController();
    activeRequest.current = controller;
    setLoading(true); setError('');
    try {
      const result = await request(target.path, { method: 'POST', signal: controller.signal });
      if (!currentGate.accepts(ticket)) return;
      const next = protectedCloseupImage(result);
      if (!next) throw new Error('Invalid close-up response');
      setImage(next);
    } catch (failure) {
      if (failure.name !== 'AbortError' && currentGate.accepts(ticket)) setError('Could not create this close-up. Try again or inspect the original drawing.');
    } finally {
      if (currentGate.accepts(ticket)) { setLoading(false); activeRequest.current = null; }
    }
  };
  if (!available) return null;
  return <div className="evidence-closeup-control">
    <Button variant="secondary" size="small" onClick={open} disabled={loading} aria-busy={loading}>{loading ? <LoaderCircle size={15} className="spin" /> : <ZoomIn size={15} />}{loading ? 'Creating close-up…' : 'Open evidence close-up'}</Button>
    <p>{loading ? 'Preparing the selected source region…' : 'Creates a Cloudinary close-up of this source page.'}</p>
    {error && <p className="evidence-closeup-error" role="alert">{error}</p>}
    {image && <CloseupDialog image={image} label={label} page={page} onClose={() => setImage(null)} />}
  </div>;
}

export default function EvidenceCloseup({ answer, evidence, request }) {
  const target = closeupTarget(answer, evidence);
  return target ? <CloseupControl key={target.key} target={target} label={evidence.label || evidence.name || `Source ${evidence._number || ''}`.trim()} page={evidence.page} request={request} /> : null;
}
