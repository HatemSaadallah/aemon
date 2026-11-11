"""Resumable LoRA training of Tiny Aya through AgentTune, on rows from strategy/rows.py.

AgentTune holds the dataset and drives the run: create_distill_trainer stores each row as a
demonstration, and Project.distill hands them to our trainer factory and calls train(). The factory
applies the chat template and puts loss on the target reply only, as the checkpoint gate proved.

Resumable across the one-day Slurm limit: it saves the adapter, optimizer, scheduler and random
state every --save-steps, keeps the latest two, and when Slurm sends USR1, or --minutes runs out,
it saves and stops cleanly. Run the same command again and it continues from the latest complete
checkpoint, skipping the batches already seen, so no row is trained twice or skipped.

--fixture-rows N trains on N scripted investigations written by code, with no model involved.
They test the machinery only, and can never be pilot data.

--validation-cases holds whole companies out of training and reports their loss beside the training
loss. Splitting by row would leak, because turns from one investigation are near copies of each other.
Training loss alone overstates learning: stage guidance names the next step, so some targets can be
copied from the context. The checkpoint kept is the one with the lowest held-out loss.
"""

from __future__ import annotations

import os as _os

if _os.environ.get('AEMON_UNSLOTH'):  # Unsloth patches transformers and TRL, so it must be imported before them
    import unsloth  # noqa: F401  # pyright: ignore[reportMissingImports]
# 'unsloth' offloads activations to the CPU (less memory, slower); 'true' is standard checkpointing, as TRL's default
# for the current trainer; 'false' none
UNSLOTH_CHECKPOINTING = {'true': True, 'false': False}.get(_os.environ.get('AEMON_UNSLOTH_CHECKPOINTING', 'unsloth'), 'unsloth')

import argparse
import json
import os
import signal
import time
from collections.abc import Sequence
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import torch
from agenttune.agentic.distill_trainer import create_distill_trainer  # noqa: E402
from peft import LoraConfig  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainerCallback  # noqa: E402
from trl.trainer.sft_config import SFTConfig
from trl.trainer.sft_trainer import SFTTrainer  # noqa: E402

from aemon.common.constants.prompts import PROMPTS
from aemon.common.constants.training import GATE_FAILED, TARGETS, UNSLOTH_TARGETS  # noqa: F401
from aemon.common.paths import ROOT  # noqa: E402
from aemon.common.types import Json
from aemon.rows.build_rows import Overlength, labels_for, transcript, turn_rows  # noqa: E402

if TYPE_CHECKING:
    from datasets import Dataset
    from peft import PeftModel
    from transformers import TrainerControl, TrainerState, TrainingArguments

STOP = {'requested': False}


def fixture_rows(count: int) -> list[Any]:
    """Scripted investigations recorded as a runner would. Written by code, never by a model."""
    from aemon.agent.records import record_of
    from aemon.environment.cases import load_cases
    from aemon.environment.tools import Investigation
    from aemon.evaluation.diagnostics.fixed_policies import scripted

    rows = []
    for case in load_cases():
        run = scripted(case, 'kept')
        replay = Investigation(case, staged=True)
        turns = [
            {'text': json.dumps({'name': c['name'], 'arguments': c['arguments']}), 'tool_result': replay.call(c['name'], c['arguments'])} for c in run.calls
        ]
        record = record_of(run, {'turns': turns, 'stop_reason': 'finished'})
        rows += [dict(r, case=case.id, source='scripted fixture') for r in turn_rows(transcript(record, case, PROMPTS['staged'])[0])]
        if len(rows) >= count:
            break
    return rows[:count]


class Deadline(TrainerCallback):
    """Saves and stops before the time limit, or when Slurm warns with USR1."""

    def __init__(self, minutes: float) -> None:
        self.end = time.time() + minutes * 60
        self.stamps: list[float] = []  # when each optimizer step ended, for seconds per step without the start-up

    def on_step_end(self, args: TrainingArguments, state: TrainerState, control: TrainerControl, **kwargs: Any) -> None:
        self.stamps.append(time.time())
        if STOP['requested'] or time.time() > self.end:  # control is changed in place, which the trainer reads
            control.should_save = True
            control.should_training_stop = True


def company_of(case_id: str) -> str:
    return case_id.split('-')[0]


# Hosted teachers whose rows are validated as their own group (DECISIONS 2026-11-10 23:05 and 23:10 UTC).
HOSTED_TEACHERS = {'28d028636d6b35cb67cc1afd3409512147cefa2b57f7a709826e971b0ef23b70': 'ds_'}


