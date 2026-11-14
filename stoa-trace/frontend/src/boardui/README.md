# BoardUI primitives in Trace

Button and Divider are adapted from the free MIT-licensed [BoardUI source](https://github.com/BoardUI/boardui), commit `ec5c5eb3e29c2441be63b9422cd54f411ef23466`, checked 14 November 2026.

Sources: `components/base/buttons/button.tsx` and `components/base/divider/divider.tsx`. The React structure and variant interfaces are retained; TypeScript and Tailwind token classes were adapted to Trace's existing JSX and CSS stack. Colors use Trace's semantic tokens, gradients are omitted, and coarse pointers receive larger targets. No Pro source or paid template is included. The inference-cost section is original Trace code, not BoardUI's Pro Agent Limits component.

The upstream MIT notice is retained in LICENSE. See the [official license explanation](https://www.boardui.com/license) for the distinction between free and Pro source.
