import test from 'node:test';
import assert from 'node:assert/strict';
import { resumeAnalysisRequest, interruptedAnalysisText } from '../src/resumeAnalysis.js';

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

test('interrupted route summaries use actual progress and preserve completed quantities', () => {
  const partial = { retryable_analysis: true, value: null, route_inspection: {source_tiles:3},
    inspection: [{tile:1,complete:true}, {tile:2,complete:false}, {tile:3,complete:true}] };
  assert.equal(interruptedAnalysisText(partial), '2 of 3 source areas inspected. Continue analysis to finish.');
  assert.equal(interruptedAnalysisText({...partial,route_inspection:null,count_inspection:{source_tiles:3}}), '2 of 3 source areas inspected. Continue analysis to finish.');
  assert.equal(interruptedAnalysisText({...partial,value:20}), null);
  assert.equal(interruptedAnalysisText({retryable_analysis:true}), 'Analysis was interrupted. Continue to finish checking the source.');
});

test('changed sources, another drawing and invalid saved scopes cannot resume', () => {
  for (const item of [{ ...answer, source_changed: true }, { ...answer, retryable_analysis: false },
      { ...answer, request_context: { ...answer.request_context, document_id: 'other' } },
      { ...answer, request_context: { ...answer.request_context, region: [0, 0, 2, 1] } }]) {
    assert.equal(resumeAnalysisRequest(item, 'drawing'), null);
  }
  assert.equal(resumeAnalysisRequest(answer, 'other'), null);
});

test('native detail areas count separately inside the same coarse tile', () => {
  const partial = {retryable_analysis:true,value:null,route_inspection:{source_tiles:4},
    inspection:[{tile:1,detail:1,complete:true},{tile:1,detail:2,complete:true},
      {tile:1,detail:3,complete:false},{tile:1,detail:4,complete:true}]};
  assert.equal(interruptedAnalysisText(partial),'3 of 4 source areas inspected. Continue analysis to finish.');
});