def group_of(row: Json) -> str:
    """The validation group: the company, prefixed ds_ for a DeepSeek row, so each teacher is averaged on its own."""
    return HOSTED_TEACHERS.get(str(row.get('teacher_weights')), '') + company_of(row['case'])


def cap_per_company(rows: list[Json], limit: int) -> list[Any]:
    """At most limit rows per validation company, evenly spaced through its rows, so one long company cannot dominate
    and evaluation stays short enough to run every few steps."""
    by = {}
    for row in rows:
        by.setdefault(company_of(row['case']), []).append(row)
    out = []
    for company in sorted(by):
        group = by[company]
        step = max(len(group) / limit, 1) if limit else 1
        out += [group[int(i * step)] for i in range(min(limit, len(group)) if limit else len(group))]
    return out


class CompanyTrainer(SFTTrainer):
    """Validation loss for each held-out company, and their unweighted mean as eval_loss, so the checkpoint is chosen
    on a company-balanced average and not on whichever company has the most or longest rows."""

    company_sets = {}

    def evaluate(
        self, eval_dataset: Dataset | dict[str, Dataset] | None = None, ignore_keys: list[str] | None = None, metric_key_prefix: str = 'eval'
    ) -> dict[str, float]:
        if eval_dataset is not None or len(self.company_sets) < 2:
            return super().evaluate(eval_dataset, ignore_keys, metric_key_prefix)
        out, per = {}, {}
        for name, data in self.company_sets.items():
            metrics = super().evaluate(data, ignore_keys, f'eval_{name}')
            per[name] = metrics[f'eval_{name}_loss']
            out.update(metrics)
        hosted = {k: v for k, v in per.items() if k.startswith('ds_')}
        if hosted and len(hosted) < len(per):  # both teachers: the universal loss weights each teacher equally
            own = {k: v for k, v in per.items() if k not in hosted}
            out['eval_teacher_commanda_loss'] = sum(own.values()) / len(own)
            out['eval_teacher_deepseek_loss'] = sum(hosted.values()) / len(hosted)
            out['eval_loss'] = (out['eval_teacher_commanda_loss'] + out['eval_teacher_deepseek_loss']) / 2
            self.log({k: out[k] for k in ('eval_loss', 'eval_teacher_commanda_loss', 'eval_teacher_deepseek_loss')})
            return out
        out['eval_loss'] = sum(per.values()) / len(per)
        self.log({'eval_loss': out['eval_loss']})
        return out


