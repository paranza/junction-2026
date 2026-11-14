import test from 'node:test';
import assert from 'node:assert/strict';
import { acceptHydratedAnswer, conversationKey, mergeConversation, pendingAnswerIds, readConversation, recordFromAnswer, recordsFromSnapshot, saveConversation } from '../src/conversationState.js';

const session = 'd3a56502-b8c6-4405-884c-e6e73f566288';
const record = (id, extra = {}) => ({ id, answerId: id, question: `Question ${id}`, timestamp: 1000, status: 'completed', documentName: 'plan.pdf', ...extra });
const memory = () => { const data = new Map(); return { getItem: key => data.get(key), setItem: (key, value) => data.set(key, value) }; };

test('session transcript is scoped and persists IDs, never cached answer values', () => {
  const storage = memory();
  saveConversation(storage, session, [record('first', { value: 99, evidence: ['untrusted'] })]);
  const restored = readConversation(storage, session);
  assert.equal(restored.length, 1);
  assert.equal(restored[0].id, 'first');
  assert.equal(restored[0].value, undefined);
  assert.equal(restored[0].evidence, undefined);
  assert.deepEqual(readConversation(storage, 'another-session'), []);
  storage.setItem(conversationKey('another-session'), storage.getItem(conversationKey(session)));
  assert.deepEqual(readConversation(storage, 'another-session'), []);
});

test('out-of-order metadata cannot duplicate a turn or regress a completed answer to pending', () => {
  const current = [record('first')];
  const next = mergeConversation(current, [record('first', { question: 'Updated question', timestamp: 9000 }), record('first', { status: 'pending', answerId: null })]);
  assert.equal(next.length, 1);
  assert.equal(next[0].status, 'completed');
  assert.equal(next[0].timestamp, 1000);
  assert.equal(next[0].answerId, 'first');
  assert.strictEqual(mergeConversation(next, next), next);
});

test('the conversation keeps chronological distinct messages even for repeated question wording', () => {
  const records = mergeConversation([], Array.from({ length: 30 }, (_, i) => record(`id-${i}`, { question: 'How many doors?', timestamp: i })));
  assert.equal(records.length, 24);
  assert.equal(records[0].id, 'id-6');
  assert.equal(records.at(-1).id, 'id-29');
});

test('hydration fetches completed saved answers only and skips unavailable ones', () => {
  const records = [record('first'), record('pending', { status: 'pending', answerId: null }), record('failed', { status: 'error', answerId: null }), record('missing')];
  assert.deepEqual(pendingAnswerIds(records, { first: { id: 'first' } }, new Set(['missing'])), []);
  assert.deepEqual(pendingAnswerIds(records, {}), ['first', 'missing']);
});

test('server session mismatch and malformed stored IDs cannot introduce a transcript entry', () => {
  const rows = [{ message_id: 'first', answer_id: 'first', question: 'How many doors?', created_at: 12, status: 'completed' }];
  assert.deepEqual(recordsFromSnapshot({ session_id: 'other', by_message: rows }, session), []);
  const accepted = mergeConversation([], recordsFromSnapshot({ session_id: session, by_message: rows }, session));
  assert.equal(accepted[0].timestamp, 12000);
  assert.deepEqual(mergeConversation([], [record('../arbitrary-path'), record('bad', { question: '' }), record('bad-time', { timestamp: NaN })]), []);
});

test('reviewed answer metadata preserves its saved identity and original question', () => {
  const item = recordFromAnswer({ id: 'saved', message_id: 'message', question: 'Count these doors', document: { name: 'level-2.pdf' }, created_at: 100, value: 7 }, 'Fallback');
  assert.equal(item.id, 'message');
  assert.equal(item.answerId, 'saved');
  assert.equal(item.question, 'Count these doors');
  assert.equal(item.documentName, 'level-2.pdf');
  assert.equal(item.timestamp, 100000);
  assert.equal(item.value, undefined);
});

test('late hydration cannot replace a newer reviewed answer or cross answer identities', () => {
  const original = { id: 'answer', value: 4 };
  const empty = acceptHydratedAnswer({}, 'answer', original);
  assert.equal(empty.answer.value, 4);
  const reviewed = { answer: { id: 'answer', value: 3, human_reviewed: true } };
  assert.strictEqual(acceptHydratedAnswer(reviewed, 'answer', original), reviewed);
  assert.strictEqual(acceptHydratedAnswer(reviewed, 'different', original), reviewed);
  assert.deepEqual(acceptHydratedAnswer({}, 'answer', { id: 'different', value: 999 }), {});
});
