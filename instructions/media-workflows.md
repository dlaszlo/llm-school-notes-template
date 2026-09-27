# Shared learning-media workflows

These instructions apply to the media role (Mantis or equivalent) and to the ingest role (Drax or equivalent) when it creates an authorized inline infographic. They extend [AGENTS.md](../AGENTS.md); they do not establish a live bot deployment, credentials, publication authority or a spending allowance. Local configuration selects the learner, language, available providers, voices and protected delivery destination. Use the [reusable prompts](media-prompts.md) for the current stage and the [handoff contract](media-handoff.md) when another role executes the work.

## Decide the learning task before generating

Read the requested current notes, their source versions, the relevant profile settings and the existing learning-scope decision. Inspect source images on which a claim depends. The title or chapter summary alone is not enough. Select relevant curriculum passages within the bounded retrieval rule; never add a whole syllabus because its file is available.

Make one short content plan: topic and context, learning goal, prerequisite bridge, essential claims/relationships with source locations and conditions, important why/how/when questions, optional enrichment, deliberate omissions and unresolved evidence. Prioritize what was taught and what understanding requires. Keep notebook content, teacher material, textbook additions and illustrative examples distinguishable. A polished output cannot resolve a source uncertainty.

Do not assume a fixed subject taxonomy. Decide which context dimensions the actual topic needs: time/place/causes, a problem and its notation, a system and its behavior, a practical starting state and evidence-supported steps, or other relevant dimensions. Explain necessary terms before relying on them. A model's successful answer is not proof that a learner understands the material; use actual learner feedback when supplied, without storing grades or behavioral profiles.

For historical topics, apply *Orient historical learning in time and place* in [AGENTS.md](../AGENTS.md): put verified time and geographical context in the opening, adapted to each format. Distinguish the historical date from the lesson date. A banner may repeat this context where readable.

## Outputs

| Format | Default deliverable | Learning structure |
|---|---|---|
| Infographic | PNG; JPG on request; landscape A4 composition, portrait on request | One visible hierarchy of the essential parts and relationships |
| Presentation | Landscape A4 PDF; one slide per page | Brief context, prerequisite bridge, coherent progression and recap |
| Podcast | MP3 with a companion script; two fictional voices | Friendly conversation with an accessible opening, connected topic blocks, key questions and a closing synthesis |
| Printable study notes | Portrait A4 PDF with selectable/searchable body text | Connected explanation, examples, figures, recap and separate final answers |

These are separate requested outputs. An ingest does not automatically trigger a podcast, a slide deck or a printed packet. Existing precise SVG/code diagrams remain the appropriate source for dimensions, force directions, formulas and exact relationships; a generated image is chosen by learning value, not subject name.

## Infographic

1. Choose one focused learning goal and a structure that makes its priorities visible. Specify exact labels, reading order, groups and meaningful relationships. For a directed diagram, enumerate every node, edge direction, edge label and condition before writing the image prompt. Decorative arrows are not meaningful relationships.
   Before paid generation, record the main takeaway, semantic structure, chosen composition and reason, orientation, and exact context line. Compare an available accepted example for the same task. Choose a layout by meaning: one shared system usually needs a single connected diagram; a sequence needs ordered steps; a comparison may benefit from panels. Do not prescribe a card grid merely because it is easy to generate or check. When content contains a cycle, process, directed relationships or connected groups, preserve that connected structure visibly in one coherent diagram. Grouping may clarify roles but must not sever meaningful connections. Split into panels only when it improves understanding and the relationship between panels remains explicit. Do not invent a closed cycle where the evidence shows only separate exchanges. Keep repeated participants in stable positions; simplify arrow routing with spacing and parallel paths instead of flattening every direction to the right and swapping sender/recipient positions. These are design choices, not a universal ban on panels or repeated nodes: use them when they serve the learning task and explain why. Landscape remains the default, portrait follows the request; neither orientation requires a particular composition.
2. Fit the essential content at the final reading size. If it requires tiny type, propose a narrower focus or natural separate outputs before spending money; do not silently omit essential content.
3. Generate with the configured image provider/model and directly inspect the entire returned image against the plan and the underlying evidence. Check accents, names, numbers, arrowheads, lost conditions and invented details. Separately check whether the main relationship is visible as a whole, the context is sufficient, and the reader can trace a connection without mentally combining disconnected panels. Compare with the accepted reference at the same reading size. Correct individual arrows are necessary but do not establish a good learning design. OCR assists label checks but does not establish visual correctness.
4. Repair only identified errors within the shared limits, preserve correct parts where possible and recheck the entire changed image. For an accepted inline image, synchronize the embed, alt text, caption, prose, evidence record and hash-bound `image-description` comment. Describe the observed final image, not the intended prompt.

Record learner feedback with the actual prompt and output in the existing private evidence record. Distinguish a flawed plan from a generator failing to follow it; repair the plan before retrying. Carry the reusable lesson into these shared prompts, without hard-coding a private learner example or claiming guaranteed first-attempt success. Reuse an accepted suitable asset before paying for another.

## Learning cues in banners

A requested banner can aid orientation and recall with a short title, one relevant period/range, a recognizable location and a few meaningful visual motifs already explained by the lesson. For history, a concise subtitle may combine period and region/present-day location when supported. Label a narrower study period as such; do not imply that it is the civilization's entire lifespan. Prioritize legibility on a phone: omit secondary motifs or optional subtitle detail before shrinking the text. Do not turn the header into an infographic, a list of dates or a paragraph of definitions. Keep required time/place in the page opening even when the banner carries it.

