import test from 'node:test';
import assert from 'node:assert/strict';
import { focusDrawingBox } from '../src/canvasFocus.js';

test('a tiny door cannot trigger excessive automatic magnification',()=>{
 const image={width:2400,height:1800},viewport={width:700,height:600},box=[.1,.2,.104,.206];
 const result=focusDrawingBox(box,image,viewport,2);
 assert.ok(result.scale<=.5);
 assert.ok(result.scale<=2.2*Math.min(650/2400,550/1800));
 assert.ok(Math.abs(result.x+(box[0]+box[2])/2*image.width*result.scale-350)<1e-8);
 assert.ok(Math.abs(result.y+(box[1]+box[3])/2*image.height*result.scale-300)<1e-8);
});
test('a low-resolution upload is centered without adding zoom beyond its fitted view',()=>{
 const result=focusDrawingBox([.1,.1,.12,.12],{width:300,height:200},{width:800,height:600},2);
 assert.equal(result.scale,2.5);
 assert.equal(focusDrawingBox([0,0,1,1],{width:0,height:0},{width:800,height:600}),null);
});
