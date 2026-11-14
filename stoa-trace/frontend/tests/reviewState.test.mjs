import test from 'node:test';
import assert from 'node:assert/strict';
import { evidenceBox, evidenceKind, savedAdditions, originalEvidence, reviewEvidence, reviewCount, reviewFingerprint, costText, aggregateUsage, countedCategory, allowedCountCategories, canonicalCategory, usageLabel, evidenceVerificationText, canResolveComparison, formatQuantityValue } from '../src/reviewState.js';

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


test('manual additions inherit the counted category, including zero counts and IFC records', () => {
  assert.equal(countedCategory({ category: 'window', value: 0, evidence: [] }), 'window');
  assert.equal(countedCategory({ evidence: [{ type: 'IfcDoor' }, { type: 'IfcDoor' }] }), 'door');
  assert.equal(countedCategory({ evidence: [{ type: 'apartment' }] }), 'apartment');
  assert.equal(countedCategory({ evidence: [{ type: 'washbasin' }] }), 'sink');
  assert.equal(countedCategory({ calculation: { classes: ['IfcSanitaryTerminal', 'washbasin'] }, evidence: [] }), 'sink');
  assert.equal(countedCategory({ evidence: [{ type: 'door' }, { type: 'window' }] }), null);
  assert.equal(countedCategory({ evidence: [{ label: 'Door beside lobby' }] }), null);
  assert.equal(canonicalCategory('sanitary_fixture'), 'sanitary_fixture');
});

test('reused visual inventory is never labelled native just because follow-up uses zero calls', () => {
  assert.equal(usageLabel({ inventory_cache_hit: true, usage: { model_calls: 0 } }), 'Prepared visual inventory reused');
  assert.equal(usageLabel({ usage: { inventory_cache_hit: true, model_calls: 0 } }), 'Prepared visual inventory reused');
  assert.equal(usageLabel({ inventory_cache_hit: true, usage: { cache_hit: true, model_calls: 0 } }), 'Saved answer reused');
  assert.equal(usageLabel({ usage: { model_calls: 0 } }), 'Native source tools');
});


test('evidence origin stays separate from quantity and semantic verification', () => {
  assert.equal(evidenceKind({ evidence_kind: 'native', source_verified: false, verification: { identity: true, quantity: null } }), 'native');
  assert.equal(evidenceKind({ evidence_kind: 'visual', source_verified: true }), 'visual');
  assert.equal(evidenceKind({ evidence_kind: 'native', manual: true }), 'manual');
  assert.equal(evidenceKind({ id: 'visual-inventory-1' }), 'visual');
  assert.equal(evidenceKind({ id: 'native-1', source_verified: false }), 'native');
  const notes = evidenceVerificationText({ verification: { identity: true, quantity: false, semantic_selection_verified: false } });
  assert.ok(notes.includes('Source identifier exists.'));
  assert.ok(notes.includes('Quantity is not supported by the cited source.'));
  assert.ok(notes.includes('Object selection and count completeness still require review.'));
});


test('working quantity choices require comparable finite values and an unchanged source', () => {
  const original = { value: 0, evidence: [], reconciliation: { status: 'disagreement', native_value: 0, visual_value: 1, unit: 'count' } };
  assert.equal(canResolveComparison(original), true);
  assert.equal(canResolveComparison({ ...original, source_changed: true }), false);
  assert.equal(canResolveComparison({ ...original, reconciliation: { ...original.reconciliation, status: 'scope_mismatch' } }), false);
  assert.equal(canResolveComparison({ ...original, reconciliation: { ...original.reconciliation, visual_value: null } }), false);
  assert.equal(original.value, 0);
});


test('quantity presentation limits float noise without altering values or exact counts', () => {
  const value = 13.617073235712027;
  assert.equal(formatQuantityValue(value, 'm²'), '13.617');
  assert.equal(formatQuantityValue(13.62, 'm²'), '13.62');
  assert.equal(formatQuantityValue(49560, 'ft²'), '49560');
  assert.equal(formatQuantityValue(17, 'count'), '17');
  assert.equal(formatQuantityValue(.0001234567, 'm³'), '0.0001235');
  assert.equal(value, 13.617073235712027);
});


test('mixed counts allow exactly the component categories for review', () => {
  assert.deepEqual(allowedCountCategories({category:'shower+bathtub'}), ['shower','bathtub']);
  assert.deepEqual(allowedCountCategories({category:'IfcDoor'}), ['door']);
  assert.deepEqual(allowedCountCategories({allowed_count_categories:['shower','bathtub','shower']}), ['shower','bathtub']);
});
