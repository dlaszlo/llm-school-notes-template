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
| Infographic | PNG; JPG on request; landscape A4 composition, portrait on request | A clear visual explanation that serves the chosen learning task |
| Presentation | Landscape A4 PDF; one slide per page | Brief context, prerequisite bridge, coherent progression and recap |
| Podcast | MP3 with a companion script; two fictional voices | Friendly conversation with an accessible opening, connected topic blocks, key questions and a closing synthesis |
| Printable study notes | Portrait A4 PDF with selectable/searchable body text | Connected explanation, examples, figures, recap and separate final answers |

These are separate requested outputs. An ingest does not automatically trigger a podcast, a slide deck or a printed packet. Existing precise SVG/code diagrams remain the appropriate source for dimensions, force directions, formulas and exact relationships; a generated image is chosen by learning value, not subject name.

## Infographic

Start with what the learner needs to recognize, explain, compare or do and which content must become visible. Select the form from that task and actual reading size, not from a preferred topology. This open repertoire offers examples, not an exhaustive taxonomy or subject mapping:

| Learning task | Possible visual form |
|---|---|
| Recognize something or identify parts | Annotated object/scene, cutaway, detail enlargement |
| Locate something in space | Map, plan, spatial section |
| Locate events in time or follow change | Timeline, parallel time bands, states over time |
| Compare | Matched views, comparison table or panels with the same criteria |
| Understand quantities, proportions or trends | Accurate chart, scale or part-whole diagram |
| Classify | Groups, hierarchy or set diagram |
| Follow a procedure or transformation | Steps, state transition, conditional branch or worked example |
| Understand why something happens | Explanatory scene or causal mechanism |
| Understand a connected system | Hub-and-spoke, network, true cycle or mixed structure |

**OTHER / ELSE:** if none fits, identify the actual learning task and content nature, then justify a custom or mixed representation. If a new image adds no meaningful learning value, reuse a suitable existing visual or prefer the text/table without generating an image. A mixed view needs a clear main purpose and explicit connections between its parts; more views are not automatically better. [Research basis and limitations](media-design-rationale.md).

1. Record a compact plan before paid generation: learning goal/main message, chosen form and reason, composition/reading order, exact labels, essential claims with source locations and conditions, size, context and format-specific checks. Detail only fields relevant to the task. Compare an available accepted example for the same learning purpose without copying an unsuitable layout. Keep exact geometry, forces, dimensions, formulas and quantitative charts on checkable SVG/code foundations.
2. **Only where relationships matter:** identify their meaning, endpoints, directed/undirected nature and conditions. A hub with reciprocal exchanges is not automatically a cycle. A true cycle, path, hierarchy or complex network should reflect the evidence. Grouping must not sever meaningful relationships; split into panels only when this aids the task and their relationship remains explicit. Keep participants and notation consistent. Use no arrowhead for an undirected relationship, one at the receiving end for a one-way relationship, and separate labeled arrows for reciprocal flows with different meanings. Distinguish a part-label leader line, an order marker and a substantive relationship; none is a decorative arrow.
3. Fit essential content at the final reading size. Rich scenes can invite exploration when their details reveal lesson concepts and preserve focus. Do not invent historical or technical claims for appearance. If the core needs tiny type, resolve a narrower focus or natural split before spending; do not silently omit it. Historical standalone media needs the verified time/place on the deliverable. Landscape remains the default, portrait follows the request; neither dictates composition.
4. Generate with the configured provider/model and inspect the actual returned image against the learning goal and evidence. Check labels, accents, numbers, core coverage, conditions and meaningful visual claims. Apply form-specific checks: part identification, spatial placement, time order, comparison criteria, quantities/scales or procedural steps. Separately assess whether the chosen form supports the learning task; do not demand a relationship network from an image serving another purpose.
5. **Verify every actual arrow individually:** its meaning, start, arrowhead location/direction, target, label and condition. Check reciprocal directions separately; look for missing, extra, reversed, incorrectly double-headed or misconnected arrows. Source evidence establishes substantive relationships; a labeling pointer must identify the correct part. Record these checks in the existing evidence record. OCR and prompt compliance alone do not establish visual correctness. Inspect the whole image, relevant details, phone appearance and actual A4 size; report any zoom requirement honestly.
6. Repair only identified errors within the shared limits, preserving correct parts and rechecking the entire changed image. If the plan was flawed, correct it before retrying; do not blindly repeat the same request. On acceptance, stop. Synchronize the embed, alt text, caption, prose, evidence record and hash-bound `image-description` comment with the observed final image. Reuse accepted suitable assets before paying for another.

