# hosted_teacher

DeepSeek (Flash, then V4-Pro) as a hosted teacher for the version 2 corrective families, run on 2026-11-10. The teacher
answered 244 corrective states (`asked_*.json`); `finish.sh` joins the parts, exports them with the provenance, replay
and split checks, and has them reviewed by DeepSeek V4-Pro into `reviews/v2_round5/`.

DECISIONS.md:
- "2026-11-10 19:30 UTC: a hosted teacher (DeepSeek) for the corrective families, and an LLM reviewer";
- "2026-11-10 18:30 UTC: a second hosted teacher, DeepSeek V4-Pro, on the same 244 states";
- "2026-11-10 19:15 UTC: the DeepSeek round's result, the threshold met, and v2 training".
