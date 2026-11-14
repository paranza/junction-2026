import assert from 'node:assert/strict';
import { test } from 'node:test';
import { closeupRequestGate, closeupTarget, protectedCloseupImage } from '../src/evidenceCloseup.js';

const evidence = { id: 'native/room 2', bbox: [.1, .2, .4, .6], page: 3 };
const answer = { id: 'answer-1', evidence: [evidence] };

test('only current, saved, located evidence can create a close-up', () => {
  const target = closeupTarget(answer, evidence);
  assert.equal(target.path, '/api/answers/answer-1/evidence/native%2Froom%202/closeup');
  assert.equal(closeupTarget({ ...answer, source_changed: true }, evidence), null);
  assert.equal(closeupTarget(answer, { ...evidence, id: 'draft-addition' }), null);
  assert.equal(closeupTarget(answer, { ...evidence, bbox: [0, 0, 0, .2] }), null);
  assert.equal(closeupTarget(answer, { ...evidence, bbox: [-.1, 0, .5, .5] }), null);
  assert.notEqual(closeupTarget(answer, { ...evidence, page: 4 }).key, target.key);
});

test('saved manual additions and polygon bounds remain eligible without altering their source geometry', () => {
  const manual = { id: 'manual-2', polygon: [[.1, .2], [.6, .2], [.6, .8]], page: 2 };
  const original = structuredClone(manual);
  assert.ok(closeupTarget({ id: 'a', review: { added_evidence: [manual] } }, manual));
  assert.deepEqual(manual, original);
  assert.equal(closeupTarget({ id: 'a', evidence: [manual] }, { ...manual, bbox: [0, 0, 0, 0] }), null);
});

test('image rendering accepts only the protected local media token and valid intrinsic dimensions', () => {
  const payload = { provider: 'cloudinary', image_url: `/api/media/${'a'.repeat(64)}.png`, width: 1000, height: 750 };
  assert.deepEqual(protectedCloseupImage(payload), { src: payload.image_url, width: 1000, height: 750 });
  for (const url of ['https://res.cloudinary.com/account/private/image.png', '//example.com/api/media/a.png', `${payload.image_url}?redirect=https://example.com`, '/api/media/../secret.png', 'data:image/png;base64,abc']) {
    assert.equal(protectedCloseupImage({ ...payload, image_url: url }), null);
  }
  assert.equal(protectedCloseupImage({ ...payload, height: 0 }), null);
  assert.equal(protectedCloseupImage({ ...payload, provider: 'other' }), null);
});

test('a superseded attempt or changed selection cannot display a late close-up response', () => {
  const gate = closeupRequestGate();
  const first = gate.begin();
  const second = gate.begin();
  assert.equal(gate.accepts(first), false);
  assert.equal(gate.accepts(second), true);
  gate.dispose();
  assert.equal(gate.accepts(second), false);
  const nextSelection = closeupRequestGate();
  assert.equal(nextSelection.accepts(nextSelection.begin()), true);
});
