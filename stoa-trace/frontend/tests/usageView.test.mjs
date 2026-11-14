import test from 'node:test';
import assert from 'node:assert/strict';
import { usageValue, spendingCoverage } from '../src/usageView.js';

test('partial pricing shows the known cost without calling it the full total',()=>{
  const usage={model_calls:4,cost_unavailable_calls:3,cost_known_usd:0.0161,cost_estimate_usd:null,input_tokens:38817,output_tokens:6813};
  assert.deepEqual(spendingCoverage(usage),{requests:4,unpriced:3,priced:1,knownCost:0.0161});
  assert.equal(usageValue(usage,'tokens'),45630);
  assert.equal(usageValue(usage,'cost'),0.0161);
});
test('empty periods contain no invented usage or spend',()=>{
  assert.deepEqual(spendingCoverage(null),{requests:0,unpriced:0,priced:0,knownCost:0});
  assert.equal(usageValue(undefined,'tokens'),0);
});
