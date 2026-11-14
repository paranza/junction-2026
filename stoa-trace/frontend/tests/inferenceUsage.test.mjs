import test from 'node:test';
import assert from 'node:assert/strict';
import { acceptUsageSnapshot, inferenceCost, inferenceSessionId, messageCost, money, requestFailure, usagePending } from '../src/inferenceUsage.js';

const session = 'd3a56502-b8c6-4405-884c-e6e73f566288';
const usage = (extra = {}) => ({ model_calls: 1, input_tokens: 1000, output_tokens: 250, cost_estimate_usd: .0045, ...extra });
const snapshot = (revision, aggregate = usage(), extra = {}) => ({ session_id: session, revision, aggregate, by_message: [], ...extra });

test('session cost accepts authoritative totals without adding historical extraction or cached answer costs again', () => {
  const first = snapshot(1);
  const cached = snapshot(2, usage(), { by_message: [{ request_id: 'first', usage: usage() }, { request_id: 'cached', usage: usage({ model_calls: 0, cost_estimate_usd: 0, cache_hit: true }), ingestion_usage: usage() }] });
  const result = acceptUsageSnapshot(first, cached, session);
  assert.equal(result.aggregate.cost_estimate_usd, .0045);
  assert.equal(result.aggregate.model_calls, 1);
  assert.equal(messageCost(result.by_message[1].usage), '$0 · cached');
});

test('slower earlier refreshes cannot replace a newer total or another session', () => {
  const current = snapshot(5, usage({ cost_estimate_usd: .012 }));
  assert.equal(acceptUsageSnapshot(current, snapshot(4), session), current);
  assert.equal(acceptUsageSnapshot(current, { ...snapshot(6), session_id: 'another-session' }, session), current);
  assert.equal(acceptUsageSnapshot(current, { ...snapshot(6), revision: NaN }, session), current);
  assert.equal(acceptUsageSnapshot(current, snapshot(6), session).revision, 6);
});

test('failed or incomplete calls preserve a known subtotal and never become free inference', () => {
  assert.deepEqual(inferenceCost(usage({ cost_estimate_usd: null, cost_known_usd: .0045, usage_incomplete: true })), { text: '$0.0045 known + unknown', unknown: true });
  assert.equal(messageCost(usage({ cost_estimate_usd: null, model_calls: 1, usage_incomplete: true })), 'Cost unknown');
  assert.equal(messageCost(null), 'Cost unknown');
  assert.equal(messageCost(usage({ cost_estimate_usd: 0, model_calls: 0 })), '$0 · no model calls');
  assert.equal(inferenceCost(usage({ cost_estimate_usd: 0, usage_incomplete: true })).unknown, true);
});

test('cost presentation does not round tiny positive inference charges to zero', () => {
  assert.equal(money(.0000005), '<$0.0001');
  assert.equal(money(0), '$0');
  assert.equal(money(-1), 'Unknown');
  assert.equal(money('0'), 'Unknown');
});

test('FastAPI error detail retains attempt usage and message identity', () => {
  const error = requestFailure({ detail: { message: 'Model request failed', message_id: 'attempt-1', usage: usage({ cost_estimate_usd: null, usage_incomplete: true }) } }, 503);
  assert.equal(error.message, 'Model request failed');
  assert.equal(error.messageId, 'attempt-1');
  assert.equal(error.usage.model_calls, 1);
  assert.equal(error.status, 503);
  assert.equal(requestFailure({ detail: 'Drawing not found' }, 404).message, 'Drawing not found');
});

test('tab identity survives reload and blocked browser storage has a stable fallback', () => {
  let saved = session;
  const storage = { getItem: () => saved, setItem: (_, value) => { saved = value; } };
  assert.equal(inferenceSessionId(storage, () => { throw new Error('Must reuse saved session'); }), session);
  saved = null;
  assert.equal(inferenceSessionId(storage, () => session), session);
  assert.equal(inferenceSessionId(storage), session);
  const blocked = { getItem: () => { throw new Error('Blocked'); }, setItem: () => { throw new Error('Blocked'); } };
  assert.equal(inferenceSessionId(blocked), session);
});

test('pending server messages keep usage tracking active after the browser stopped waiting', () => {
  assert.equal(usagePending(snapshot(1, usage(), { by_message: [{ status: 'pending' }] })), true);
  assert.equal(usagePending(snapshot(2, usage(), { by_message: [{ status: 'error' }] })), false);
  assert.equal(usagePending(snapshot(3, usage(), { by_message: [{ status: 'completed' }] })), false);
});
