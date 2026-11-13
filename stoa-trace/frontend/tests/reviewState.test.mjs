import test from 'node:test';
import assert from 'node:assert/strict';
import { evidenceBox, evidenceKind, savedAdditions, originalEvidence, reviewEvidence, reviewCount, reviewFingerprint, costText, aggregateUsage } from '../src/reviewState.js';

test('polygon evidence has focusable bounds and invalid geometry stays unlocated', () => {
  assert.deepEqual(evidenceBox({ polygon: [[.2, .3], [.7, .4], [.5, .9]] }), [.2, .3, .7, .9]);
  assert.equal(evidenceBox({ polygon: [[.2, .3], [Number.NaN, .4], [.5, .9]] }), null);
  assert.equal(evidenceBox({ bbox: [.8, .2, .1, .9] }), null);
  assert.equal(evidenceBox({ bbox: [null, .2, .8, .9] }), null);
  assert.equal(evidenceBox({ bbox: [-.1, .2, .8, .9] }), null);
  assert.equal(evidenceBox({ guid: 'native-guid', page: 1 }), null);
});

test('review restores immutable originals and includes additions only once after reloading', () => {
  const first = { id: 'door-1', label: 'Door', page: 1, bbox: [.1, .1, .2, .2] };
  const second = { id: 'door-2', label: 'Door', page: 1, bbox: [.3, .1, .4, .2] };
  const added = { id: 'manual-1', label: 'Missed door', page: 1, bbox: [.5, .1, .6, .2], manual: true };
  const saved = { original_value: 2, original_evidence: [first, second], added_evidence: [added], evidence: [first, { ...second, excluded: true }, added] };
  const before = JSON.stringify(saved);
  assert.equal(originalEvidence(saved).length, 2);
  assert.equal(savedAdditions(saved).length, 1);
  assert.equal(reviewEvidence(saved, savedAdditions(saved)).length, 3);
  assert.equal(reviewCount(saved, savedAdditions(saved), ['door-2']), 2);
  assert.equal(reviewCount(saved, savedAdditions(saved), ['door-2', 'manual-1']), 1);
  assert.equal(JSON.stringify(saved), before);
});

test('a missed object can be added to an established zero count and restored', () => {
  const original = { value: 0, evidence: [] };
  const addition = { id: 'manual-window', label: 'Window', manual: true };
  assert.equal(reviewCount(original, [addition], []), 1);
  assert.equal(reviewCount(original, [], []), 0);
});

test('evidence origin and unknown inference cost do not imply verification or free inference', () => {
  assert.equal(evidenceKind({ id: 'vision-2' }), 'visual');
  assert.equal(evidenceKind({ id: 'manual-2' }), 'manual');
  assert.equal(evidenceKind({ guid: 'native' }), 'native');
  assert.equal(costText({ model_calls: 1, cost_estimate_usd: null, cost_basis: 'unconfigured' }), 'Cost unavailable');
  assert.equal(costText({ model_calls: 0, cost_estimate_usd: null, cost_basis: 'native' }), '$0 model inference');
  assert.equal(costText({ cost_estimate_usd: .01234 }), '$0.0123 estimated');
});

test('review changes are order insensitive for exclusions but track note and additions', () => {
  assert.equal(reviewFingerprint(['b', 'a'], [], 'checked'), reviewFingerprint(['a', 'b'], [], 'checked'));
  assert.notEqual(reviewFingerprint([], [], ''), reviewFingerprint([], [], 'verified door identity visually'));
  assert.notEqual(reviewFingerprint([], [], ''), reviewFingerprint([], [{ id: 'manual' }], ''));
});


test('per-page initial usage is aggregated without treating unknown costs as free', () => {
  const combined = aggregateUsage([{ model_calls: 1, input_tokens: 100, output_tokens: 20, cost_estimate_usd: .02 }, { model_calls: 1, input_tokens: 200, output_tokens: 40, cost_estimate_usd: null }]);
  assert.equal(combined.model_calls, 2);
  assert.equal(combined.input_tokens, 300);
  assert.equal(combined.output_tokens, 60);
  assert.equal(combined.cost_estimate_usd, null);
  assert.equal(aggregateUsage([]), null);
});
