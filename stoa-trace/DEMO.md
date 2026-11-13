# A three-minute Trace demo

Open the workspace, choose a source, and ask a question. Every example below is computed from the drawing/model rather than a lookup of the supplied answer labels.

1. Search `site1102_bldg2242_floor10281.pdf`. Ask **“What is the net floor area of room 5.11 ('Stanza') in m²?”** Expected source-supported result: **13.62 m²**. Click the evidence item to inspect the room. Explain how native CAD labels and geometry can be aligned to the paired PDF.
2. Search `A-801`. Open the Xcel Sports Complex door/finish schedule. Ask **“On sheet A-801 of the Xcel Sports Complex drawings, what is the area of room 128 (Fieldhouse) in the finish room schedule?”** Expected result: **29,690 ft²**. Show the cited schedule row and calculation.
3. Search `ac20_arc.ifc`. Ask **“How many doors are in the model?”** Expected modeled inventory: **77 doors**. Expand a source item to show its exact GUID and properties. Explain when a model has no linked drawing projection rather than inventing a highlight.
4. To demonstrate corrections, ask a count question with multiple located candidates, exclude an item, and recompute. The revised value is computed from the included set and marked as reviewed; it does not establish that no objects were missed. Refresh and restore the saved question to show that the review persisted.

For a visual example, search `high_quality_architectural-10370.png` and ask **“How many windows are shown on this floor plan?”** This is intentionally a limitation example: the tested vision response included a partially cropped window and disagreed with the supplied count label. Inspect the markers and warning instead of presenting it as a correct autonomous result.

The defensible pitch is: **a stronger model can improve interpretation while the source extraction, geometry, reproducible calculations, scope controls and review trail remain useful.**

The frozen benchmark is a diagnostic sample, not a competition score. The final native run answered 22/50 questions: all 21 answered numeric questions matched the supplied labels; one text answer awaits manual review. Across all 44 numeric questions, accuracy was 21/44 because abstentions count as failures. The three separate vision tests got two areas correct and one count wrong. Do not combine these small samples into a general accuracy claim.

Before presenting, check the live workspace and API credit quota. The configured OpenAI key expires November 20 and the Verda provisioning credential November 16. Existing VM operation does not require the provisioning credential to remain active; future cloud management does. No GPU or fine-tuned drawing segmentation model is deployed in this version.
