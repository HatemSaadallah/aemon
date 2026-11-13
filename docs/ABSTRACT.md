# Abstract

**aemon: teaching a 3B model to investigate a strategy question, with AgentTune and AuditKIT.**
Team Two-eyed Ravens, Lexsi AI Hackathon, Track 3 (agentic distillation; workflow and decision agents; efficient
trajectories).

Asked whether a manufacturer should take its technology into a new market, language models tend to write consulting
prose: unsourced numbers, and evidence gathered only for the answer they started with. We built an environment in
which an agent must investigate instead: frame the decision, state rival causal theories, weigh quoted evidence from a
dossier of public records for and against each, look for evidence against its favourite, propose a test with a
decision rule, revise when new evidence arrives, and recommend. Twelve guarded tools and a stage controller enforce
the procedure: a quote that is not word for word in its source is refused, and every call can be replayed.

Command A+ served as the teacher. Only its investigations that replayed exactly and reached an accepted finish became
training data: 3,891 rows from 158 investigations, plus 51 correction rows. We fine-tuned Tiny Aya Global (3.35B
parameters) with AgentTune (LoRA), replayed every evaluation run with AuditKIT, and scored runs with executable checks
and two blind LLM judges, both qualified beforehand.

On a frozen test of four companies never used for training or selection, run once, the fine-tuned model scored 1.48
against 0.65 for the base model under its best prompt (0–3 rubric; +0.83, 95% interval 0.69 to 0.97). It was higher on
all 16 cases and finished 28 of 48 investigations against 4. A second frozen test on twelve new companies gave +0.52
[0.33, 0.70]. The gain holds when whole companies are resampled, and on the stages both runs
reached (+0.92).

The final system was built after both tests, partly from failures seen in their runs, so its numbers are not held out.
It adds a second adapter and decoding-time guards that remove failing
actions: repeated calls, misquotes, and an evidence label chosen before the quote. On the same cases it scores +1.02
[0.92, 1.10] and +1.11 [1.01, 1.20] over the base model, and finishes 46 of 48 and 65 of 72 investigations. Per finished
investigation it needs 39 tool calls against the base model's 242, and refused calls fall from 29% to 7.5%.

A closed model does better. Claude Haiku 5.5, run through the same environment and judged blind alongside our arms,
scores 2.28 against the final system's 1.62, for about $0.008 per investigation through the API against $0.03
self-hosted. Fine-tuning takes the small model about 60% of the way from its base to Haiku. What it offers instead is
control: it runs offline on one GPU or a laptop, keeps the case data on the machine, and its weights are open.

The model learned the procedure more than the judgement. Its largest gains are in framing the decision and stating
distinct theories; its recommendations score lowest. An audit of the teacher shows why: 74% of the teacher's
recommendations use a number found in no source, and the student inherits such habits. At run time, removing a failing
action from what the model can produce worked; telling the model about its mistake did not.

The model, the data, every judged run, a live demo and the code are public.
