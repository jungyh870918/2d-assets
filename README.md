# 2D ART FACTORY

Mass-produce game art from purchased and CC0 modular 2D assets **without touching the
originals** — by combination, palette, and layer rules only.

One line: **nothing is drawn here. Things are combined, verified, and wired into the engine.**

```
git clone https://github.com/jungyh870918/2d-assets.git
```

---

## 0. The primary reader of this document is not a human

This README is written assuming an **LLM agent working in a different project on a different
machine** reads it. If that is you, you should be able to decide all three of these on your own,
before asking a human anything:

1. **Is my problem this repository's problem?** (§1)
2. **What can I actually run with this clone right now?** (§2)
3. **What may I order, and what will be refused?** (§6, §9)

Once you have decided, **explain your reading to the human.** That is the order — understand
first, then explain. §10 gives the template to fill in. Fill it rather than improvising a summary.

> **Language note.** This README is English. `CLAUDE.md`, `00_DOCS/`, `tools/README.md`, and all
> generated reports are **Korean** — they are working documents for the maintainer. Everything an
> outside agent needs to make the three decisions above is in this file. The machine-readable
> artifacts (`*.json`) are language-neutral; prefer them over the prose reports (§7).

### Reading order for an agent

| Step | Read | Purpose | Needs source assets |
|---|---|---|---|
| 1 | This README §1–§2 | Applicability · what a clone contains | No |
| 2 | `02_CATALOG/CAPABILITIES.md` | **What can be ordered right now** (auto-generated facts) | No |
| 3 | This README §3–§4 | Concept model · input contract | No |
| 4 | One scenario from §6 | Execution recipe | Depends |
| 5 | `CLAUDE.md` (Korean) | Absolute rules when modifying this repo | No |
| 6 | `00_DOCS/DIRECTOR_CONTEXT.md` (Korean) | Who decides · why the boundaries are where they are | No |

**Run this one command first** — it works with no source assets present:

```bash
python3 tools/capability_sheet.py && cat 02_CATALOG/CAPABILITIES.md
```

That is the capability sheet. It is more current than every document below it, because no human
writes it — it is recomputed from the catalogs and license records on every run.

---

## 1. Thirty-second triage — is this your problem?

### What this repository does

- Takes existing **modular parts** (body / hair / torso / legs / feet / weapon …) and combines
  them by rule into a **character population**. Give it a seed and the result reproduces
  byte-for-byte.
- **Verifies** the result against facts only (dimensions · alpha · duplicates · source immutability
  · reproducibility · licensing).
- **Wires it into Unity** (Sprite Library / Sprite Resolver / AnimatorController / prefab builders).
- **Propagates license and attribution** all the way to the output — commercial eligibility and
  author credits ride along into the Unity manifest and the consumer package.

### What it does not do

| Not done | Why · instead |
|---|---|
| Draw new art | No generative image models. Feeding purchased assets to an AI is an invariant violation (§9) |
| **Decide which result is better** | Aesthetic judgement belongs to a human. That is why there is deliberately no `picks/` or `approved/` folder |
| Split a finished character sheet into parts | `composed_sheet` packs cannot be combined. They are scanned and recorded only (§3.3) |
| Generate tilemaps / levels / backgrounds | Environment packs are scanned only — `generation_mode: unsupported` |
| Make your licensing decision for you | With no license record, generation is **refused** (§9) |
| Set the game's art policy | The Factory supplies capability; the game decides what to use (§8) |

### Triage table — find your row

| Your situation | Verdict | Go to |
|---|---|---|
| Parts are separate per-slot PNGs sharing one origin and canvas | **✅ Exactly this** | §6-B → §6-A |
| You want a pack this repo already catalogs (LPC / CC0) | **✅ Ready now** | §6-A |
| You want 20 deterministic NPCs in a Unity game | **✅ Supported** | §6-C, §8 |
| You only have finished character sheets (all frames in one `walk.png`) | **⚠️ Not combinable** | §6-D |
| It is a background tileset / interior pack | **⚠️ Scan only** | §6-D |
| You want concepts, a protagonist, a boss, or a UI language | **❌ Wrong repo** | §11 art-studio |
| "Generate sprites with AI" | **❌ Refused** | §9 |
| "Pick the prettiest combination" | **❌ This repo does not pick** | §10, ask the human |

> **The dividing line**: this repository handles **populations** (villagers · mobs · soldiers ·
> color variants). It does not handle **identity** (protagonist · boss · landmarks · UI).
> Shipping purchased-pack parts as-is means the pack author, not you, set your game's art
> direction. Prototype · placeholder · machine verification is the safe range of use.

