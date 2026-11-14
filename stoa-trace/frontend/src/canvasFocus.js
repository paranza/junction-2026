export function focusDrawingBox(box, image, viewport, pixelRatio=1) {
  if (!box || !image.width || !image.height || !viewport.width || !viewport.height) return null;
  const fit=Math.max(0.015,Math.min((viewport.width-50)/image.width,(viewport.height-50)/image.height));
  const nativeScale=1/Math.max(1,pixelRatio);
  const maximum=Math.max(fit,Math.min(nativeScale,fit*2.2));
  const width=Math.max(0.025,box[2]-box[0])*image.width;
  const height=Math.max(0.025,box[3]-box[1])*image.height;
  const scale=Math.max(fit,Math.min(maximum,viewport.width*0.4/width,viewport.height*0.4/height));
  return {scale,x:viewport.width/2-(box[0]+box[2])/2*image.width*scale,
    y:viewport.height/2-(box[1]+box[3])/2*image.height*scale};
}
