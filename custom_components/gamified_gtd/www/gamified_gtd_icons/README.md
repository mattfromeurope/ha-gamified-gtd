# Custom icons (optional)

The cards look for icon files here and fall back to text glyphs when a file is
missing:

```
gamified_gtd_icons/
  special/<stat>.png      strength, perception, endurance, charisma, intelligence, agility, luck
  special/<stat>.svg      SHIPPED placeholder (our own Vault-Boy-style drawing) — used when no .png exists
  skill/<skill>.png       barter, energy_weapons, explosives, guns, lockpick, medicine,
                          melee_weapons, repair, science, sneak, speech, survival, unarmed
  perk/<perk_id>.png      e.g. swift_learner.png, intense_training.png, educated.png
  quest/<project_id>.png  optional per-quest icon
  goat/slide_<n>.png      G.O.A.T. slides (Fallout 3), slide_1.png … slide_10.png —
                          shown on the gamified-gtd-goat card during the test;
                          sources: the Fallout Wiki links in DESIGN.md / the GOAT
                          questionnaire (FO3_GOAT_slide_<n>.jpg)
```

Lookup order per icon: `<id>.png` (your drop-in) → `<id>.svg` (shipped placeholder,
only for `special/`) → text glyph.

Served at `/gamified_gtd_static/gamified_gtd_icons/...`.

**Note:** The original Fallout: New Vegas icons are copyrighted by Bethesda/ZeniMax
and are therefore **not shipped** with this integration. If you own the game, you may
copy the icons from your own game files or from a source you are licensed to use into
the folders above — the cards will pick them up automatically (hard-refresh the browser
after adding files).
