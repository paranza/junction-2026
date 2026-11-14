# Lift landing doors in visual door counts

14 November 2026. The user reported a missing lift door in a raster-plan chat.

The original Carbon answer returned 35 door assemblies. Its own warning identified the lift entrance but excluded it for lacking a leaf/swing-arc symbol, explicitly giving 36 if lift shaft doors were included. This was a classification/scope error, not a failure to notice the lift.

The general visual-answer and inventory instructions now include clearly depicted lift landing entrances and sliding-door symbols without requiring a hinged leaf or swing arc. They still exclude a shaft rectangle or the word Lift alone, and leafless passage openings. This rule uses drawing semantics; there is no filename, room-number or expected-count lookup. Prompt/inventory revisions invalidate old analyses without rewriting saved answers.

Live checks used the same Carbon policy as the original case: high image resolution, medium thinking, 24,000-token cap, 600-second timeout and no small-image crops. The original question was unchanged. The complete uploaded drawing returned **36**, with a lift-door evidence region. Two independently authored controls returned **two doors** for one hinged door plus a visible lift landing entrance and **one door** for one hinged door plus a closed labelled shaft. Each used one actual model request in an isolated development runtime. Production was not used for these paid checks.

The controls establish this distinction on three examples, not universal recognition accuracy. Lift-door labels alone do not justify automatic additions. The original 35-count answer and its audit trail remain saved.