---

## 2. What a clone gives you — and what it does **not**

**Every later judgement is wrong if you miss this.**

This repository ships the **machine**, not the **material**.

```
You get ✅                          You do not get ❌ (.gitignore)
────────────────────────────       ────────────────────────────
tools/          full pipeline       01_SOURCE/**    original art (licensing · size)
00_DOCS/        contracts, licenses 05_GENERATED/** outputs (regenerable)
02_CATALOG/     pack catalogs       06_UNITY_EXPORT/** exported packages (regenerable)
03_PALETTES/    palette definitions
04_RULES/       generation rules
CLAUDE.md       working instructions
```

### Why this layout is in your favour

`02_CATALOG/*.json` **is committed.** A catalog is not art — it is a list of filenames,
dimensions, sha256 hashes, and inference results — so it carries no redistribution problem.
Therefore an agent can:

- read everything a pack makes possible **while owning none of the assets**, and
- later prove **byte-for-byte** that a copy it obtained is the same pack that was cataloged.

```bash
# Works immediately with no assets — regenerates the capability sheet
python3 tools/capability_sheet.py

# List the source files the catalog expects, with hashes, to check against your own copy
python3 -c "
import json
c = json.load(open('02_CATALOG/lpc_ulpc-generator_phase1.json'))
print('pack root:', c['pack']['root'])
for e in c['entries'][:5]:
    print(e['sha256'][:12], e['bytes'], e['path'])
print('...', len(c['entries']), 'entries total')
"
```

### What happens if you run it without assets

It does not silently produce something wrong. It names the exact file and stops.

```
ap2d.compose.ComposeError: 소스 에셋이 없다:
  01_SOURCE/characters/lpc_ulpc-generator_phase1/spritesheets/body/bodies/male/walk.png
```

(`소스 에셋이 없다` = "source asset missing".)

| Command | On an asset-less clone |
|---|---|
| `tools/capability_sheet.py` | ✅ Works |
| `tools/tests/test_pipeline.py` | ⚠️ Partial — most tests build their own fixtures; 7 that need real sources fail and 44 skip (§13) |
| `tools/scan_pack.py` | ❌ Nothing to scan |
| `tools/run_pipeline.py` | ❌ `ComposeError: source asset missing` |
| `tools/source_fingerprint.py` | ❌ `01_SOURCE` does not exist |

### So there are exactly three ways to get material

1. **Obtain a pack this repo already catalogs.** The download URL is the `source_url` field in
   `00_DOCS/licenses/<pack>.md`. Unpack it as-is into `01_SOURCE/<domain>/<pack>/`.
2. **Add your own pack** — §6-B.
3. **Add parts you made yourself** — any origin works, as long as the input contract (§4) holds.

---

## 3. The concept model — how this machine sees the world

Know these four and you can interpret almost every field in every report.

### 3.1 Every capability is three-valued — `yes` / `no` / `unknown`

**`unknown` is never rounded up to `yes`.** "Not found" and "not present" are different claims.

Example: the HD Survivor pack encodes 8 directions as **rows inside a sheet**, so filenames alone
cannot reveal whether a direction axis exists. Its `direction_axis.present` is `unknown`, not `no`.

> Agent rule: when a report says `unknown`, do not summarize it as "none".
> Report it to the human as **"not proven"**.

### 3.2 `composable` — the definition of combinability

```
composable = parts_separable ∧ pre_aligned ∧ animation_compatible
```

| Capability | Meaning |
|---|---|
| `parts_separable` | Do parts exist as separate per-slot files or cells? |
| `shared_canvas` / `shared_cell` | Do the layers that will overlap share a canvas, or a logical cell? |
| `pre_aligned` | Can they be stacked without coordinate correction? |
| `shared_origin` | Do they share an origin? |
| `animation_compatible` | Do animations and frame counts match across slots? |
| `directional` | Was a direction axis actually read? |
| `origin_policy` | The basis for the pivot (`shared_canvas` / `logical_cell` / `unknown`) |

These are **computed** by the scanner, not declared by a human.

### 3.3 `generation_mode` — where packs diverge

| Mode | Meaning | Combinable | Unity consumption path |
|---|---|---|---|
| `modular_composition` | Pick parts and compose | **Yes** | Sprite Library (runtime) or baked sheets |
| `composed_sheet` | Already-finished character sheet | **No** | Animator + sheet slicing, on the game side |
| `unsupported` | Not a character-generation target (tilesets etc.) | No | — |

