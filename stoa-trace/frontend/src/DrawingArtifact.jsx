import React, { useEffect, useId, useState } from 'react';
import { FileText, ChevronDown } from 'lucide-react';

export default function DrawingArtifact({ count, focusRequest=0, children }) {
  const [open,setOpen]=useState(false);
  const bodyId=useId();
  useEffect(()=>{if(focusRequest>0)setOpen(true)},[focusRequest]);
  return <div className="chat-artifact">
    <button type="button" className="artifact-toggle" aria-expanded={open} aria-controls={bodyId} onClick={()=>setOpen(value=>!value)}>
      <FileText size={17}/><span>Evidence</span><small>{count}</small><ChevronDown size={15} style={{transform:open?'rotate(180deg)':undefined}}/>
    </button>
    <div className="artifact-body" id={bodyId} hidden={!open}>{children}</div>
  </div>;
}
