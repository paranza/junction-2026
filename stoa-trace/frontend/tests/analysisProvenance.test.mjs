import test from 'node:test';
import assert from 'node:assert/strict';
import { analysisProvenance, modelDisplayName } from '../src/analysisProvenance.js';

const reviewed = overrides => ({
  method: 'visual_inventory', operation: 'count', unit: 'count', model: 'gemini-4-carbon', value: 5,
  count_audit: { status: 'completed', initial_model: 'gemini-4-carbon', auditor_model: 'gemma-4-31b-it', initial_value: 4, audited_value: 5, independent_verification: false },
  ...overrides,
});

test('native quantities and calibrated measurements never acquire visual model provenance from usage', () => {
  for (const method of ['native_ifc_quantity', 'native_object_selection', 'calibrated_polygon_area']) {
    assert.equal(analysisProvenance({ method, model: 'gemini-4-carbon', usage: { models: ['gemini/gemini-4-carbon'] } }), null);
  }
});

test('distinct model roles and original-to-audited counts remain visible after human corrections', () => {
  const result = analysisProvenance(reviewed({ value: 7, human_reviewed: true }));
  assert.equal(result.analysisModel, 'Gemini 4 Carbon');
  assert.equal(result.reviewer, 'Gemma 4 31B');
  assert.equal(result.statusText, 'Review completed');
  assert.deepEqual(result.changedCounts, { before: 4, after: 5 });
  assert.equal(result.note, 'Model review; inspect the highlighted evidence.');
  assert.equal(JSON.stringify(result).includes('verified'), false);
});

test('an unavailable or incomplete review cannot advertise a completed count correction', () => {
  for (const [status, text] of [['unavailable', 'Review unavailable'], ['incomplete', 'Review incomplete'], ['incomplete_scope', 'Scope incomplete']]) {
    const source = reviewed(); source.count_audit.status = status;
    const result = analysisProvenance(source);
    assert.equal(result.statusText, text);
    assert.equal(result.changedCounts, null);
    if (status !== 'incomplete') assert.equal(result.reviewerLabel, 'Selected reviewer');
  }
});

test('unreviewed visual results do not invent a reviewer, including cached inventories', () => {
  const result = analysisProvenance({ method: 'visual_inventory', model: 'gemini-4-carbon', usage: { cache_hit: true, models: [] } });
  assert.equal(result.analysisModel, 'Gemini 4 Carbon');
  assert.equal(result.reviewer, null);
  assert.equal(result.statusText, null);
});

test('zero is a valid original count but missing, negative and noninteger counts are not comparisons', () => {
  const source = reviewed(); source.count_audit.initial_value = 0;
  assert.deepEqual(analysisProvenance(source).changedCounts, { before: 0, after: 5 });
  for (const value of [null, -1, 1.5, NaN, '4']) {
    const invalid = reviewed(); invalid.count_audit.initial_value = value;
    assert.equal(analysisProvenance(invalid).changedCounts, null);
  }
  const area = reviewed({ operation: 'area', unit: 'm²' });
  assert.equal(analysisProvenance(area).changedCounts, null);
});

test('model names are readable without implying a missing model was used', () => {
  assert.equal(modelDisplayName('gemini/gemma-4-26b-a4b-it'), 'Gemma 4 26B A4B');
  assert.equal(modelDisplayName('models/gemma-4-31b-it'), 'Gemma 4 31B');
  assert.equal(modelDisplayName(null), 'Model not recorded');
  assert.equal(analysisProvenance({ method: 'vision' }).reviewer, null);
});