Feeding a non-combinable pack to the generator produces an **explicit SKIP**, not an incidental
error:

```python
from ap2d import catalog, generate
generate.generation_status(catalog.load_catalog("02_CATALOG/<pack>.json"))
# -> {"status": "skipped", "generation_mode": "composed_sheet",
#     "reason": "composed_sheets_only", "capabilities": {...}}
```

**This is not a failure.** Do not report it to a human as one — report that the pack was never a
combination target, and give the `reason`.

### 3.4 Physical layout ≠ logical topology

Two packs stored completely differently run through the same pipeline:

| | CC0 (vector cartoon) | LPC (64px pixel art) |
|---|---|---|
| Physical unit | 1 PNG = 1 frame | 1 PNG = a (direction × frame) sheet |
| Coordinates | `(slot, asset, animation, frame)` | `(slot, asset, animation, direction, frame)` |
| Resolve | Open file, crop by animation bbox | Open sheet, crop by logical cell |

`compose.resolve_layer()` is the **single place** that absorbs this difference; after it, the
compositing loop is identical code for both packs. That is why "any origin works as long as the
contract holds" is true rather than aspirational.

---

## 4. Input contract — can your assets enter?

The checklist an agent uses to evaluate a **new pack, commissioned parts, or self-made parts.**
Satisfy it and the pipeline runs regardless of the pack's style or origin.

| # | Requirement | If violated |
|---|---|---|
| 1 | **Separate PNG per slot** (or regular sheet cells) | Falls to `composed_sheet`; not combinable |
| 2 | Overlapping parts share a **logical cell and origin** | `pre_aligned: unknown` → `composable: no` |
| 3 | Animation names and frame counts **match across slots** | `animation_compatible` drops (declare `allow_subset` for partial) |
| 4 | **Z-order declared by the source** (or stated in the rule) | Humans transcribing it get it wrong |
| 5 | Colors follow a **ramp structure** | Palette-swap quality is not guaranteed |
| 6 | `00_DOCS/licenses/<pack>.md` **frontmatter exists** | The generator refuses to start |

Required frontmatter fields (`REQUIRED_FIELDS` in `tools/ap2d/licensing.py`):

```markdown
---
pack: <must equal the folder name under 01_SOURCE>
license: CC0-1.0
commercial_use: yes        # yes / no / unknown
modification: yes          # "no" makes combination itself a license violation
redistribution: yes
ai_training: yes
credit_required: yes       # attribution obligation — a separate axis from commercial_use
pipeline_approved: yes     # anything but "yes" blocks the generator
acquired: 2026-08-16
source_url: https://...
---
```

How license state affects the pipeline:

| State | scan | generate | export | Commercial release |
|---|---|---|---|---|
| `pipeline_approved: yes` + `commercial_use: yes` | ○ | ○ | ○ | ○ |
| `pipeline_approved: yes` + `commercial_use: no` | ○ | ○ | ○ | **✗** |
| `pipeline_approved: no` / `modification: no` / no record | ○ | **blocked** | — | ✗ |

`commercial_use: no` is **not** a hard gate on generation. Instead
`commercial_release_eligible: false` is computed and travels **all the way through** —
catalog summary → generation.json → Unity manifest → validation report — with a warning banner
on the reports.

> **Attribution is a separate axis from commercial use.** `commercial_use: yes` does not waive
> credit. LPC is `commercial_use: yes` **and** `credit_required: yes`; shipping it without author
> credits violates CC-BY / OGA-BY. The credit lines travel into the Unity manifest and are copied
> into the consumer package as `ATTRIBUTION.md` (§8).

---

## 5. The six pipeline stages and their outputs

```
01_SOURCE  ──(scan)──>  02_CATALOG  ──>  CAPABILITIES.md   "what can be ordered"
                            │
        03_PALETTES + 04_RULES
                            │
                        (generate)          seed-deterministic
                            ↓
                       05_GENERATED  ──>  <profile>_brief.md   "what was done"
                            │
                        (validate)
                            ↓
                      06_UNITY_EXPORT
                            │
                    (export_consumer_package)
                            ↓
                    a separate Unity game project
```

All at once:

```bash
python3 tools/run_pipeline.py 04_RULES/<rule>.json
```

Stage by stage:

