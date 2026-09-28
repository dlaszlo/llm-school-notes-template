# Precise diagrams and rendered illustrations

Use this guide when an authorized visual depends on precise geometry, notation, data or motion. It extends [media workflows](media-workflows.md); it does not require a specific renderer, a new installation or an infographic for every topic.

## Choose the representation

| Learning need | Possible tool | What it does not establish |
|---|---|---|
| Small exact construction, vectors, notation | Authored SVG or typesetting such as TikZ | Correct inputs, conventions or source coverage |
| Quantitative relationship or data | A plotting library with explicit data/functions | Correct units, domain or interpretation |
| Relationships, hierarchy, grammar tree | Graphviz or a suitable existing diagram tool | Correct edges or pedagogically meaningful layout |
| Parametric shape, section, projection | CAD, for example FreeCAD | Valid design for every parameter set or compliance with a drawing standard |
| Spatial illustration or prescribed movement | A renderer such as POV-Ray | Physical dynamics, collision-free contact or engineering validity |

These are compatible options, not subject categories. Use the least complex method that makes the important relationship clear and checkable. A supplementary generated infographic may help in any subject; preserve the notebook's precise teaching diagrams separately. Rendering every simple force diagram in 3D adds no automatic learning value.

## Verify the meaningful detail, regardless of tool

1. Identify what the learner is supposed to infer and which visible detail carries that claim. Decide which parts must be exact and which may be simplified. An icon can be schematic, but cannot contradict the function it is used to explain. Simplification must not remove the lesson's subject.
2. Establish the source, parameters, units, relevant drawing convention and applicability. Do not invent an unspecified standard or dimensional tolerance. A model library or a renderer is not the authority for the lesson.
3. Check the actual constructed result against the claim using the appropriate independent method: calculations, geometric intersections, graph structure, source comparison or the applicable notation rules. Merely reading back supplied parameters is insufficient. Choose a check whose failure would expose a meaningful error.
4. Inspect the final rendered/exported view too: projection, cropping, line styles, labels, attachment points, scale and readability. A valid model can have a misleading picture, and a beautiful picture can have an invalid model. Inspect composite graphics after assembly.
5. Record source/model versions, meaningful checks, final artifact hashes and remaining limitations in the existing evidence record. Distinguish a sampled check from a full validation. Never claim manufacturing, structural or standards certification from an educational illustration.

Examples: if a gear's profile or engagement is taught, check the actual tooth geometry and relevant parameters, including the generator's limitations; a gear-shaped star is insufficient. For a thread, identify the intended profile and axial spacing, handedness and number of starts where relevant; a decorative spiral is not a specification. For a wall or section, verify the source's line/hatch convention and what it denotes; a software pattern name does not establish its meaning. The same principle applies to axes, circuit symbols, chemical bonds, grammatical relationships and other meaningful details.

## Animation and runtime

Animate only when change, sequence or spatial behavior adds understanding. Define whether it is a prescribed sequence of poses, a kinematic model or a physical simulation. State a consequential simplification for the learner; keep software metadata in evidence. A pauseable animation should have a useful static counterpart for printing and inaccessible playback.

Check relevant constraints across the generated sequence numerically where possible. Inspect initial/final states, extrema, contacts and other critical transitions, then the final playback. Sparse frame sampling alone does not validate every intermediate state. Record exactly which frames or invariants were checked and distinguish technical playback testing from a person actually watching it.

Measure with a small representative case before committing to a large run. Record tool/version, hardware or VM resources, resolution, quality, thread count, number of frames and wall time; separate model construction, rendering and encoding where available. Repeat short cases and report their spread. Do not extrapolate a trivial scene into a guaranteed cost for a complex one. A VM comparison uses the same source revision and settings, then separately tests any proposed resource change.

The [optional pilot](../examples/technical-visuals/README.md) provides checked example sources, measured limits and previews. It is not an automatic installation or a requirement to adopt those tools.

## Human feedback

When the user asks to review samples, keep a discoverable pending list in the existing planning/review record: artifact/link and version or hash, machine checks separately, human status and the specific response when it arrives. Until the user explicitly says they viewed it, record it as not yet viewed; silence, time passing or a general acknowledgment is not visual acceptance. Viewing and accepting are separate states. This tracks a requested review; it does not add a universal approval gate to authorized note work.
