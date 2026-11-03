---
name: ai-sindan-art
description: Create or revise the sixteen travel-themed AI SINDAN type illustrations with consistent characters, palette, and composition. Use for this project's type art and naming, not for diagnoses or unrelated image requests.
---

# AI SINDAN travel illustrations

Work in the AI SINDAN repository. Read its AGENTS.md. The canonical copy of this skill is `skills/ai-sindan-art/`; an installed copy should locate the repository from the current workspace, not assume a user's absolute path.

Read `skills/ai-sindan/assets/journey-types.json` for the stable four-letter codes, Japanese names, plain-language summaries, scene prompts, and alt text. Read [references/prompts.json](references/prompts.json) for the shared art direction and exact generation prompts. Names and artwork are presentation, never inputs to classification.

Use the built-in image generation tool, one call per asset. No API key or CLI fallback is needed. Only send the generic scene and art direction to the image tool; private report text, excerpts, and personal data are not art references.

For an existing set, inspect `skills/ai-sindan/assets/journey/SGIC.png` as the style and character reference. Use its local path as a reference image for each new scene, rather than chaining the last generated image; that avoids cumulative style drift. Keep the ochre-cloaked traveler, teal hat, cream robot, opaque cream paper background, restrained gouache texture, full figures, and readable silhouettes. Vary actions and props to match the type's scene. No in-image labels or text; the HTML supplies names accessibly. All types deserve the same visual appeal and equal partnership, with no rank, competence, or moral hierarchy.

Inspect each result for the intended scene, character consistency, unwanted text, and obvious anatomy issues. Correct a failed image with a targeted image-generation edit. Save every approved original in `skills/ai-sindan/assets/journey/<CODE>.png`; keep replacements as versioned siblings until deliberately selected. Record the exact prompt and reference code in `references/prompts.json`.

For HTML delivery, run `scripts/export-jpeg.ps1 -AssetDirectory <repo>/skills/ai-sindan/assets/journey`. This only resizes and encodes delivery copies; it does not redraw artwork. PNG originals remain intact. The renderer embeds the JPEGs, so the fixed report remains standalone. Run `python skills/ai-sindan/scripts/semantic.py render --output output/semantic` after integration. Preserve report.json, original analysis dates, unknown/mixed classifications, and the privacy boundary of share-profile.json. Verify all sixteen images and alt texts, the current-type image, and legacy fallback. Keep the page compact.

Track code, art, and this skill in local Git. Keep generated reports and private data ignored. Do not publish or push without a request.
