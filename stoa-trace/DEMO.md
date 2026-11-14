# A three-minute Trace demo

Open the workspace, choose a source, and ask a question. Every example below is computed from the drawing/model rather than a lookup of the supplied answer labels.

1. Search `site1102_bldg2242_floor10281.pdf`. Ask **“What is the net floor area of room 5.11 ('Stanza') in m²?”** Expected source-supported result: **13.62 m²**. Click the evidence item to inspect the room. Explain how native CAD labels and geometry can be aligned to the paired PDF.
2. Search `A-801`. Open the Xcel Sports Complex door/finish schedule. Ask **“On sheet A-801 of the Xcel Sports Complex drawings, what is the area of room 128 (Fieldhouse) in the finish room schedule?”** Expected result: **29,690 ft²**. Show the cited schedule row and calculation.
3. Search `ac20_arc.ifc`. Ask **“How many doors are in the model?”** Expected modeled inventory: **77 doors**. Expand a source item to show its exact GUID and properties. Explain when a model has no linked drawing projection rather than inventing a highlight.
4. Reuse `site1102_bldg2242_floor10281.pdf` and ask **"How many windows are drawn on this floor plan?"** The native inventory contains **13 windows**. Click a source item to focus it. Demonstrate Add missed object, an exclusion, undo, a review note, save and reload. For a rehearsal on this correct native result, explicitly identify any temporary addition as a workflow test and restore the original count afterward. Do not describe a test mark as a genuine missed window. The original answer and every review revision remain available in the export.
5. On room 5.11, enable comparison and ask the net-area question again. Show the printed annotation versus the independently calculated native outline area, their tolerance, and the source region. Save a working quantity with a reason if appropriate. Agreement is not independent proof of correctness. A deliberately conflicting generated fixture belongs in a clearly labelled test demonstration, never a claimed real-project discrepancy.

For a visual example, search `high_quality_architectural-10370.png` and ask **“How many windows are shown on this floor plan?”** This is intentionally a limitation example: the tested vision response included a partially cropped window and disagreed with the supplied count label. Inspect the markers and warning instead of presenting it as a correct autonomous result.

The defensible pitch is: **a stronger model can improve interpretation while the source extraction, geometry, reproducible calculations, scope controls and review trail remain useful.**

The upgraded native diagnostic answers 30/50 questions: 28 correct numeric answers
and two text answers awaiting manual review. Across all 44 numeric questions,
accuracy is 28/44 because abstentions count as failures. On a separate paired
100-question evaluation, numeric correctness improved from 41/97 to 55/97,
with three incorrect answered numeric cases remaining. These stratified samples
are not competition scores. The earlier three vision tests got two areas correct
and one count wrong; the new inventory's live visual accuracy remains unmeasured.
Keep numeric accuracy, coverage, evidence checks and inference cost separate.

Show the answer's usage details and distinguish initial visual extraction from
cached follow-up questions. Model calls require configured credentials and the
existing attempt allowance; a zero-call native rehearsal works without a key.

Before presenting, check the live workspace and API credit quota. The configured OpenAI key expires November 20 and the Verda provisioning credential November 16. Existing VM operation does not require the provisioning credential to remain active; future cloud management does. No GPU or fine-tuned drawing segmentation model is deployed in this version.
