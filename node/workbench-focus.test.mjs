import test from 'node:test';
import assert from 'node:assert/strict';
import {focusWorkbenchHeading} from '../web/shared/workbench-focus.mjs';
test('step changes bring offscreen content into view while preserving visible content position',()=>{
 for(const [top,bottom,shouldScroll] of [[-640,-610,true],[950,980,true],[90,120,false]]){
  let focused=false,scroll=null;
  const heading={focus:options=>{focused=options.preventScroll;},getBoundingClientRect:()=>({top,bottom}),closest:()=>({getBoundingClientRect:()=>({top:top-28})})};
  focusWorkbenchHeading(heading,{innerHeight:900,scrollY:1031,scrollTo:options=>{scroll=options;}});
  assert.equal(focused,true);assert.equal(heading.tabIndex,-1);assert.equal(Boolean(scroll),shouldScroll);
  if(shouldScroll)assert.equal(scroll.top,Math.max(0,top-28+1031-24));
 }
});
