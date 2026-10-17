# Vaelin UI demo shell · S8 (non-production · local only)

> **This directory = local Web demo shell** · fixture data only · **zero Hermes** · **no public tunnel**  
> Source: UI S8 staging (`_ui_demo_stage`) · public path `demos/ui/`

## Demo ≠ production

- Fixture JSON only; no vault / Hermes / SEALED / plugins
- Three modes (Oxygen / Caesar / Yue) are static grey states
- S8: next-screen preview · speaker timer · speaker notes print / fake HTML export · a11y (skip link / focus / reduced motion)
- Also: clean mode `g` · help `?` · presenter bar `p` · shell-local `localStorage` only

## Run locally

After cloning this repo, from the repository root:

```bat
cd demos\ui
start_demo.bat
```

Or any shell:

```bash
cd demos/ui
python -m http.server 8765 --bind 127.0.0.1
```

Open `http://127.0.0.1:8765/` · **no public tunnel** · use HTTP (not `file://`)

Keys: `←/→` navigate · `?` help · `Esc` close · `g` clean · `p` presenter · `t` timer · `n` preview · `Shift+P` notes

## Hard rules

No production Hermes / hooks / plugins / vault · no live three-mode backends · no tunnel · no guardrail lexicons or real chats in this shell