A banner may be a rich, inviting scene worth looking at: connected, accurate lesson motifs can reward looking more closely and cue ideas encountered in the text. Minimalism is not mandatory; keep the text short and the main focus clear, and do not fill detail with unsupported historical claims. Choose motifs for learning value, not generic spectacle. A drawn river landscape, tool or building can cue a concept; its generated details are not evidence for authentic geography, architecture or chronology. An asserted map, inscription, dated object or reconstruction needs the normal source and visual checks. Keep provider names, costs and generation metadata in evidence/comments. This guidance applies to the next authorized banner creation or revision, not an automatic paid replacement of existing headers.

## Presentation

Plan the whole storyboard first. A requested slide count includes title, transition and recap pages. Without a requested count, use about 3-5 pages for a short topic, 6-10 for an ordinary summary and at most 12 automatically. A longer deck needs an explicit request. Do not add filler, obligatory separate title/thank-you slides or unreadably dense pages to meet a count.

Each storyboard entry records its title, one coherent learning point, exact visible text, essential-claim IDs/source locations, visual structure and connection to adjacent pages. The deck must be understandable without a presenter or hidden speaker notes. Check complete coverage, prerequisite order and consistency before paid image generation. If the requested count cannot hold the core readably, resolve scope before generating.

Give every slide prompt the same visual specification: A4 orientation, margins, title position, text hierarchy, consistent concept colors and illustration conventions. Generate and inspect slides individually; retain accepted slides while repairing a failed one. Assemble only accepted pages in storyboard order. Render and inspect every page of the final PDF, including size, sequence, clipping, labels and continuity. A PDF made of images is not an editable PPTX.

## Podcast

Support one friendly conversational format; do not introduce an unnecessary debate or style selector. Both fictional speakers may ask and explain. Avoid forced disagreement, repetitive praise and a rigid question-answer pattern on every line. Use the profile's language; retain language-learning examples in their relevant language with an accessible explanation.

Before TTS, plan the topic blocks and approximate duration, then write and verify the complete dialogue. The opening must orient someone who has not read the wiki or heard another episode: name the topic and broader subject, establish the central question and explain why it matters. Aim to make this clear within roughly the first half-minute without imposing a rigid spoken timer. Choose the necessary spatial, historical, conceptual or practical background from the actual lesson. Do not start in the middle of an explanation or assume advanced vocabulary.

Build prerequisites, connect the blocks and discuss the important questions and reasoning after explaining each substantive topic. Small recall pauses may help but must not turn the dialogue into an exam. Describe meaningful visual relationships audibly; do not rely on phrases such as "this arrow here". Clearly identify a made-up illustrative example as an example. End by connecting the key ideas and returning to the opening question.

Without a requested duration, start around 3-5 minutes for a short topic or 5-8 for an ordinary summary; do not automatically exceed 10 minutes. These are planning estimates, not filler targets; measure the final recording. Keep speaker-to-voice assignments stable. Verify text fidelity, pronunciation, speaker identity, joins, pace and intelligibility across the complete recording. Transcription is supplementary evidence, not direct listening. Record an audio-check limitation honestly; do not mark unlistened audio fully verified.

## Printable notes and A4 checks

Apply *Printable study notes* in `AGENTS.md`: a short topic orientation, needed concepts, connected explanations, useful worked examples and recap, then self-check questions with numbered answers in a separate final section. The paper must be sufficient for the core learning task without links, hidden comments or an external presenter. Preserve editable text input and source/asset versions; do not generate body-text pages as images.

Landscape A4 is 297 x 210 mm; portrait is 210 x 297 mm. Infographics/slides keep at least 10 mm safe margins; prose handouts start with at least 15 mm margins and about 11-12 pt body text. Inspect readability at actual print size and grayscale where relevant. Fit images without distortion or clipping essential content. Document intended physical size and actual pixel dimensions. A nominal 300 dpi landscape A4 raster is about 3508 x 2480 pixels; upscaling or changing density metadata does not create detail. An infographic remains a standalone image; no compulsory PDF conversion is implied.

For a handout, also check extracted text/reading order, accents, formulas, numbering, question-answer agreement, page breaks and figure/caption placement. Estimate length from the task rather than imposing the slide cap on prose. Never shrink type or omit necessary steps to fit a requested count; propose a natural scope adjustment. Recheck changed pages and overall sequence after repair.

## Acceptance, repair and delivery

The checked content plan is the acceptance contract. Missing essential content, false facts, reversed relationships, lost conditions, clipped or unreadable text and unresolved required checks prevent a ready state. Pure taste differences do not justify another paid call once the requested learning purpose and appearance are met.

Use at most the initial generation plus two repairs per infographic, slide or faulty speech segment; for a handout use the initial layout plus two targeted repair rounds as the starting bound. Enforce a configured whole-request cap covering all outputs and paid reviews as well as per-unit attempts. The executor must track these durably; a prompt reminder is not a cost control. Changing role, filename, provider or session never resets counts. Preserve accepted components. An ambiguous provider response requires reconciliation before another potentially duplicate charge.

Stop on acceptance, an exhausted bound or unresolved essential evidence. A failed essential component leaves the deliverable a draft with a precise defect report; do not insert it as finished learning material. An optional image failure need not block supported notes. Store the source versions, scope plan, script/storyboard, exact prompts, hashes, checks, limits and actual costs in the authorized private record. A learner-facing version/date helps identify outdated printed or downloaded material.

Large audio/PDF/image artifacts use the configured protected media store, such as a verified per-learner Drive folder. Small inline wiki images may remain in Git. Do not infer access from a pasted folder URL, make a file public or alter sharing automatically. A cloud reviewer must be able to inspect the same artifact or report it as unavailable. A relevant source change makes the derivative due for review; do not silently replace a different version behind a printed label.