Record learner feedback with the actual prompt and output in the existing private evidence record. Distinguish a flawed plan from a generator failing to follow it. Carry reusable lessons into the shared prompts without hard-coding a private learner example or promising guaranteed first-attempt success. A generation/repair limit is a ceiling, not a quota to consume.

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

## Visual decision, prompt construction and acceptance

The author chooses the content before invoking the image model. Start from the current lesson and its scope record: goal, required core, prerequisite bridge, optional depth and source versions. Reuse an applicable decision; do not repeat curriculum retrieval for each banner or format. Read fresh requirement passages only when priority, depth or applicability remains uncertain. Scope and requirement hashes stay in the private record, not in the provider prompt.

Record a compact plan: goal; scope reference; decision (no new image/reuse/precise code/generated image); learning value; exact source locations and conditions; visible introduction; final mandatory labels and visual claims; example if useful; composition/reading order; optional motifs; production method; final size and QA. Keep exact geometry, numerical charts, forces and formulas in checkable code/SVG. A subject name alone never determines the medium.

Banner role preference: useful orientation/overview or characteristic cue; representative application, example or detail; related motif or understandable visual metaphor; topic-related decoration when nothing more useful fits. These are options, not a mandatory ladder or fixed fact count. Keep the wide, low shape and phone-sized main reading clear. Beautiful detail is welcome when it supports the topic; it must not imply unsupported geography, chronology or reconstruction.

For infographics, identify what the learner can recognize, explain, compare or do from the image. Context must be visible in the image itself: identify the object/system/text, the central question and indispensable terms before using them. A clause number, abbreviation or symbol is not an explanation. A correct but opaque picture fails. If the core cannot fit readably, narrow the visual focus or split into distinct useful figures before spending; preserve the full lesson in prose.

Use form-specific constraints only where relevant:

* Sequence: identify what the order means, actual stages, transitions and whether spacing is time-scaled. Chronology does not prove causation, improvement or a cycle.
* Contrast: use the same comparison criteria; distinguish typical cases, theoretical endpoints and extremes. Do not turn a continuum into a false binary or imply a numerical scale without data.
* Relationships: choose topology from semantic links, with endpoints, direction, labels and conditions. A hub exchanging with its neighbors is not a circular process. Check EVERY visible arrow, including unexpected ones.
* Grouping: identify membership or part-whole basis; preserve overlaps. Proximity does not imply causation or rank.
* Metaphor: name the intended correspondence and important misleading implications to avoid. Do not let decoration masquerade as a literal fact.
* OTHER: recognize the actual content and choose a justified novel or mixed representation, reuse, or no new image. Infographics need learning value; banners can be decoration.

Choose examples to teach recognition, transfer or limits. A verified case different from the concrete wording of an everyday principle can demonstrate generalization. The prompt supplies the checked situation, conditions, consequence and allowed conclusion; the image model must not invent a historical event, law, quote or number. A fictional explanatory case is explicitly identified as an example.

Construct one provider prompt in this order: purpose/use; visible introduction; exact mandatory text, claims and composition; optional motifs; style/size; relevant accuracy constraints. The provider never receives the full private profile, corpus, internal reasoning or responsibility for choosing lesson facts. Use [stage prompts](media-prompts.md) and the [shared executor](learning-image-execution.md).

Inspect the finished image independently of the intended prompt: can its declared learning task be completed without mentally supplying missing context? Check required depth, core and bridge; optional details must remain optional. Verify text, chronology, examples, conditions, anatomy/object identity and all actual arrows as relevant. Inspect full resolution, phone placement and A4 aspect/print size. A4 fit is not a claim of 300-dpi detail; record dimensions and zoom needs. Banners receive proportional checks but cannot use decoration to excuse a misleading period or object.

At the attempt bound, publish only the best usable reviewed candidate. A cosmetic imperfection can remain; essential factual/context/relationship defects cannot. Keep the suitable old image or supported text if no candidate passes. Record a numbered, self-contained follow-up question with the candidate, concrete defect, proposed change, retained good content, current delivery state, actual cost, estimated next cost and exact requested extra calls/budget. Remaining money does not reset attempts.
