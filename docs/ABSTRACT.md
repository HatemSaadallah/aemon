# Abstract

**aemon: teaching a 3B model to investigate a strategy question, with AgentTune and AuditKIT.**
Team Two-eyed Ravens, Lexsi AI Hackathon, Track 3 (agentic distillation; business workflow and decision agents). The abstract as submitted.

Should a manufacturer take its technology into a new market? The answer could shape its next product, investment, and years of work. Aemon helps teams investigate that decision before they commit.

Aemon is a strategy investigation agent powered by a small, locally runnable language model. Give it a market-entry question, and it builds competing explanations, searches for evidence, challenges its favourite hypothesis, and proposes a practical test. The investigation unfolds in an interactive workspace where users can explore the reasoning, inspect sources, and see what would change the recommendation.

At its core is a simple principle: make the reasoning inspectable. Twelve guarded tools structure the investigation, check quotations against their sources, and prevent simulated results from being presented as real evidence. Every tool call is recorded and can be replayed.

We used AgentTune to distill successful investigations from a stronger teacher into Tiny Aya Global, a 3.35-billion-parameter model, and AuditKIT to replay evaluation runs. On two frozen tests covering 16 unseen companies, the fine-tuned model outperformed its best-prompted base under two blind LLM judges. On the first test, its average quality score rose from 0.65 to 1.48 out of 3.

We then tackled the failures directly. Two complementary adapters divide evidence gathering and reasoning, while decoding constraints prevent repeated actions and invalid quotations. This final system completed 46 of 48 investigations, compared with 4 of 48 for the base model on the same benchmark. These later results reflect improvements developed after the original tests.

Aemon can run locally on a laptop or GPU, giving teams control over their model and keeping case data on their own machine. Recommendations still need human review; the strongest gains are in structuring the investigation.

Our goal is to help teams move from "we think this will work" to "here is the evidence, here is the uncertainty, and here is what we should test next."
