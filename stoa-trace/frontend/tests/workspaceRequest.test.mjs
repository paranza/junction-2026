import test from 'node:test';
import assert from 'node:assert/strict';
import { workspaceRequest } from '../src/workspaceRequest.js';

test('a cached HTML page cannot be mistaken for a successful chat response',async()=>{
  await assert.rejects(workspaceRequest('/api/workspace/chats','GET',undefined,{fetcher:async()=>new Response('<html>old app</html>',{headers:{'content-type':'text/html'}})}),/page instead of chat data/);
});
test('connection failures and HTTP errors remain distinguishable',async()=>{
  await assert.rejects(workspaceRequest('/api/workspace/chats','GET',undefined,{fetcher:async()=>{throw new TypeError('fetch failed')}}),/Cannot reach the local server/);
  await assert.rejects(workspaceRequest('/api/workspace/chats','GET',undefined,{fetcher:async()=>new Response('private diagnostic',{status:404})}),error=>error.status===404&&error.message.includes('HTTP 404')&&!error.message.includes('private diagnostic'));
});
test('a stalled connection has a bounded wait and a retryable error',async()=>{
  await assert.rejects(workspaceRequest('/api/workspace/chats','GET',undefined,{fetcher:async()=>{throw new DOMException('timed out','TimeoutError')}}),/did not respond in time/);
});
