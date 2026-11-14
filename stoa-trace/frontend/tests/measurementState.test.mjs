import test from 'node:test';
import assert from 'node:assert/strict';
import { measurementDraft, parseMeasurementPoints, validMeasurementPoints } from '../src/measurementState.js';

const context = { page: 1, source_fingerprint: 'source-v1', image_width: 2000, image_height: 1000 };
const reference = [[0, 0], [1, 0]];
const geometry = [[0, 0], [1, 0], [1, 1], [0, 1]];
const draft = options => measurementDraft({ documentId: 'uploaded-plan', page: 1, context,
  reference, geometry, value: '10', unit: 'm', kind: 'area', ...options });

test('coordinate entry accepts line pairs and JSON without accepting out-of-page points', () => {
  assert.deepEqual(parseMeasurementPoints('0.1, 0.2\n0.8, 0.9').points, [[.1, .2], [.8, .9]]);
  assert.deepEqual(parseMeasurementPoints('[[0,0],[1,1]]').points, [[0, 0], [1, 1]]);
  for (const text of ['1.1, 0.2', 'hello', '0.1,0.2,0.3', ',0.3', '0.3,', ',', '0x0,1', '[[true,0],[1,1]]', '[[null,0],[1,1]]']) {
    assert.ok(parseMeasurementPoints(text).error, text);
  }
  assert.deepEqual(parseMeasurementPoints('').points, []);
});

test('a measurement needs an explicit reference, current source and sufficient geometry', () => {
  for (const options of [{ reference: [] }, { reference: [[0, 0], [0, 0]] }, { value: '' },
    { value: '0' }, { value: '-2' }, { value: 'Infinity' }, { unit: 'px' },
    { geometry: [[0, 0], [1, 0]] }, { context: { ...context, page: 2 } },
    { context: { page: 1 } }, { page: 0 }, { kind: 'volume' }]) {
    assert.ok(draft(options).error, JSON.stringify(options));
  }
});

test('payload pins the source and clones drawn points instead of retaining mutable UI state', () => {
  const drawn = geometry.map(point => [...point]);
  const result = draft({ geometry: drawn });
  assert.equal(result.error, '');
  assert.equal(result.payload.source_fingerprint, 'source-v1');
  assert.equal(result.payload.calibration.document_id, 'uploaded-plan');
  assert.equal(result.payload.calibration.value, 10);
  drawn[0][0] = .9;
  assert.equal(result.payload.geometry[0][0], 0);
});

test('length uses two endpoints and rejects repeated or extra endpoints', () => {
  assert.equal(draft({ kind: 'length', geometry: [[0, 0], [.5, .5]] }).error, '');
  assert.ok(draft({ kind: 'length', geometry }).error);
  assert.equal(validMeasurementPoints([[0, 0], [0, 0]], 2, true), false);
  assert.equal(validMeasurementPoints([[0, 0], [1, 1]], 2, true), true);
});
