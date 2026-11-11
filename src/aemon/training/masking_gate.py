"""Gates 1 to 4 of docs/TRAINING_PILOT.md, on the real Tiny Aya checkpoint.

Each step records pass or fail and carries on where it can, so one run shows everything that is
wrong. One optimizer step proves plumbing only. It says nothing about whether training helps.

Run on the cluster through Slurm. Usage:
    python -m aemon.training.masking_gate --model PATH --output PATH
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import torch
from agenttune.agentic.distill_trainer import create_distill_trainer  # noqa: E402
from agenttune.agentic.events import Event, EventKind, EventLog
from agenttune.agentic.rollout_engines.rollout_factory import fold_tool_messages_into_user  # noqa: E402
from peft import LoraConfig, PeftModel  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainerCallback  # noqa: E402
from trl.trainer.sft_config import SFTConfig
from trl.trainer.sft_trainer import SFTTrainer  # noqa: E402

from aemon.agent.experimental.reference import conclude, investigate  # noqa: E402
from aemon.common.constants.prompts import PROMPTS
from aemon.common.types import Json, Message
from aemon.environment.cases import load_cases  # noqa: E402

if TYPE_CHECKING:
    from datasets import Dataset
    from transformers import PreTrainedTokenizerBase, TrainerControl, TrainerState, TrainingArguments

TEMPLATE_SHA = '2147c474f41b'
TAGS = re.compile(r'<tool_call>\s*(.*?)\s*</tool_call>', re.DOTALL)
TARGETS = ['q_proj', 'k_proj', 'v_proj', 'o_proj']
SYSTEM = PROMPTS['strong']


def reference_log(limit_calls: int) -> EventLog:
    """The first calls of the reference investigation, as AgentTune trajectory events."""
    run = conclude(investigate(load_cases('moldex-base')[0]))
    log = EventLog(tier='full')
    log.append(Event(EventKind.OBSERVATION, {'text': 'A new investigation is ready. Call read_brief.'}))
    for entry in run.calls[:limit_calls]:
        log.append(Event(EventKind.TOOL_CALL, {'action': {'name': entry['name'], 'arguments': entry['arguments']}}))
        log.append(Event(EventKind.TOOL_RESULT, {'output': json.dumps(entry['result'])[:1500]}))
    log.append(Event(EventKind.TURN_COMPLETE, {}))
    return log


def repaired(row: Json) -> list[dict[str, str]]:
    """A system prompt plus strict user and assistant turns, as Tiny Aya's template requires."""
    messages, merged = fold_tool_messages_into_user(row['messages']), [{'role': 'system', 'content': SYSTEM}]
    for message in messages:
        if message['role'] == 'assistant':  # teach the same bare JSON that runs enforce, with no tags
            message = dict(message, content=TAGS.sub(r'\1', message['content']).strip())
        if merged[-1]['role'] == message['role']:
            merged[-1] = dict(merged[-1], content=merged[-1]['content'] + '\n' + message['content'])
        else:
            merged.append(dict(message))
    return merged


def labelled(tokenizer: PreTrainedTokenizerBase, messages: list[Message], limit: int) -> Json:
    """Input ids with labels on assistant turns only. Everything else is -100, so it adds no loss."""
    ids, labels = [], []
    for index in range(1, len(messages)):
        if messages[index]['role'] != 'assistant':
            continue
        before = cast(str, tokenizer.apply_chat_template(messages[:index], tokenize=False, add_generation_prompt=True))
        after = cast(str, tokenizer.apply_chat_template(messages[: index + 1], tokenize=False))
        start = len(tokenizer(before, add_special_tokens=False)['input_ids'])
        ids = tokenizer(after, add_special_tokens=False)['input_ids']
        labels = (labels + [-100] * len(ids))[: len(ids)]
        labels[start:] = ids[start:]
    return {'input_ids': ids[:limit], 'attention_mask': [1] * len(ids[:limit]), 'labels': labels[:limit]}


class MaskedFactory:
    """AgentTune's trainer_factory hook: its trajectories, TRL's trainer, our assistant-only labels."""

    def __init__(self, model_path: str, limit: int) -> None:
        self.model_path, self.limit = model_path, limit
        self.trainer: SFTTrainer | None = None
        self.callback: GradientCheck | None = None
        self.start: dict[str, torch.Tensor] | None = None

    def __call__(self, model: str, train_dataset: Dataset, **kwargs: Any) -> SFTTrainer:
        tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        rows = [labelled(tokenizer, repaired(cast(Json, row)), self.limit) for row in train_dataset]
        self.rows, self.tokenizer = rows, tokenizer
        base = AutoModelForCausalLM.from_pretrained(self.model_path, dtype=torch.bfloat16, device_map={'': 0})
        from datasets import Dataset

        config = SFTConfig(remove_unused_columns=False, dataset_kwargs={'skip_prepare_dataset': True}, **kwargs)
        trainer = SFTTrainer(
            model=base,
            args=config,
            train_dataset=Dataset.from_list(rows),
            processing_class=tokenizer,
            peft_config=LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, target_modules=TARGETS, task_type='CAUSAL_LM'),
            data_collator=self.collate,
            callbacks=[self.callback] if self.callback else None,
        )
        self.trainer = trainer
        self.start = {n: p.detach().float().cpu().clone() for n, p in cast(torch.nn.Module, trainer.model).named_parameters() if p.requires_grad}
        return trainer

    def collate(self, batch: list[Json]) -> dict[str, torch.Tensor]:
        pad = self.tokenizer.pad_token_id
        size = max(len(item['input_ids']) for item in batch)

        def filled(key: str, value: int) -> torch.Tensor:
            return torch.tensor([item[key] + [value] * (size - len(item[key])) for item in batch])

        return {'input_ids': filled('input_ids', pad), 'attention_mask': filled('attention_mask', 0), 'labels': filled('labels', -100)}