class Factory:
    """AgentTune's trainer_factory hook. Rows arrive as AgentTune demonstrations and are decoded back."""

    def __init__(
        self,
        model_path: str,
        limit: int,
        resume: str | None,
        callbacks: list[TrainerCallback],
        held_out: Sequence[Json] = (),
        stages: Sequence[str | None] = (),
        sources: Sequence[str] = (),
        init_adapter: str | None = None,
        unsloth_seed: int | None = None,
    ) -> None:
        self.unsloth_seed = unsloth_seed  # set: load and wrap the model with Unsloth (its own environment; see --unsloth)
        self.model_path, self.limit, self.resume, self.callbacks, self.held_out, self.stages = model_path, limit, resume, callbacks, held_out, stages
        self.init_adapter = init_adapter
        self.sources, self.supervised = sources, {}
        self.refused, self.refused_validation = {}, {}

    def __call__(self, model: str, train_dataset: Dataset, **kwargs: Any) -> CompanyTrainer:
        tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        self.tokenizer = tokenizer
        rows = []
        for index, row in enumerate(train_dataset):
            item = cast(Json, row)
            context = json.loads(item['messages'][0]['content'])
            target = item['messages'][1]
            try:
                made = labels_for(tokenizer, {'messages': context + [target], 'target_index': len(context)}, self.limit)
                rows.append(made)
                source = self.sources[index] if index < len(self.sources) else 'teacher'
                count = self.supervised.setdefault(source, {'rows': 0, 'tokens': 0})
                count['rows'] += 1
                count['tokens'] += sum(label != -100 for label in made['labels'])
            except Overlength:  # refused and counted by stage, never cut, so late stages are not silently lost
                stage = self.stages[index] if index < len(self.stages) else None
                self.refused[stage] = self.refused.get(stage, 0) + 1
        held, sets = [], {}
        for row in self.held_out:
            try:
                made = labels_for(tokenizer, row, self.limit)
            except Overlength:
                self.refused_validation[row.get('stage')] = self.refused_validation.get(row.get('stage'), 0) + 1
                continue
            held.append(made)
            sets.setdefault(group_of(row), []).append(made)
        self.trained_rows, self.validation_rows = len(rows), len(held)
        if self.unsloth_seed is not None:  # the same LoRA (rank 16, alpha 32, dropout 0.05, every linear layer), built by Unsloth
            from unsloth import FastLanguageModel  # pyright: ignore[reportMissingImports]

            base, _ = FastLanguageModel.from_pretrained(self.model_path, max_seq_length=self.limit, dtype=torch.bfloat16, load_in_4bit=False)
            base = FastLanguageModel.get_peft_model(base, r=16, lora_alpha=32, lora_dropout=0.05, target_modules=list(UNSLOTH_TARGETS),
                                                    bias='none', use_gradient_checkpointing=UNSLOTH_CHECKPOINTING, random_state=self.unsloth_seed)
            lora: LoraConfig | None = None
        else:
            base = AutoModelForCausalLM.from_pretrained(self.model_path, dtype=torch.bfloat16, device_map={'': 0})
            lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, target_modules=TARGETS, task_type='CAUSAL_LM')
        if self.init_adapter:  # a continuation: train the existing adapter further instead of a fresh one
            from peft import PeftModel

            base = PeftModel.from_pretrained(base, self.init_adapter, is_trainable=True)  # type: ignore[assignment]
            lora = None
        from datasets import Dataset

        config = SFTConfig(remove_unused_columns=False, dataset_kwargs={'skip_prepare_dataset': True}, **kwargs)
        trainer = CompanyTrainer(
            model=base,
            args=config,
            train_dataset=Dataset.from_list(rows),
            eval_dataset=Dataset.from_list(held) if held else None,
            processing_class=tokenizer,
            peft_config=lora,
            data_collator=self.collate,
            callbacks=self.callbacks,
        )
        trainer.company_sets = {name: Dataset.from_list(group) for name, group in sorted(sets.items())}
        # AgentTune calls trainer.train() itself, so the bound method is replaced to resume from the latest checkpoint
        trainer.train = partial(trainer.train, resume_from_checkpoint=self.resume)  # pyright: ignore[reportAttributeAccessIssue]
        self.trainer = trainer
        return trainer

    def collate(self, batch: list[Json]) -> dict[str, torch.Tensor]:
        pad = self.tokenizer.pad_token_id
        size = max(len(item['input_ids']) for item in batch)

        def filled(key: str, value: int) -> torch.Tensor:
            return torch.tensor([item[key] + [value] * (size - len(item[key])) for item in batch])

        return {'input_ids': filled('input_ids', pad), 'attention_mask': filled('attention_mask', 0), 'labels': filled('labels', -100)}


def latest_checkpoint(folder: str | Path) -> str | None:
    """Only checkpoints the trainer finished writing count."""
    done = [p for p in Path(folder).glob('checkpoint-*') if (p / 'trainer_state.json').exists()]
    return str(max(done, key=lambda p: int(p.name.split('-')[1]))) if done else None


