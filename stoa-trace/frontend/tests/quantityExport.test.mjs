import test from 'node:test';
import assert from 'node:assert/strict';
import { quantityRows, quantitiesCsv } from '../src/quantityExport.js';

const records = [
  { id: 'm1', answerId: 'a1', question: 'What is the total net floor area of all rooms?', documentName: 'plan.dxf' },
  { id: 'm2', answerId: 'a2', question: 'How many doors are shown?', documentName: 'plan.dxf' },
  { id: 'm3', answerId: 'pending', question: 'Still loading', documentName: 'plan.dxf' },
];
const answers = {
  a1: { id: 'a1', value: 19.62, unit: 'm²', answer: '19.62 m², from 2 room area annotations.', status: 'supported', scope: 'Selected floor drawing',
    document: { name: '0123456789ab-plan.dxf', source: 'uploads' }, request_context: { scope: 'document', page: 1, region: [0, 0, .5, .5] },
    calculation: { operation: 'sum', terms: [13.62, 6], result: 19.62 },
    evidence: [{ id: 'r1', label: 'Stanza', properties: { room_number: '5.11' } }, { id: 'r2', label: 'Bagno', properties: { room_number: '5.12' } }] },
  a2: { id: 'a2', value: 9, unit: 'count', answer: '9 doors.', status: 'human_reviewed', human_reviewed: true, review: { revision: 2 },
    document: { name: 'plan.dxf', source: 'swiss_dwellings' }, calculation: { operation: 'count_distinct_guid', count: 9 }, evidence: [{ id: 'd1', label: 'Door frame' }] },
};

test('each answered question becomes one row, and a sum lists its measured items', () => {
  const rows = quantityRows(records, answers);
  assert.deepEqual(rows[0].slice(0, 3), ['Question', 'Quantity', 'Unit']);
  assert.equal(rows.length, 5);
  assert.deepEqual(rows[1].slice(0, 3), ['What is the total net floor area of all rooms?', 19.62, 'm²']);
  assert.equal(rows[1][4], 'plan.dxf');
  assert.equal(rows[1][5], 'Selected floor drawing, selected area');
  assert.equal(rows[1][6], 'sum of 2 source quantities');
  assert.deepEqual(rows[2], ['  5.11 Stanza', 13.62, 'm²']);
  assert.deepEqual(rows[3], ['  5.12 Bagno', 6, 'm²']);
  assert.deepEqual([rows[4][1], rows[4][2], rows[4][7], rows[4][8], rows[4][9]], [9, 'count', 'human reviewed', 'revision 2', 'a2']);
});

test('item lines use the unit of the terms, and a formula is the basis', () => {
  const wall = { id: 'w', value: 62.4, unit: 'm²', answer: '62.4 m² of wall area.', status: 'supported',
    calculation: { formula: '24 m × 2.6 m = 62.4 m²', terms: [14, 10], term_unit: 'm' }, evidence: [{ id: 'a', label: 'Living' }, { id: 'b', label: 'Kitchen' }] };
  const rows = quantityRows([{ answerId: 'w', question: 'Wall area?' }], { w: wall });
  assert.equal(rows[1][6], '24 m × 2.6 m = 62.4 m²');
  assert.deepEqual(rows[2], ['  Living', 14, 'm']);
  const ranked = { ...wall, calculation: { operation: 'max', terms: [14, 10] }, evidence: [{ id: 'a', label: 'Living' }] };
  assert.equal(quantityRows([{ answerId: 'w', question: 'Largest?' }], { w: ranked }).length, 2);
});

test('the file opens in a spreadsheet with the reader\'s decimal mark and no formula cells', () => {
  const rows = [['Question', 'Quantity'], ['=HYPERLINK("http://example.test")', 13.62], ['Rooms 1, 2; "A"', 1e21], ['Geometry', 2.002139190581575], ['-2 rooms', Number.NaN]];
  const comma = quantitiesCsv(rows, ',');
  assert.ok(comma.startsWith('﻿Question;Quantity\r\n'));
  assert.ok(comma.includes('"\'=HYPERLINK(""http://example.test"")";13,62\r\n'));
  assert.ok(comma.includes('"Rooms 1, 2; ""A""";1e+21\r\n'));
  assert.ok(comma.includes('Geometry;2,0021\r\n'));
  assert.ok(comma.endsWith("'-2 rooms;\r\n"));
  assert.ok(quantitiesCsv(rows).includes(',13.62\r\n'));
  assert.ok(quantitiesCsv([['Tiny', 0.00004]]).includes('Tiny,0.00004\r\n'));
});


test('grouped quantities remain separate rows in the whole chat export', () => {
  const result = { id: 'g', rows: [{ label: 'Oak', value: 9, unit: 'count' }, { label: 'Steel', value: 4, unit: 'count' }], status: 'supported' };
  const rows = quantityRows([{ answerId: 'g', question: 'Group by material' }], { g: result });
  assert.equal(rows.length, 4);
  assert.deepEqual(rows[2].slice(0, 3), ['  Oak', 9, 'count']);
  assert.deepEqual(rows[3].slice(0, 3), ['  Steel', 4, 'count']);
  assert.equal(rows[3][9], 'g');
});
