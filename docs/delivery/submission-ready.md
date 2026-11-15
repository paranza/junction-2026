# Metria — submission fields

Project name: Metria

Punchline: Your blueprint, with the answers drawn in.

Challenge: Make Blueprints Talk — Stoa

Demo: https://stoa-86-38-182-146.sslip.io/

Source: https://github.com/paranza/junction-2026

Other link: https://github.com/paranza/junction-2026#readme

Tech challenges: Best Use of Gemini API; Best Use of Cloudinary; Verda Compute Track.

Presentation: [Metria PDF](Metria-Junction-2026.pdf). No final video is available.

## Description

Metria makes construction drawings interactive. Upload a blueprint, ask a question, and see the answer connected to the objects, annotations and geometry on the plan.

Built for construction engineers, Metria brings quantity extraction, measurement and source inspection into one workspace. Ask about doors, windows, rooms, floor areas or visible piping routes. Select a region to focus the analysis, explore the highlighted evidence and export the results.

### Intelligence that works with the drawing

Metria combines Gemini visual reasoning with native document extraction and geometric computation. It reads supported PDF text and schedules, DXF geometry and IFC records. For scanned and complex drawings, Gemini inspects detailed source regions, identifies relevant features and selects the tools needed to answer the question.

Counts are assembled from located objects. Measurements are calculated from source geometry, dimensions and drawing scales. The result stays connected to the drawing, making quantities easier to inspect, discuss and use.

### Built for the engineering workflow

A chat-first interface sits beside a large plan preview. Conversations stay organized by drawing, selected-area questions focus the analysis, and evidence artifacts bring the supporting details into the conversation. Engineers can inspect close-ups, adjust counts and retain the original answer alongside their review.

### Meaningful technology integrations

Gemini powers visual inspection, source interpretation and tool selection.

Cloudinary transforms selected evidence coordinates into detailed source close-ups, connecting each answer to an inspectable part of the drawing.

Verda hosts the persistent application, API, drawing tools, uploads and database. We also used Verda GPU compute to train and evaluate a pretrained drawing-symbol detector as part of our research.

The application combines React, FastAPI, SQLite, CAD/PDF parsers and geometric tools, with inference usage tracking, persistent conversations and evidence export.

Metria puts the question, quantity and supporting drawing evidence in the same place.
