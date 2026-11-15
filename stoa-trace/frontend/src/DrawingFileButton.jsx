import React from 'react';

export const DRAWING_FILE_ACCEPT = '.pdf,.png,.jpg,.jpeg,.gif,.webp,.bmp,.tif,.tiff,.svg,.dxf,.dwg,.ifc';

// The pointer/keyboard activates the actual file input. This avoids relying on
// a second, programmatic click retaining the browser's transient activation.
export default function DrawingFileButton({children,className='',label='Upload drawing',disabled=false,onFiles}) {
  return <span className="drawing-file-control" onClick={event=>event.stopPropagation()} onKeyDown={event=>event.stopPropagation()}>
    <button type="button" className={className} tabIndex={-1} aria-hidden="true" disabled={disabled}>{children}</button>
    <input type="file" aria-label={label} multiple accept={DRAWING_FILE_ACCEPT} disabled={disabled}
      onChange={event=>{
        const files=Array.from(event.currentTarget.files || []);
        event.currentTarget.value='';
        if (files.length) onFiles(files);
      }} />
  </span>;
}