def reproduces(factory: Factory, rows: list[Json], count: int) -> tuple[int, int]:
    """After an overfit run, does the model write the target reply for rows it trained on?"""
    model, tokenizer = cast('PeftModel', cast(CompanyTrainer, factory.trainer).model), factory.tokenizer
    model.eval()
    hits = []
    for row in rows[:count]:
        context = row['messages'][: row['target_index']]
        prompt = tokenizer.apply_chat_template(context, tokenize=False, add_generation_prompt=True)
        ids = tokenizer(prompt, return_tensors='pt', add_special_tokens=False).to(model.device)
        with torch.no_grad():
            out = model.generate(**ids, max_new_tokens=400, do_sample=False)
        reply = tokenizer.decode(out[0][ids['input_ids'].shape[1] :], skip_special_tokens=True).strip()
        hits.append(reply == row['messages'][row['target_index']]['content'].strip())
    return sum(hits), len(hits)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True)
    parser.add_argument('--rows', help='rows from strategy.rows')
    parser.add_argument('--fixture-rows', type=int, help='train on scripted fixtures instead, to test the machinery')
    parser.add_argument('--out', required=True)
    parser.add_argument('--max-steps', type=int, default=0, help='0 means set by --epochs')
    parser.add_argument('--epochs', type=float, default=3)
    parser.add_argument('--warmup', type=float, default=0.05, help='share of steps spent warming up')
    parser.add_argument('--save-steps', type=int, default=25)
    parser.add_argument('--learning-rate', type=float, default=1e-4)
    parser.add_argument('--batch', type=int, default=1)
    parser.add_argument('--accumulate', type=int, default=4)
    parser.add_argument('--max-length', type=int, default=8192)
    parser.add_argument('--minutes', type=float, default=1380, help='stop and save before this, to stay inside the one-day limit')
    parser.add_argument('--seed', type=int, default=7)
    parser.add_argument('--check', type=int, default=0, help='after training, test whether it reproduces this many training targets')
    parser.add_argument('--require', type=int, default=0, help='fail the job unless at least this many are reproduced, so a dependent run never starts')
    parser.add_argument('--validation-cases', nargs='*', default=[], help='companies held out of training, by case id prefix such as hellberg')
    parser.add_argument('--validation-rows-per-company', type=int, default=40, help='evenly spaced, 0 for all')
    parser.add_argument('--validation-rows', help="extra held-out rows, such as a hosted teacher's investigations of a few training companies; validated as their own teacher group, never trained")
    parser.add_argument('--extra-rows', help='rows of another source, such as recovery corrections from strategy.correct')
    parser.add_argument('--extra-token-share', type=float, default=0.2, help='at most this share of supervised target tokens comes from the extra rows')
    parser.add_argument('--init-adapter', help='continue training this LoRA adapter instead of starting a fresh one')
    parser.add_argument('--unsloth', action='store_true', help='build the model and LoRA with Unsloth; needs AEMON_UNSLOTH=1 and its own environment (jobs/unsloth_smoke.sbatch)')
    parser.add_argument('--stages', nargs='*', default=[], help='a specialist: train and validate only on rows from these stages, such as test')
    args = parser.parse_args()
    signal.signal(signal.SIGUSR1, lambda *_: STOP.update(requested=True))
    every = fixture_rows(args.fixture_rows) if args.fixture_rows else [json.loads(line) for line in open(args.rows)]
    if args.stages:  # the same split by company, applied after choosing the stages, so validation measures the same skill
        every = [r for r in every if r.get('stage') in args.stages]
    held_all = [r for r in every if r['case'].startswith(tuple(args.validation_cases))] if args.validation_cases else []
    rows = [r for r in every if r not in held_all]
    held = cap_per_company(held_all, args.validation_rows_per_company)
    if args.validation_rows:
        extra_held = [json.loads(line) for line in open(args.validation_rows)]
        held_all += extra_held
        held += cap_per_company(extra_held, args.validation_rows_per_company)
    if args.extra_rows:  # target length in characters stands in for tokens when choosing; the report counts real tokens
        extra = [r for r in map(json.loads, open(args.extra_rows)) if not r['case'].startswith(tuple(args.validation_cases or ()))]
        size = lambda r: len(r['messages'][r['target_index']]['content'])  # noqa: E731
        base, budget = sum(size(r) for r in rows), args.extra_token_share
        allowed = base * budget / (1 - budget) if 0 < budget < 1 else (0 if budget <= 0 else float('inf'))
        if allowed <= 0:  # a share of 0 trains on the teacher rows alone
            extra = []
        elif sum(size(r) for r in extra) > allowed:
            keep, total = [], 0
            for r in extra[:: max(1, round(sum(size(r) for r in extra) / allowed))]:
                if total + size(r) <= allowed:
                    keep.append(r)
                    total += size(r)
            extra = keep
        rows += [dict(r, source=r.get('source', 'extra')) for r in extra]
    if held and {(r['case'], r.get('teacher_weights')) for r in held} & {(r['case'], r.get('teacher_weights')) for r in rows}:
        raise SystemExit("a case is on both sides of the split for the same teacher")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    resume = latest_checkpoint(out / 'checkpoints')
    if not args.max_steps:  # epochs over the training rows, rounded up to whole optimizer steps
        args.max_steps = max(1, int(-(-len(rows) * args.epochs // (args.batch * args.accumulate))))
    demos = [{'prompt': json.dumps(r['messages'][: r['target_index']]), 'response': r['messages'][r['target_index']]['content']} for r in rows]
    factory = Factory(
        args.model,
        args.max_length,
        resume,
        [deadline := Deadline(args.minutes)],
        held,
        [r.get('stage') for r in rows],
        [r.get('source', 'teacher') for r in rows],
        init_adapter=args.init_adapter,
        unsloth_seed=args.seed if args.unsloth else None,
    )
    evaluation: dict[str, Any] = (
        dict(eval_strategy='steps', eval_steps=args.save_steps, load_best_model_at_end=True, metric_for_best_model='eval_loss', greater_is_better=False)
        if held
        else {}
    )
    trainer = create_distill_trainer(
        args.model,
        demonstrations=demos,
        trainer_factory=factory,
        output_dir=str(out / 'checkpoints'),
        max_steps=args.max_steps,
        per_device_train_batch_size=args.batch,
        gradient_accumulation_steps=args.accumulate,
        learning_rate=args.learning_rate,
        lr_scheduler_type='cosine',
        warmup_steps=max(1, round(args.max_steps * args.warmup)),
        bf16=True,
        report_to=[],
        logging_steps=1,
        save_strategy='steps',
        save_steps=args.save_steps,
        save_total_limit=2,
        seed=args.seed,
        data_seed=args.seed,
        **evaluation,
    )
    started = time.time()
    trainer.train()
    state = factory.trainer.state
    import subprocess

    revision = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True, cwd=ROOT, check=False).stdout.strip() or os.environ.get(
        'CODE_REVISION', ''
    )
    report = {
        'config': vars(args),
        'code_revision': revision,
        'lora_targets': TARGETS,
        'trained': True,
        'source': 'scripted fixtures, not pilot data' if args.fixture_rows else args.rows,
        'rows': len(rows),
        'resumed_from': resume,
        'global_step': state.global_step,
        'max_steps': args.max_steps,
        'stopped_early': state.global_step < args.max_steps,
        'losses': [round(h['loss'], 4) for h in state.log_history if 'loss' in h],
        'seconds': round(time.time() - started),
        'held_out_cases': sorted({r['case'] for r in held}),
        'held_out_rows': len(held),
        'overlength_refused_by_stage': factory.refused,
        # Candidate rows are built from accepted episodes; retained rows passed the length limit and are what was used
        'row_accounting': {
            'training_candidates': len(rows),
            'training_refused_overlength': sum(factory.refused.values()),
            'training_rows_used': factory.trained_rows,
            'validation_candidates': len(held_all),
            'validation_after_company_cap': len(held),
            'validation_refused_overlength': sum(factory.refused_validation.values()),
            'validation_rows_used': factory.validation_rows,
            'validation_refused_by_stage': factory.refused_validation,
            'validation_rows_by_company': {c: sum(group_of(r) == c for r in held) for c in sorted({group_of(r) for r in held})},
            'note': 'Rows are not independent: each accepted episode gives about 25.',
        },
        'supervised_by_source': factory.supervised,
        'extra_share': {
            k: round(factory.supervised.get('correction', {}).get(k, 0) / max(sum(v[k] for v in factory.supervised.values()), 1), 3) for k in ('rows', 'tokens')
        },
        'held_out_by_company': {
            c: [[h['step'], round(h[f'eval_{c}_loss'], 4)] for h in state.log_history if f'eval_{c}_loss' in h]
            for c in sorted({group_of(r) for r in held})
        },
        'held_out_by_teacher': {
            t: [[h['step'], round(h[f'eval_teacher_{t}_loss'], 4)] for h in state.log_history if f'eval_teacher_{t}_loss' in h] for t in ('commanda', 'deepseek')
        },
        'held_out_metric': ('universal: the mean of the two teachers, each the unweighted mean over its validation companies'
                            if any(group_of(r).startswith('ds_') for r in held) and any(not group_of(r).startswith('ds_') for r in held)
                            else 'unweighted mean over validation companies' if len({group_of(r) for r in held}) > 1 else 'mean over validation rows'),
        'rows_by_stage': {k: sum(r.get('stage') == k for r in rows) for k in sorted({str(r.get('stage')) for r in rows})},
        'held_out_losses': [[h['step'], round(h['eval_loss'], 4)] for h in state.log_history if 'eval_loss' in h],
        'best_checkpoint': state.best_model_checkpoint,
        'peak_gpu_gb': round(torch.cuda.max_memory_allocated() / 1e9, 2),
        'step_seconds': [round(b - a, 2) for a, b in zip(deadline.stamps, deadline.stamps[1:])],
    }
    if state.global_step >= args.max_steps:
        factory.trainer.save_model(str(out / 'adapter'))
        if args.check:
            report['reproduced'], report['checked'] = reproduces(factory, rows, args.check)
    (out / f'report-step{state.global_step}.json').write_text(json.dumps(report, indent=1))
    print(json.dumps({k: v for k, v in report.items() if k != 'losses'} | {'first_loss': report['losses'][:1], 'last_loss': report['losses'][-1:]}), flush=True)
    if args.require and report.get('reproduced', 0) < args.require:
        print(f'gate failed: reproduced {report.get("reproduced", 0)} of {report.get("checked", 0)}, under {args.require}', flush=True)
        raise SystemExit(GATE_FAILED)  # its own exit code, so a failed gate is never confused with a crash


if __name__ == '__main__':
    main()