class GradientCheck(TrainerCallback):
    """Reads gradients after backward and before the optimizer clears them."""

    def __init__(self) -> None:
        self.mean, self.nonzero, self.total = None, 0, 0

    def on_pre_optimizer_step(
        self, args: TrainingArguments, state: TrainerState, control: TrainerControl, model: torch.nn.Module | None = None, **kwargs: Any
    ) -> None:
        model = cast(torch.nn.Module, model)  # the trainer always passes it
        grads = [p.grad for p in model.parameters() if p.requires_grad and p.grad is not None]
        self.total = sum(1 for p in model.parameters() if p.requires_grad)
        self.nonzero = sum(bool(g.abs().sum() > 0) for g in grads)
        self.mean = float(torch.stack([g.float().abs().mean() for g in grads]).mean()) if grads else None


class Gate:
    def __init__(self) -> None:
        self.steps = {}

    def run(self, name: str, step: Callable[[], Json | None]) -> None:
        started = time.time()
        try:
            detail = step() or {}
            self.steps[name] = {'passed': not detail.pop('failed', False), 'seconds': round(time.time() - started, 1), **detail}
        except Exception:  # noqa: BLE001  record it, and let later steps try
            self.steps[name] = {'passed': False, 'seconds': round(time.time() - started, 1), 'error': traceback.format_exc(limit=4)[-900:]}
        print(json.dumps({name: self.steps[name]}, default=str)[:700], flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--work', default='gate_output')
    parser.add_argument('--max-length', type=int, default=4096)
    args = parser.parse_args()
    gate, state = Gate(), {}
    report = {
        'simulated_content': True,
        'trained': 'one optimizer step only, as a plumbing check',
        'gpu': torch.cuda.get_device_name(0),
        'torch': torch.__version__,
    }

    def tokenizer_step() -> Json | None:
        state['tokenizer'] = tokenizer = AutoTokenizer.from_pretrained(args.model)
        templates = tokenizer.chat_template if isinstance(tokenizer.chat_template, dict) else {'default': tokenizer.chat_template}
        hashes = {name: hashlib.sha256(text.encode()).hexdigest()[:12] for name, text in templates.items()}
        tools = [{'type': 'function', 'function': {'name': 'probe_tool', 'description': 'A probe.', 'parameters': {'type': 'object', 'properties': {}}}}]
        rendered = tokenizer.apply_chat_template([{'role': 'user', 'content': 'hello'}], tools=tools, tokenize=False, add_generation_prompt=True)
        return {
            'templates': hashes,
            'default_matches_the_fixture': hashes.get('default') == TEMPLATE_SHA,
            'tools_rendered_natively': 'probe_tool' in rendered,
            'pad_token': tokenizer.pad_token,
            'failed': 'default' not in hashes,
        }

    def load_step() -> Json | None:
        state['model'] = model = AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.bfloat16, device_map={'': 0}).eval()
        config = model.config
        return {
            'parameters_billions': round(sum(p.numel() for p in model.parameters()) / 1e9, 3),
            'layers': config.num_hidden_layers,
            'hidden': config.hidden_size,
            'attention': str(getattr(config, '_attn_implementation', None)),
            'gpu_gb': round(torch.cuda.max_memory_allocated() / 2**30, 2),
        }

    def forward_step() -> Json | None:
        tokenizer, model = state['tokenizer'], state['model']
        batch = tokenizer('A short check of the forward pass.', return_tensors='pt').to(model.device)
        with torch.no_grad():
            loss = model(**batch, labels=batch['input_ids']).loss.item()
        return {'loss': round(loss, 3), 'failed': not torch.isfinite(torch.tensor(loss))}

    def generate_step() -> Json | None:
        tokenizer, model = state['tokenizer'], state['model']
        messages = [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': 'A new investigation is ready. Call read_brief.'}]
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        batch = tokenizer(text, return_tensors='pt', add_special_tokens=False).to(model.device)
        started = time.time()
        with torch.no_grad():
            out = model.generate(**batch, max_new_tokens=60, do_sample=False)
        new = out[0][batch['input_ids'].shape[1] :]
        reply = tokenizer.decode(new, skip_special_tokens=True)
        match = re.search(r'\{.*\}', reply, re.DOTALL)
        try:
            call = json.loads(match.group(0)) if match else None
        except json.JSONDecodeError:
            call = None
        # The gate needs a real generated call. Whether it is a good one is the baseline's question.
        return {
            'prompt_tokens': int(batch['input_ids'].shape[1]),
            'reply': reply[:240],
            'tokens_per_second': round(len(new) / (time.time() - started), 1),
            'parsed_as_a_call': bool(call and call.get('name')),
            'exactly_right_call': bool(call and call.get('name') == 'read_brief' and call.get('arguments') == {}),
            'failed': 'read_brief' not in reply,
        }

    def rows_step() -> Json | None:
        state['log'] = log = reference_log(12)
        factory = state['factory'] = MaskedFactory(args.model, args.max_length)
        state['distill'] = create_distill_trainer(
            args.model,
            trajectories=[log],
            trainer_factory=factory,
            output_dir=str(Path(args.work) / 'checkpoints'),
            max_steps=1,
            per_device_train_batch_size=1,
            learning_rate=1e-4,
            bf16=True,
            report_to=[],
            save_strategy='no',
            logging_steps=1,
        )
        row = state['distill'].sft_dataset()
        messages = repaired(row[0])
        tokenizer = state['tokenizer']
        sample = labelled(tokenizer, messages, args.max_length)
        trained = [t for t, label in zip(sample['input_ids'], sample['labels'], strict=False) if label != -100]
        total = tokenizer.apply_chat_template(messages, tokenize=False)
        visible = tokenizer.decode(trained)
        tool_text = next(m['content'] for m in row[0]['messages'] if m['role'] == 'tool')[:60]
        return {
            'rows': len(row),
            'tokens': len(sample['input_ids']),
            'tokens_with_loss': len(trained),
            'system_prompt_rendered': SYSTEM[:50] in total,
            'tool_output_in_context': tool_text in total,
            'tool_output_has_no_loss': tool_text not in visible,
            'target_preview': visible[:160],
            'failed': SYSTEM[:50] not in total or tool_text in visible or not trained or len(trained) >= len(sample['input_ids']),
        }

    def train_step() -> Json | None:
        state.pop('model', None)
        torch.cuda.empty_cache()
        check = state['gradients'] = GradientCheck()
        state['factory'].callback = check
        state['distill'].train()
        trainer = state['factory'].trainer
        model = trainer.model
        names = [n for n, p in model.named_parameters() if p.requires_grad]
        history = [h for h in trainer.state.log_history if 'loss' in h]
        loss = history[-1]['loss'] if history else None
        lora = sum('lora_' in n for n in names)
        after = {n: p.detach().float().cpu() for n, p in model.named_parameters() if p.requires_grad}
        changed = sum(not torch.equal(after[n], factory_start) for n, factory_start in state['factory'].start.items())
        state['trained'] = after
        return {
            'loss': loss,
            'trainable_tensors': len(names),
            'all_lora': lora == len(names),
            'mean_abs_gradient': check.mean,
            'tensors_with_gradient': check.nonzero,
            'tensors_changed_by_the_step': changed,
            'peak_gpu_gb': round(torch.cuda.max_memory_allocated() / 2**30, 2),
            'failed': loss is None or not torch.isfinite(torch.tensor(float(loss))) or lora != len(names) or not check.nonzero or not changed,
        }

    def reload_step() -> Json | None:
        trainer, tokenizer = state['factory'].trainer, state['tokenizer']
        path = Path(args.work) / 'adapter'
        trainer.model.save_pretrained(path)
        batch = tokenizer('A short check of the saved adapter.', return_tensors='pt').to(trainer.model.device)
        del trainer.model, trainer
        state['factory'].trainer = None
        torch.cuda.empty_cache()
        # Full precision: at bfloat16, logits move in steps of about 0.25, which hides one small step.
        base = AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.float32, device_map={'': 0}).eval()
        with torch.no_grad():
            plain = base(**batch).logits.cpu()
        reloaded = PeftModel.from_pretrained(base, path).eval()
        loaded = {n: p.detach().float().cpu() for n, p in reloaded.named_parameters() if 'lora_' in n}
        trained = {n.replace('.default.', '.'): p for n, p in state['trained'].items()}
        same = sum(torch.equal(p.float(), trained.get(n.replace('.default.', '.'), torch.empty(0))) for n, p in loaded.items())
        with torch.no_grad():
            after = reloaded(**batch).logits.cpu()
        effect = (plain - after).abs().max().item()
        size = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
        return {
            'adapter_mb': round(size / 1e6, 1),
            'tensors_reloaded_exactly': same,
            'tensors_saved': len(trained),
            'adapter_effect_on_logits': effect,
            'failed': same != len(trained) or effect == 0,
        }

    for name, step in (
        ('tokenizer_and_template', tokenizer_step),
        ('load_real_weights', load_step),
        ('forward_pass', forward_step),
        ('real_tool_call', generate_step),
        ('masked_rows_and_system_prompt', rows_step),
        ('one_optimizer_step', train_step),
        ('save_and_reload_adapter', reload_step),
    ):
        gate.run(name, step)
    report['steps'] = gate.steps
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, indent=1, default=str))
    print(json.dumps({k: v['passed'] for k, v in gate.steps.items()}, indent=1))


if __name__ == '__main__':
    main()