| Command | Does | Writes |
|---|---|---|
| `tools/scan_pack.py <pack dir>` | Scan sources, infer structure | `02_CATALOG/<pack>.json`, `.summary.md` |
| `tools/capability_sheet.py` | Roll up packs, palettes, rules | `02_CATALOG/CAPABILITIES.md` |
| `tools/generate_characters.py <rule>` | Seeded combination + compositing | `05_GENERATED/characters/<profile>/<seed>/` |
| `tools/make_contact_sheet.py <profile>` | One sheet to eyeball | `05_GENERATED/reports/<profile>.png` |
| `tools/validate_generated.py <rule>` | 10 checks + distribution observation | `..._validation.{json,md}` · `..._attribution.md` |
| `tools/order_brief.py <rule>` | One-page reply | `..._brief.{json,md}` |
| `tools/export_unity.py <rule>` | Unity package (baked) | `06_UNITY_EXPORT/characters/<profile>/` |
| `tools/export_unity_runtime.py <rule>` | Unity package (Sprite Library) | `06_UNITY_EXPORT/runtime/<profile>/` + `ATTRIBUTION.md` |
| `tools/export_consumer_package.py <Assets path> --profiles <p>` | Copy into an external Unity project | consumer `Assets/ArtFactory/` |
| `tools/tests/test_pipeline.py` | Full test suite | 206 tests |
| `tools/source_fingerprint.py` | Detect source tampering | tree sha256 |

`run_pipeline.py` runs scan → generate → contact sheet → export → validate → brief, then
regenerates `CAPABILITIES.md`. **The brief is written even when validation fails** — what failed
and why is section ⑥ of the brief.

---

## 6. Execution recipes by scenario

### A. I am a game project's agent and I need an NPC population

```bash
# 1. Read what is possible (no assets required)
python3 tools/capability_sheet.py && cat 02_CATALOG/CAPABILITIES.md

# 2. Pick a pack with composable: yes, obtain it, unpack into 01_SOURCE
#    Download URL: the source_url field in 00_DOCS/licenses/<pack>.md

# 3. Copy an existing rule and make it yours
cp 04_RULES/lpc_phase1_population.json 04_RULES/mygame_villagers.json
#    Change at least: id · profile · seeds · slot allow/deny · the order block

# 4. Run it
python3 tools/run_pipeline.py 04_RULES/mygame_villagers.json

# 5. Read the one-page reply and report to the human with the §10 template
cat 05_GENERATED/reports/mygame_villagers_brief.md
```

The rule fields an agent actually touches:

```jsonc
{
  "schema": "ap2d.rule/1",
  "id": "mygame_villagers",
  "profile": "mygame_villagers",          // becomes the output folder name
  "pack": "lpc_ulpc-generator_phase1",
  "catalog": "02_CATALOG/lpc_ulpc-generator_phase1.json",

  "order": {                               // a label. It blocks nothing
    "purpose": "order_response",           // self_verification | order_response
    "consumer": "unknown",                 // ← do NOT invent this. unknown is valid
    "request": "the request, verbatim or summarized",
    "not_done": [{"requested": "...", "reason": "..."}]
  },

  "animations": ["idle", "walk", "run"],
  "directions": ["south", "west", "east", "north"],
  "slots": {
    "body":  { "required": true,  "from": "body" },
    "hair":  { "required": false, "from": "hair", "none_weight": 0.2,
               "deny": ["hair_braid"] }    // narrow candidates with allow / deny
  },
  "layer_order": "by_z_pos",               // never transcribe z-order the source declares
  "unity": { "pixels_per_unit": 64, "filter_mode": "Point", "pivot": "BottomCenter",
             "frame_rate": 8 },
  "archetypes": [
    { "name": "villager", "seeds": { "from": 4001, "to": 4010 } }
  ],
  "global": { "no_duplicate_combinations": true, "deterministic": true }
}
```

> **Do not invent `order.consumer`.** Promoting a game repo's directory name or an abbreviation
> into a consumer identifier gives one game three names. If none was issued to you, `unknown` is
> the **correct** value.

### B. I want to add a new pack

```bash
# 1. Unpack as-is (never modify)
#    01_SOURCE/<domain>/<vendor>_<pack>_<version>/    + SOURCE.md
# 2. Write the license record — frontmatter required (§4)
#    00_DOCS/licenses/<pack>.md
# 3. Scan
python3 tools/scan_pack.py 01_SOURCE/characters/<pack>
# 4. Read the "generation capability" table in the summary FIRST
cat 02_CATALOG/<pack>.summary.md
#    composable: no means stop here — no rule is worth writing, and reason says why
# 5. Write a rule from the "parts found" table → continue at §6-A step 3
```

