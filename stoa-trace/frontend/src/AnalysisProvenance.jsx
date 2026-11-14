import React from 'react';
import { analysisProvenance } from './analysisProvenance.js';
import './AnalysisProvenance.css';

export default function AnalysisProvenance({ answer }) {
  const provenance = analysisProvenance(answer);
  if (!provenance) return null;
  return <section className="analysis-provenance" aria-label="Analysis sources">
    <div className="analysis-provenance-heading">
      <h3>Analysis sources</h3>
      {provenance.statusText && <span>{provenance.statusText}</span>}
    </div>
    <dl>
      <dt>Drawing analysis</dt><dd>{provenance.analysisModel}</dd>
      {provenance.reviewer && <><dt>{provenance.reviewerLabel}</dt><dd>{provenance.reviewer}</dd></>}
      {provenance.changedCounts && <>
        <dt>Initial candidates</dt><dd>{provenance.changedCounts.before}</dd>
        <dt>After model review</dt><dd>{provenance.changedCounts.after}</dd>
      </>}
    </dl>
    <p>{provenance.note}</p>
  </section>;
}
