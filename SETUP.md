# How the profile cards update

Three repositories; only this one is public.

```
ai-usage (private)                     paper-library (private)
  Mac launchd 12:40 / 23:40              Actions daily 06:07 Taipei
  codexbar → data/ai.json → push         alphaXiv API → data/library.json, covers
  Actions: draw ai-usage-card.svg        Actions: draw papers-card.svg
        │  scripts/publish.sh (PROFILE_TOKEN)  │
        └──────────────┬───────────────────────┘
                       ▼
samynhn/samynhn (public, this repo)
  assets/ai-usage-card.svg, assets/papers-card.svg, data/*-summary.json, data/papers-links.md
  Actions (daily 06:37 + whenever the private repos publish):
    GitHub stats → draw profile-{light,dark}.svg → refresh README paper links
```

Raw usage history and the full library stay private; only the rendered cards and two small
summaries (tokens in 30 days, primary tool, paper count, top folder) are published here.
All automated commits use bot authors, so they never show up in your contribution graph.

## Setup

1. Create two **private** repos, `ai-usage` and `paper-library`, and push the matching folders.
2. Create a **fine-grained token**: GitHub → Settings → Developer settings → Fine-grained tokens →
   Repository access: *only `samynhn/samynhn`* → Permissions: *Contents: Read and write*.
3. Secrets (repo → Settings → Secrets and variables → Actions):
   - `ai-usage`: `PROFILE_TOKEN`
   - `paper-library`: `PROFILE_TOKEN`, `ALPHAXIV_API_KEY`
4. In all three repos: Settings → Actions → General → Workflow permissions → *Read and write*.
5. On the Mac:
   ```bash
   git clone https://github.com/samynhn/ai-usage.git ~/ai-usage
   bash ~/ai-usage/mac/install.sh
   ```
6. Run each workflow once by hand (Actions → Run workflow): paper-library, then ai-usage
   (the Mac's first push already triggers it), then this repo.

The token expires (max 1 year for fine-grained tokens) – renew it and update both secrets.
