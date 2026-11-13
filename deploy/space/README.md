---
title: aemon
emoji: 👁️
colorFrom: indigo
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
license: cc-by-nc-4.0
short_description: A small model that investigates a strategy question
---

# aemon

*weigh what is known. test what is not.*

A strategy-investigation agent: Tiny Aya Global (3.35B parameters) with LoRA adapters, working through a fixed
investigation process over a dossier of public sources. Open the app, pick a company, and read a finished investigation
or start one.

- **Sign-in.** Pick any username: a new one opens a new account, and the same one brings you back to it. There is no
  password, so a username is not private.
- **Speed.** This Space runs the 4-bit model on CPU. Finished investigations open at once; a new one takes many minutes
  and stops after 45 steps, the budget of the evaluated runs.
- **What runs.** The final system: version 1 of the adapter gathers the evidence and version 3 reasons over it (dig
  then reason), with decoding-time guards. Results, including a comparison with Claude Haiku 5.5, are in the
  [repository](https://github.com/HatemSaadallah/aemon).
- **Model and licence.** Base model: [CohereLabs/tiny-aya-global](https://huggingface.co/CohereLabs/tiny-aya-global),
  CC-BY-NC 4.0, non-commercial use. Adapter: [two-eyed-ravens/aemon](https://huggingface.co/two-eyed-ravens/aemon).
- **Sources.** The dossier quotes public web pages, each shown with its publisher and link. Company banners and logos
  are from Wikimedia Commons with their licences recorded in `app/profiles/company_profiles.json`.

The recommendations are a small model's reading of a fixed set of sources, not advice.
