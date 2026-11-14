import test from 'node:test';
import assert from 'node:assert/strict';
import { draftCountSummary } from '../src/reviewState.js';

test('the chat summary reflects draft exclusions and additions immediately', () => {
  const answer = { category: 'window', evidence: [{id:'first'},{id:'second'}] };
  assert.equal(draftCountSummary(answer, [], ['first']), '1 window after your changes.');
  assert.equal(draftCountSummary(answer, [{id:'added'}], ['first']), '2 windows after your changes.');
  assert.equal(draftCountSummary(answer, [], ['first','second']), '0 windows after your changes.');
});
