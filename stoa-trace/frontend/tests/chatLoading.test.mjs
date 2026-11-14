import test from 'node:test';
import assert from 'node:assert/strict';
import { loadChatWorkspace } from '../src/chatLoading.js';
test('refresh reads existing chats without creating or changing a thread',async()=>{
 const calls=[];const data={projects:[],threads:[{id:'existing'}]};
 assert.equal(await loadChatWorkspace(async(...args)=>{calls.push(args);return data}),data);
 assert.deepEqual(calls,[['/api/chats']]);
});
test('a transient service failure is retried and recovered',async()=>{
 let calls=0;const data={projects:[],threads:[]};
 const result=await loadChatWorkspace(async()=>{if(++calls<3)throw new Error('startup');return data},{delay:async()=>{}});
 assert.equal(result,data);assert.equal(calls,3);
});
test('unavailable history returns safely after bounded attempts',async()=>{
 let calls=0;assert.equal(await loadChatWorkspace(async()=>{calls++;throw new Error('offline')},{delay:async()=>{}}),null);assert.equal(calls,3);
});
test('invalid service data cannot replace saved thread state',async()=>{
 assert.equal(await loadChatWorkspace(async()=>({threads:'invalid',projects:[]}),{delay:async()=>{}}),null);
});
test('leaving the workspace discards an in-flight load',async()=>{
 let active=true;const result=await loadChatWorkspace(async()=>{active=false;return{projects:[],threads:[]}},{active:()=>active});assert.equal(result,null);
});
