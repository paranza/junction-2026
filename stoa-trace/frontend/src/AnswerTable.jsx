import React from 'react';
import { formatQuantityValue } from './reviewState.js';

export default function AnswerTable({ rows, evidence, onSelect }) {
  if (!rows?.length) return null;
  return <div className="answer-table-scroll"><table className="answer-table">
    <thead><tr><th scope="col">Group</th><th scope="col">Quantity</th><th scope="col"><span className="sr-only">Source</span></th></tr></thead>
    <tbody>{rows.map((row, index) => {
      const source = evidence.find(item => row.object_ids?.includes(item.id));
      return <tr key={index}><th scope="row">{row.label}</th><td>{formatQuantityValue(row.value, row.unit)} {row.unit}</td><td>{source && <button type="button" onClick={() => onSelect(source)} aria-label={`Show source for ${row.label}`}>Show source</button>}</td></tr>;
    })}</tbody>
  </table></div>;
}
