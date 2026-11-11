---
title: README
emoji: 👁️
colorFrom: indigo
colorTo: gray
sdk: static
pinned: false
---

<p align="center">
  <img alt="aemon: weigh what is known. test what is not." src="https://raw.githubusercontent.com/HatemSaadallah/aemon/main/docs/figures/aemon-wordmark.png" width="380">
</p>

# Two-Eyed Ravens

**aemon** teaches a 3B open model to investigate a strategy question the way a careful analyst would: frame the
decision, state rival explanations, weigh quoted evidence for and against each, look for what would prove the
favourite wrong, propose a test when one is worth its cost, and revise when new evidence arrives.

Built for the Lexsi AI Hackathon, Track 3 (Agentic Fine-Tuning), with AgentTune, AuditKIT and CuratorKIT.

| **+0.83** | **+0.52** | **28 of 48** | **$0.03** |
|:---:|:---:|:---:|:---:|
| blind quality over the best-prompted base model on the first frozen test (0–3 scale, 95% interval 0.69 to 0.97) | on a second frozen test, 12 more unseen companies (0.33 to 0.70) | investigations finished with an accepted recommendation, against 4 of 48 for the base model | per investigation, self-hosted on one A100 slice |

## Start here

- **[Live demo](https://saadallah-r-hatem--aemon-serve.us-east.modal.run/)**: sign in with the test account from our submission. It runs on CPU and sleeps when idle.
- **[Write-up and code](https://github.com/HatemSaadallah/aemon)**: the full submission write-up is the repository's README.
- **[Model](https://huggingface.co/HatemSaadallah/tiny-aya-global-strategy-agent)**: the LoRA adapter for Tiny Aya Global, with its GGUF conversion.
- **[Dataset](https://huggingface.co/datasets/HatemSaadallah/strategy-agent-investigations)**: training rows, the dossier, every case, and all evaluation runs and judge outputs.
- **[Collection](https://huggingface.co/collections/HatemSaadallah/strategy-investigation-agent-6af0d2ab19339ae58d020326)** · **[Paper](https://github.com/HatemSaadallah/aemon/blob/main/docs/PAPER.pdf)**

![The reasoning map of one investigation](https://raw.githubusercontent.com/HatemSaadallah/aemon/main/docs/figures/ui/redesign/after/map.png)

## Team

Hatem Saadallah and Nour Jennane, Master's students in artificial intelligence.