If the scanner does not recognize a part, add **only the word** to `BODY_PART_VOCAB` in
`tools/ap2d/catalog.py`. Anything not in the vocabulary stays `unknown` and is reported in the
summary's anomaly section — so **nothing is ever silently miscombined.**

Use an adapter only when the pack **supplies authoritative metadata itself** (LPC's
`sheet_definitions`, for example):

```bash
python3 tools/scan_pack.py 01_SOURCE/characters/<pack> --adapter lpc
```

**Pack-specific knowledge lives only in `tools/ap2d/packs/`.** Putting a branch like
`if "lpc" in pack_name` into a generic module **fails an AST test.**

### C. I want to wire it into a Unity game

```bash
# Factory side
python3 tools/export_unity_runtime.py 04_RULES/<rule>.json --seeds 4101 4102 --cell-size 64
python3 tools/export_consumer_package.py /path/to/MyGame/Assets --profiles <profile>
```

The rest happens **inside the consumer Unity project**, via the editor builders
(`SpriteLibraryBuilder` → library · prefab · `CharacterProfile`; `AnimationClipBuilder` → clips ·
controller). Game code knows exactly three types — §8.

```csharp
profile.SetMotion(animator, "walk");   // the only entry point for game code
profile.HasAnimation("run");
```

If the profile requires attribution, the package ships `Profiles/<profile>/ATTRIBUTION.md` and the
package README carries the credit lines. Putting them in your game's credits is your obligation,
not an optional extra (§4).

### D. My pack is `composable: no`

That is normal. It is not a failure. There are three options.

| `reason` | Meaning | What you can do |
|---|---|---|
| `composed_sheets_only` | Only finished sheets exist | Give up combination. Slice the sheet in Unity and drive it with an Animator. The catalog is still useful — animation, frame, and dimension lists |
| `atlas_only_no_individual_props` | Atlas only; parts not separable | Tilemap/environment use only. Not a character-generation target |
| `pre_aligned: unknown` | Alignment unproven | Re-request from the source author per the §4 contract, or separate the parts yourself into a distinct layer |

**Do not** add an exception to `compose.py` to force it through. `compose.require_modular()`
raising `UnsupportedModeError` is the design, not a bug.

### E. I do not like the result

There is no "make it better" knob here. Validation looks at **facts only**. The only thing you can
adjust is the **input**:

