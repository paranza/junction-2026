import test from 'node:test';
import assert from 'node:assert/strict';
import { resumeAnalysisRequest } from '../src/resumeAnalysis.js';

const answer = { document_id: 'drawing', question: 'Count the openings in this area', retryable_analysis: true,
  request_context: { document_id: 'drawing', page: 2, scope: 'page', region: [.2, .3, .8, .9] } };

test('continuing keeps the original page and selection without a follow-up answer hint', () => {
  const result = resumeAnalysisRequest(answer, 'drawing');
  assert.equal(result.page, 2);
  assert.deepEqual(result.region, [.2, .3, .8, .9]);
  assert.equal(result.question, answer.question);
  assert.equal(result.previous_answer_id, undefined);
  result.region[0] = .1;
  assert.equal(answer.request_context.region[0], .2);
});

test('changed sources, another drawing and invalid saved scopes cannot resume', () => {
  for (const item of [{ ...answer, source_changed: true }, { ...answer, retryable_analysis: false },
      { ...answer, request_context: { ...answer.request_context, document_id: 'other' } },
      { ...answer, request_context: { ...answer.request_context, region: [0, 0, 2, 1] } }]) {
    assert.equal(resumeAnalysisRequest(item, 'drawing'), null);
  }
  assert.equal(resumeAnalysisRequest(answer, 'other'), null);
});
