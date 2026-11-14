// Adapted from BoardUI's free MIT Agent Thinking wave/spin implementation.
// Copyright (c) 2026 Mertcan Dundar Esmergul (BoardUI). See LICENSE and README.
import React, { useEffect, useState } from 'react';
import './agent-thinking.css';

const SEED = [0.55,0.3,0.15,0.85,0.55,0.3,1,0.85,0.55];
export default function AgentThinking({ variant='wave', label='Analyzing drawing' }) {
  const [opacities,setOpacities]=useState(SEED);
  useEffect(()=>{
    const preference=window.matchMedia('(prefers-reduced-motion: reduce)');
    let timer,phase=0;
    const update=()=>{
      window.clearInterval(timer); setOpacities(SEED);
      if(preference.matches)return;
      timer=window.setInterval(()=>{
        phase=(phase+1/8)%1;
        setOpacities(Array.from({length:9},(_,index)=>{
          const column=index%3,row=Math.floor(index/3);
          const scalar=variant==='spin'?(Math.atan2(row-1,column-1)/(2*Math.PI)+1)%1:((column+row)/4)*(3/4);
          const behind=(phase-scalar+1)%1;
          return 0.12+0.88*Math.max(0,1-behind/0.3)**1.5;
        }));
      },80);
    };
    update(); preference.addEventListener('change',update);
    return()=>{window.clearInterval(timer);preference.removeEventListener('change',update)};
  },[variant]);
  return <div className="board-agent-thinking" role="status"><span className="board-thinking-grid" aria-hidden="true">{opacities.map((opacity,index)=><span key={index} style={{opacity}}/>)}</span><span>{label}</span></div>;
}