| Symptom (read it in the report's "observed distribution") | Where to act |
|---|---|
| Ten characters look like one | Check each slot's "used" count → loosen `deny` or widen the pack subset |
| One part keeps recurring (high most-common share) | Adjust `none_weight` / `allow`, widen the seed range |
| Everything is the same color | Add palette rules (`03_PALETTES/`) — note the current engine is multiply tint |
| The style does not fit the game | **Not a pipeline problem.** Change packs, or see §11 art-studio |

**Never add aesthetic criteria to validation.** A pass line built on tone distance or color
distribution throws away good results because of a number.

### F. I want to check what changed (regression)

```bash
python3 tools/source_fingerprint.py     # were the sources tampered with?
python3 tools/tests/test_pipeline.py    # 206 tests
python3 tools/run_unity_tests.py        # Unity EditMode + PlayMode (needs Unity)
```

Same seed + same rule + same catalog must give **byte-identical** results. A difference is itself
a bug signal.

---

## 7. How to read the outputs — which question, which file

Agents should parse **JSON**, not look at PNGs. Every `.md` is a human-facing rendering of the
same facts, and the `.md` files are in Korean.

| What you want to know | Human-readable | Machine-readable |
|---|---|---|
| What can be ordered now | `02_CATALOG/CAPABILITIES.md` | `pack.capabilities` in each `<pack>.json` |
| What is in this pack | `02_CATALOG/<pack>.summary.md` | `02_CATALOG/<pack>.json` (`entries[]`, `parts{}`) |
| What was done for this order | `05_GENERATED/reports/<profile>_brief.md` | `..._brief.json` |
| Did it pass | `..._validation.md` | `..._validation.json` (`checks[]`, `status`) |
| How to credit the authors | `..._attribution.md` | `attribution` block in the runtime manifest; `sources.json` per seed |
| What this character is made of | — | `05_GENERATED/characters/<profile>/<seed>/character.json` |
| Reproduction coordinates (what gets approved) | brief §② | `generation.json` (`rule_sha256` · `catalog_sha256` · `seed`) |
| What Unity will consume | — | `06_UNITY_EXPORT/runtime/<profile>/runtime_manifest.json` |

Schema identifiers: `ap2d.rule/1` · `ap2d.character/1` · `ap2d.unity_runtime/1` ·
`ap2d.attribution/1`

### The six sections of the brief

| § | Content | What an agent must be careful about |
|---|---|---|
| ① What was requested | Purpose · consumer · profile · pack | `self_verification` means it was not an external order |
| ② Reproduction coordinates | Rule/catalog sha256 · seed · palette | **Approval attaches here, not to the PNG** |
| ③ Technical verification | The 10 checks | **PASS = pipeline consistency. Not adoption, not release clearance** |
| ④ Release signals | `commercial_release_eligible` · credit obligation | If `false`, report the commercial restriction **explicitly** |
| ⑤ Observed distribution | How many candidates actually appeared | **Not a check.** No thresholds, no grades |
| ⑥ Not done / refused | With reasons | If empty, it is genuinely empty |

### The 10 checks (all factual; no aesthetic judgement)

Generated count matches · `01_SOURCE` unchanged (hash comparison) · no reference to assets absent
from the catalog · source assets exist · output files exist · image dimensions match · alpha
channel valid · no duplicate combinations · license restrictions propagated · same seed
regenerates identically.

---

## 8. The Unity consumer boundary (Export Contract v1)

### Game code knows exactly three types

`CharacterProfile` · `CharacterAppearance` · `CharacterView`. Label conventions, `SpriteResolver`
categories, slot z-order, sheet cell coordinates, and source paths are things the game **does not
need to know, and must not know.**

### Ownership — the exporter touches only its own

| Owner | Path | Exporter |
|---|---|---|
| Factory | `<pkg>/Runtime/`, `<pkg>/Editor/`, `<pkg>/Profiles/<p>/runtime_manifest.json`, `<pkg>/Profiles/<p>/ATTRIBUTION.md`, `parts/` | Overwrites |
| Consumer | `<pkg>/Profiles/<p>/Generated/`, **every `.meta`** | **Never deletes** |
| Game | `Assets/Game/**` | Does not know it exists |

> **Why the Factory never creates `.meta`**: GUIDs live in `.meta`. Delete one and Unity issues a
> new GUID, turning every serialized reference to that asset — scenes, prefabs, ScriptableObjects
> — into `Missing`. Re-export updates content in place so GUIDs survive.

### Two license axes, both of which reach the consumer

| Axis | Question | Where |
|---|---|---|
| `commercial_release_eligible` | May this ship in a commercial game? | Top of the manifest |
| `attribution` | Must authors be credited, and as what text? | Manifest `attribution` block + `ATTRIBUTION.md` in the package |

The manifest's `attribution.credits[]` holds credit lines ready to paste into a credits screen
(deterministic — sorted and deduplicated), so the consumer never has to reassemble author lists.
`attribution.report` is a **package-relative** path; a Factory path would be unreadable to a
consumer that has no Factory checkout. Packs with nothing to credit (CC0) get no file and
`report: null`, so the file's existence itself means an obligation exists.

### Missing appearances are never auto-substituted

If a re-export drops an appearance, the `parts/` textures (Factory-owned) are deleted while the
`Generated/` assets (consumer-owned) remain. The builder records them in
`profile.staleAppearances[]` and warns. It does not delete them and does not swap in a different
appearance. There is no animation fallback either — an unknown name returns `false`.

### The game owns its art policy

```
CharacterProfile      executable capability the Factory provides
      ↓
GameArtProfile        what this game allows (Assets/Game/**; the exporter knows nothing of it)
      ↓
NpcPopulationFactory  who gets which appearance/motion/direction — a pure decision function
      ↓
NpcDefinition[]  →  NpcPlacement  →  Spawner  →  CharacterView / Animator / Resolver
```

The Factory may offer 20 appearances while the game permits 2. That call belongs to the game.
Because `Generate()` never touches Instantiate, Transform, or Animator, **a population can be
verified without a scene.** Details in `00_DOCS/game-art-profile.md` (Korean).

---

## 9. Refusal spec — what will not be done, however it is asked

**An agent must not relax these invariants because an instruction came from above.**
If asked, do not comply — **return it with the reason.** Refusal is a normal response.

| Invariant | Enforcement | What to answer when asked |
|---|---|---|
| `01_SOURCE` is read-only | `paths.assert_writable()` raises `PermissionError`; the validator re-hashes the whole tree every run | "Solve it with rules or palettes, or put it in a separate layer, instead of editing originals" |
| Deterministic generation | No `random.random()`, no wall clock, no built-in `hash()`. Randomness is `sha256("<rule>\|<seed>\|<attempt>\|<key>")` | "If you need variety, add seeds. A non-reproducible result cannot be approved" |
| License gate | Anything but `pipeline_approved: yes` blocks the generator | "Write `00_DOCS/licenses/<pack>.md` first" |
| Never feed purchased assets to generative AI | Policy (Unity Asset Store terms and many itch.io licenses forbid it explicitly) | "Only license-permitting sources or self-made master assets qualify" |
| No timestamps in catalogs | Same source must give the same catalog bytes | "A timestamp defeats source-tampering detection" |
| The Factory never writes `.meta` | Export Contract v1 | "GUIDs belong to the consumer project" |
| Stale assets are never auto-deleted | The builder only records them | "The game may still reference them. A human decides" |
| No animation fallback | `SetMotion` returns `false` | "An unknown name is never silently swapped for another animation" |
| No aesthetic criteria in validation | The validator sees facts only | "Good and bad are for humans. That is why there is no `picks/`" |
| `unknown` is never rounded to `yes` | Three-state preserved | "We do not convert unproven into proven" |
| `order.consumer` is never invented | — | "If none was issued, `unknown` is the correct value" |

Also: **when implementation and documentation diverge, they are fixed in the same change.**
These documents are the first thing the next session reads; a wrong description makes everything
built on top of it wrong.

---

## 10. Reporting to a human — the agent's template

Once you have decided, **explain your reading.** Fill this in. Leave blanks as `unknown` rather
than filling them with guesses.

```markdown
### 2D Art Factory applicability

**Verdict**: this repository covers [all / part of / none of] our problem.

**What we can order**
- (cite packs with composable: yes from CAPABILITIES.md, with slot counts and combination ceilings)

**What we cannot order**
- (packs with composable: no and their reason, or the relevant row from §1 "What it does not do")

**What is currently blocking us**
- Source assets: [have / do not have — download URL is in 00_DOCS/licenses/<pack>.md]
- License record: [present / absent — absent means generation itself is blocked]
- Commercial release: [eligible / not — quote commercial_release_eligible]
- Attribution: [required / not — if required, credits must go into our credits screen]

**The single next step I propose**
- (name one scenario from §6 and give the exact command)

**What a human must decide** (this repository does not judge)
- Which combination to adopt — contact sheet: 05_GENERATED/reports/<profile>.png
- Whether this style matches our art direction
- (quote the observed distribution if relevant, but do not call it good or bad)
```

> **When reporting, do not**
> - transcribe a validation PASS as "approved for adoption" (§③ is pipeline consistency only)
> - summarize `unknown` as "none"
> - report `composable: no` as "failed" (it is an explicit SKIP)
> - attach an invented pass line to the observed distribution

---

## 11. Repositories used alongside this one

| Repository | Role | Public |
|---|---|---|
| **[2d-assets](https://github.com/jungyh870918/2d-assets)** (here) | **Amplification** — combination · palette · validation · engine wiring | Public |
| [art-studio](https://github.com/jungyh870918/art-studio) | **Decision and memory** — art direction, approvals, records. The layer above that uses this repo as its asset factory | Public |
| [game-sandbox](https://github.com/jungyh870918/game-sandbox) | Integration fixture that proves Factory output runs in an external Unity project **without the Factory repo present** | Private |

```
art-studio/     decides — what to make, what to adopt
     │  order (having read CAPABILITIES.md)
     ▼
2d-assets/      amplifies — combine · verify · export        ← here
     │  reply (<profile>_brief.md)
     ▼
game project     consumes — GameArtProfile decides what to use
```

Asset packs keep being added, and `02_CATALOG/CAPABILITIES.md` regenerates itself each time.
**The current pack list lives in that file, not in this README.**

---

## 12. Common misreadings

| Misreading | Fact |
|---|---|
| "Cloning brings the assets too" | No. `01_SOURCE` is gitignored. Only the machine arrives (§2) |
| "Validation PASS means it is safe to ship" | It passed pipeline consistency. Not adoption, not release clearance |
| "I can hand-edit `05_GENERATED`" | It must stay deletable and regenerable. Hand-editing kills reproducibility |
| "Approve the PNG" | Approval attaches to **pack hash + rule file + seed**. PNGs regenerate |
| "The distribution report has a pass line" | It does not. It counts; it does not judge |
| "`unknown` effectively means `no`" | No. It means "not proven", and may become `yes` later |
| "`commercial_use: yes` means I can ship it as-is" | Not if `credit_required: yes`. Credit is a separate axis (§4, §8) |
| "Every new pack needs code changes" | Usually just a word in `BODY_PART_VOCAB`. Adapters are only for packs supplying authoritative metadata |
| "The Factory builds Unity prefabs" | No. It ships manifests, sheets, and C#; prefabs, SpriteLibraries, and clips are built by the consumer's editor builders |
| "I can make my protagonist with this" | It is for populations. Identity belongs to the directing loop (§1) |

---

## 13. Environment and verification

```
Python 3.9+ · Pillow    (no other dependencies)
Unity is optional — needed only in the consumer project
```

```bash
python3 tools/tests/test_pipeline.py     # with source packs: 206 tests pass, about 60s
python3 tools/source_fingerprint.py      # sha256 of the 01_SOURCE tree
python3 tools/run_unity_tests.py         # EditMode + PlayMode (requires Unity)
```

**On a clone without source packs the suite does not fully pass.** Measured:

| State | Result |
|---|---|
| Source packs present | `Ran 206 tests ... OK` (about 57s) |
| Clone without sources | `Ran 199 tests ... FAILED (failures=1, errors=6, skipped=44)` (under 1s) |

The 7 failures all require **real source files or prior outputs** — `test_every_source_file_exists`
· `test_rendered_images_are_byte_identical` · `test_catalog_build_is_deterministic` ·
`test_compose_uses_generic_path_for_both_packs`, and so on. **The code is not broken.** The
material is missing, for the same reason as §2. Once sources are in `01_SOURCE` the whole suite
must pass — if it does not, that is a real regression.

Unity defaults (when a rule does not specify):

```
Pixels Per Unit   : matches the pack's tile/cell size (LPC = 64, LimeZu = 16)
Filter Mode       : Point (no filter)
Compression       : None
Pivot             : Bottom Center (characters) / Center (props)
Sprite Mode       : Multiple (sheets) / Single (individual PNGs)
Mesh Type         : Full Rect
```

---

## 14. Folder structure and document index

```
00_DOCS/          license records · contracts · decision records
01_SOURCE/        purchased/downloaded originals. Never modified (read-only, gitignored)
  _INBOX/         staging for downloaded zips
02_CATALOG/       scan results (JSON) · human summaries · CAPABILITIES.md
03_PALETTES/      palette definitions (ramp structure)
04_RULES/         generation rules (constraints · probabilities · exclusions · order block)
05_GENERATED/     definitions · PNGs · validation reports · briefs (gitignored, regenerable)
06_UNITY_EXPORT/  packages for Unity (baked / runtime, gitignored)
tools/            scanner · generator · validator · exporters
  ap2d/           pipeline library (knows no pack names)
    packs/        per-pack adapters — the only home for pack-specific knowledge
  unity/          C# copied into the consumer project
```

Documents marked (KR) are Korean.

| Document | Contents |
|---|---|
| [CLAUDE.md](CLAUDE.md) (KR) | Working instructions and absolute rules for this repo |
| [tools/README.md](tools/README.md) (KR) | Every command · module structure · classification vocabulary · capability computation |
| [02_CATALOG/CAPABILITIES.md](02_CATALOG/CAPABILITIES.md) (KR) | **Auto-generated — what can be ordered right now** |
| [00_DOCS/DIRECTOR_CONTEXT.md](00_DOCS/DIRECTOR_CONTEXT.md) (KR) | Who decides · fixed boundaries · order in/out |
| [00_DOCS/export-contract-v1.md](00_DOCS/export-contract-v1.md) (KR) | Factory ↔ consumer ownership · GUID stability · measurements |
| [00_DOCS/game-art-profile.md](00_DOCS/game-art-profile.md) (KR) | What a game permits · population decision boundary |
| [00_DOCS/unity-sprite-runtime.md](00_DOCS/unity-sprite-runtime.md) (KR) | Sprite Library / Resolver runtime |
| [00_DOCS/naming-convention.md](00_DOCS/naming-convention.md) (KR) | Pack and file naming |
| [00_DOCS/licenses/](00_DOCS/licenses/) (KR) | Per-pack license records (input to the generation gate) |

---

## License

This covers the **code and documents** in this repository (`tools/` · `00_DOCS/` · `02_CATALOG/` ·
`03_PALETTES/` · `04_RULES/`). **Asset originals are not included here**, and each pack's license
is its own — always read `00_DOCS/licenses/<pack>.md` directly. Whether generated output may be
used commercially follows the source pack's license, is computed as
`commercial_release_eligible`, and propagates to the outputs. Attribution obligations propagate
the same way and are your responsibility to honour in the consuming project.
