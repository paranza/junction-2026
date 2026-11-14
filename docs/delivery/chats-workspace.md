# Chats workspace

The Metria navigation separates Chats, Dataset, Spending and Settings. Chats accepts uploads and keeps each drawing's conversation separate. Projects group multiple chats; chat names and project assignment can be edited from Chat options. Selecting another drawing creates or reopens its own chat in the current project. Threads, project membership and drawing bindings persist in SQLite; message history uses the existing server-backed session ledger with the thread UUID.

Answers contain expandable drawing-analysis artifacts. Per-message spending, the global Saved answers disclosure, Takeoff & code check and reference-measurement tools are removed from the interface. Inference spending appears only in Spending, which aggregates actual request IDs across sessions and shows daily/model breakdowns. Unknown usage and unavailable rates remain unknown; a known subtotal is kept separate. Dataset browsing excludes uploaded files.

The new SQLite tables are additive. Existing answers, reviews, upload files and model-request history are retained. Usage aggregation tests cover duplicate events, mismatched responses and source separation. Chat tests cover independent thread sessions and project assignment. Browser checks cover project creation, thread switching, document binding and history after refresh.
