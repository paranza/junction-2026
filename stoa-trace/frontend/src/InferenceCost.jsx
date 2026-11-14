import React, { useId } from 'react';
import { ChevronDown } from 'lucide-react';
import { inferenceCost, messageCost, usageNumber } from './inferenceUsage.js';
import './InferenceCost.css';

export function MessageInferenceCost({ usage, label = 'This message' }) {
  return <div className="message-inference-cost" aria-label={`${label} inference cost`}>
    <span>{label}</span><strong>{messageCost(usage)}</strong>
  </div>;
}

export default function InferenceCost({ snapshot, unavailable }) {
  const popoverId = useId();
  const usage = snapshot?.aggregate;
  const cost = inferenceCost(usage);
  const messages = Array.isArray(snapshot?.by_message) ? snapshot.by_message.slice().reverse() : [];
  const total = usage ? cost.text : unavailable ? 'Unavailable' : 'Loading…';
  return <div className="session-inference" aria-label="Current session inference cost">
    <button type="button" className="session-cost-trigger" popoverTarget={popoverId} aria-label={`Session inference cost: ${total}. View breakdown`}>
      <span>Session cost</span><strong aria-live="polite">{total}</strong><ChevronDown size={14} aria-hidden="true" />
    </button>
    <div id={popoverId} popover="auto" className="session-inference-popover" role="region" aria-label="Session inference breakdown">
      <div className="session-inference-heading"><span>Session inference</span><strong>{total}</strong></div>
      <div className="session-inference-metrics"><span>{usageNumber(usage?.model_calls)} model calls</span><span>{usageNumber(usage && Number.isFinite(usage.input_tokens) && Number.isFinite(usage.output_tokens) ? usage.input_tokens + usage.output_tokens : null)} tokens</span></div>
      <p>{unavailable ? usage ? 'Could not refresh usage. The last recorded total is shown.' : 'Session usage is unavailable on this server.' : 'Estimated token cost before credits. Hosting and media costs are separate.'}</p>
      <div className="session-message-details"><h3>{snapshot?.message_count ?? messages.length} session messages</h3>
        {messages.length ? <ol>{messages.map(item => <li key={item.request_id || item.message_id || item.answer_id}>
          <span title={item.question}>{item.question || 'Drawing question'}</span>
          <div><strong>{['pending', 'running', 'in_progress'].includes(item.status) ? 'In progress' : messageCost(item.usage)}</strong><small>{item.status === 'error' || item.status === 'failed' ? 'Request failed' : item.status === 'pending' ? 'Server is still running' : `${usageNumber(item.usage?.model_calls)} model calls`}</small></div>
        </li>)}</ol> : <p>Your question costs will appear here.</p>}
      </div>
    </div>
  </div>;
}
