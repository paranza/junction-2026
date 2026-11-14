// self-check of the Gemini box_2d -> pixel math used in the browser snippet
const toPx = ([y0, x0, y1, x1], W, H) => ({ x: x0 * W / 1000, y: y0 * H / 1000, width: (x1 - x0) * W / 1000, height: (y1 - y0) * H / 1000 });
const r = toPx([100, 250, 500, 750], 2000, 1000);
console.assert(r.x === 500 && r.y === 100 && r.width === 1000 && r.height === 400, r);
console.log("ok", r);
