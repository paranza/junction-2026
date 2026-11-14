import test from 'node:test';
import assert from 'node:assert/strict';
import { attachChatDrawing } from '../src/chatAttachment.js';

test('confirmed attachment opens without a follow-up history request', async () => {
  const calls = [];
  const saved = {id:'a',document_id:'drawing'};
  const result = await attachChatDrawing(async (...args) => {
    calls.push(args);
    if (args[1] === 'GET' || args.length === 1) throw new Error('History unavailable');
    return {thread:saved};
  }, {threads:[{id:'a',document_id:null}],active:'a',documentId:'drawing',identity:'new'});
  assert.equal(result.thread, saved);
  assert.deepEqual(calls,[['/api/workspace/chats/a','PATCH',{document_id:'drawing'}]]);
});

test('retry after a lost response reuses the same thread identity', async () => {
  const calls=[];
  const options={threads:[{id:'a',document_id:'first',project_id:'p'}],active:'a',documentId:'second',identity:'stable'};
  const request=async (...args)=>{calls.push(args);if(calls.length===1)throw new Error('Lost response');return {thread:{id:'stable',document_id:'second'}}};
  await assert.rejects(attachChatDrawing(request,options));
  const result=await attachChatDrawing(request,options);
  assert.equal(result.thread.id,'stable');
  assert.equal(result.switched,true);
  assert.equal(calls[0][2].session_id,'stable');
  assert.deepEqual(calls[0],calls[1]);
});

test('opening a drawing already in this project reuses its chat', async () => {
  const existing={id:'b',document_id:'second',project_id:'p'};
  const result=await attachChatDrawing(()=>{throw new Error('Unexpected request')},{threads:[{id:'a',document_id:'first',project_id:'p'},existing],active:'a',documentId:'second',identity:'new'});
  assert.equal(result.thread,existing);
});
