// A chat's answered quantities as a spreadsheet file. Presentation only: every value
// comes from a saved answer and nothing is recalculated here.
const text = value => value == null ? '' : String(value);

export function quantityRows(records, answers) {
  const rows = [['Question', 'Quantity', 'Unit', 'Answer', 'Drawing', 'Scope', 'Basis', 'Status', 'Reviewed', 'Answer ID']];
  for (const record of records) {
    const answer = answers[record.answerId];
    if (!answer) continue;
    const calculation = answer.calculation && typeof answer.calculation === 'object' ? answer.calculation : {};
    const terms = Array.isArray(calculation.terms) ? calculation.terms : [];
    const evidence = Array.isArray(answer.evidence) ? answer.evidence : [];
    const basis = typeof answer.calculation === 'string' ? answer.calculation
      : calculation.formula || calculation.expression || calculation.plan?.explanation
        || (calculation.operation ? `${calculation.operation}${terms.length ? ` of ${terms.length} source ${terms.length === 1 ? 'quantity' : 'quantities'}` : ''}`.replaceAll('_', ' ') : '');
    const name = text(answer.document?.name || record.documentName);
    const context = answer.request_context || {};
    rows.push([record.question, typeof answer.value === 'number' ? answer.value : '', answer.unit, answer.answer || answer.message,
      answer.document?.source === 'uploads' ? name.replace(/^[a-f0-9]{12}-/i, '') : name,
      [typeof answer.scope === 'string' ? answer.scope : answer.scope?.label, context.region ? 'selected area' : context.scope === 'page' ? `page ${context.page}` : ''].filter(Boolean).join(', '),
      basis, answer.source_changed ? 'source changed' : text(answer.status).replaceAll('_', ' '),
      answer.human_reviewed ? `revision ${answer.review?.revision ?? 1}` : '', answer.id]);
    for (const group of answer.rows || []) {
      rows.push([`  ${text(group.label)}`, typeof group.value === 'number' ? group.value : '', group.unit, '', name, '', 'Source group', answer.status, '', answer.id]);
    }
    // A sum of source quantities also lists each measured item, so a total of room areas reads as a room schedule.
    if (terms.length > 1 && terms.length === evidence.length && terms.every(term => typeof term === 'number')) {
      evidence.forEach((item, index) => rows.push([`  ${[item.properties?.room_number, item.label].filter(Boolean).join(' ') || item.id}`, terms[index], calculation.term_unit || answer.unit]));
    }
  }
  return rows;
}

// Spreadsheet programs read a comma-decimal locale with semicolon separators, and run a
// cell that starts with = + - or @ as a formula.
export function quantitiesCsv(rows, decimal = '.') {
  const separator = decimal === ',' ? ';' : ',';
  const cell = value => {
    // Four decimals match the precision of the totals and drop floating-point noise.
    if (typeof value === 'number') return Number.isFinite(value) ? String(Math.abs(value) < .001 ? value : Number(value.toFixed(4))).replace('.', decimal) : '';
    const safe = /^[=+\-@\t\r]/.test(text(value)) ? `'${text(value)}` : text(value);
    return /[",;\r\n]/.test(safe) ? `"${safe.replaceAll('"', '""')}"` : safe;
  };
  return `﻿${rows.map(row => row.map(cell).join(separator)).join('\r\n')}\r\n`;
}
