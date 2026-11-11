"""Load aemon's recorded results into MLflow: training runs, evaluation runs and judged comparisons.

Nothing here runs a model or a judge. It reads files that already exist and logs them, so it can be re-run at any time:
a file already logged with the same content is skipped (each run is tagged with its source path and sha256).

    .venv/bin/python ops/mlflow/backfill.py            # everything found
    .venv/bin/python ops/mlflow/backfill.py --dry-run  # list what would be logged

Three experiments:
- aemon-training: one run per adapter training (trainer_state.json, adapter_config.json, the training report).
  Per-step loss, gradient norm, token accuracy and learning rate; held-out loss per evaluation step.
- aemon-evaluation: one run per runner report (base or adapter, on a case split). The arguments it ran with, the
  mechanical summary (finished, refusals, stop reasons) and, where judged, each judge's mean score for that report.
- aemon-comparisons: one run per judge report (arm A minus arm B): each arm's mean, the paired difference with its
  95% case-cluster interval, per judge and for the mean of judges.

Models (the Models tab of aemon-evaluation, and the registry): each adapter and the base model is a logged model whose
weights stay where they are (cluster, Hugging Face), with its training run as the source and the evaluations it ran
linked to it. The registry `aemon-adapter` holds v1, v2 and v3 as versions 1 to 3, with aliases `submitted` (v1) and
`exploratory` (v3).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import sys
from pathlib import Path

os.environ.setdefault('MLFLOW_DISABLE_AGENT_HINT', '1')
import mlflow  # noqa: E402
from mlflow.entities import Metric, Param, RunTag  # noqa: E402
from mlflow.tracking import MlflowClient  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'src'))
from aemon.evaluation.judging.report import episode_scores, load  # noqa: E402

HOME = Path.home() / 'lexsi-backup/mlflow'
TRACKING = os.environ.get('MLFLOW_TRACKING_URI', f'sqlite:///{HOME}/mlflow.db')
ARTIFACTS = f'file://{HOME}/artifacts'
TRAINING_STATES = Path.home() / 'lexsi-backup/cluster/training_states'
# run folder on the cluster -> (name in the docs, training report written at its last step)
TRAINED = {
    'final_pilot': ('v1 (submitted adapter)', 'report-step1971.json'),
    'v3': ('v3', 'report-step1876.json'),
    'v2_deepseek': ('v2 (DeepSeek corrective)', 'report-step480.json'),
    'third_pilot': ('third adapter (development)', 'report-step880.json'),
    'final_overfit': ('v1 overfit gate', None),
    'third_overfit': ('third overfit gate', None),
}
PREDICTIONS = ('claude', 'codex', 'claudecode')


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def flat(prefix: str, value: object, out: dict[str, float]) -> None:
    """Numbers under a nested dict become metrics named a.b.c; everything else is skipped."""
    if isinstance(value, bool):
        out[prefix] = float(value)
    elif isinstance(value, (int, float)):
        out[prefix] = float(value)
    elif isinstance(value, dict):
        for k, v in value.items():
            flat(f'{prefix}.{k}' if prefix else str(k), v, out)


def clean(name: str) -> str:
    return ''.join(c if c.isalnum() or c in '._-/ ' else '_' for c in name)[:250]


class Logger:
    def __init__(self, dry: bool) -> None:
        self.dry = dry
        mlflow.set_tracking_uri(TRACKING)
        self.client = MlflowClient()
        self.experiments: dict[str, str] = {}
        self.logged = self.skipped = 0

    def experiment(self, name: str) -> str:
        if name not in self.experiments:
            found = self.client.get_experiment_by_name(name)
            self.experiments[name] = found.experiment_id if found else self.client.create_experiment(name, artifact_location=f'{ARTIFACTS}/{name}')
        return self.experiments[name]

    def done(self, experiment: str, digest: str) -> bool:
        runs = self.client.search_runs([self.experiment(experiment)], f"tags.source_sha256 = '{digest}'", max_results=1)
        return bool(runs)

    def run(self, experiment: str, name: str, source: Path, params: dict, metrics: dict[str, float], tags: dict,
            steps: dict[str, list[tuple[int, float]]] | None = None, artifacts: tuple[Path, ...] | list[Path] = ()) -> None:
        digest = sha(source)
        if not self.dry and self.done(experiment, digest):
            self.skipped += 1
            return
        print(f'{"would log" if self.dry else "log"} {experiment}: {name}')
        self.logged += 1
        if self.dry:
            return
        run = self.client.create_run(self.experiment(experiment), run_name=name, tags={'mlflow.runName': name})
        rid = run.info.run_id
        now = int(source.stat().st_mtime * 1000)
        batch_metrics = [Metric(clean(k), v, now, 0) for k, v in metrics.items()]
        for key, series in (steps or {}).items():
            batch_metrics += [Metric(clean(key), v, now, int(s)) for s, v in series]
        tag_list = [RunTag(k, str(v)[:5000]) for k, v in {**tags, 'source': str(source.relative_to(REPO) if source.is_relative_to(REPO) else source), 'source_sha256': digest}.items()]
        param_list = [Param(clean(k), str(v)[:6000]) for k, v in params.items() if v is not None]
        for i in range(0, max(len(batch_metrics), 1), 900):  # the store takes at most 1000 entities per batch
            self.client.log_batch(rid, metrics=batch_metrics[i:i + 900], params=param_list if i == 0 else [], tags=tag_list if i == 0 else [])
        for a in artifacts:
            self.client.log_artifact(rid, str(a))
        self.client.set_terminated(rid, 'FINISHED', end_time=now)


def training(log: Logger) -> None:
    for folder, (label, report_name) in TRAINED.items():
        state_path = TRAINING_STATES / f'{folder}.trainer_state.json'
        if not state_path.exists():
            continue
        state = json.loads(state_path.read_text())
        config_path = TRAINING_STATES / f'{folder}.adapter_config.json'
        config = json.loads(config_path.read_text()) if config_path.exists() else {}
        report_path = TRAINING_STATES / report_name if report_name else None
        report = json.loads(report_path.read_text()) if report_path and report_path.exists() else {}
        steps: dict[str, list[tuple[int, float]]] = {}
        for entry in state['log_history']:
            for k, v in entry.items():
                if k not in ('step', 'epoch') and isinstance(v, (int, float)):
                    steps.setdefault(k, []).append((entry['step'], v))
        params = {
            'run_folder': folder, 'lora_r': config.get('r'), 'lora_alpha': config.get('lora_alpha'), 'lora_dropout': config.get('lora_dropout'),
            'target_modules': config.get('target_modules'), 'base_model': config.get('base_model_name_or_path'),
            'epochs': state.get('num_train_epochs'), 'max_steps': state.get('max_steps'), 'batch_size': state.get('train_batch_size'),
            'code_revision': report.get('code_revision'), 'rows': report.get('rows'), 'held_out_rows': report.get('held_out_rows'),
            'supervised_by_source': json.dumps(report.get('supervised_by_source')) if report else None,
        }
        metrics = {'best_eval_loss': state['best_metric']} if state.get('best_metric') is not None else {}
        if report.get('seconds'):
            metrics['train_seconds'] = float(report['seconds'])
        if report.get('peak_gpu_gb'):
            metrics['peak_gpu_gb'] = float(report['peak_gpu_gb'])
        log.run('aemon-training', label, state_path, params, metrics, {'adapter': label, 'kind': 'training'}, steps,
                [p for p in (config_path, report_path) if p and p.exists()])


def judge_means(folder: Path) -> dict[str, dict[str, tuple[float, int]]]:
    """report path -> judge -> (mean episode score, episodes), from a judged folder's key and predictions."""
    key_path = folder / 'key.jsonl'
    if not key_path.exists():
        return {}
    key = [json.loads(line) for line in key_path.read_text().splitlines() if line.strip()]
    out: dict[str, dict[str, list[float]]] = {}
    for judge in PREDICTIONS:
        path = folder / f'{judge}_predictions.jsonl'
        if not path.exists():
            nested = list(folder.glob(f'{judge}_*/predictions.jsonl'))
            path = nested[0] if nested else path
        if not path.exists():
            continue
        preds = load(str(path))
        for k in key:
            p = preds.get(k['packet_id'])
            if p and 'judgment' in p:
                score, _ = episode_scores(p['judgment'])
                if score is not None:
                    out.setdefault(k['report'], {}).setdefault(judge, []).append(score)
    return {r: {j: (statistics.mean(v), len(v)) for j, v in js.items()} for r, js in out.items()}


def evaluation(log: Logger) -> None:
    judged: dict[str, dict[str, tuple[float, int]]] = {}
    for folder in sorted((REPO / 'reports/judge').iterdir()):
        if folder.is_dir():
            for report, judges in judge_means(folder).items():
                for j, v in judges.items():
                    judged.setdefault(Path(report).name, {})[f'{folder.name}.{j}'] = v
    for path in sorted((REPO / 'reports').rglob('*.json')):
        if path.stat().st_size > 200_000_000:
            continue
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not (isinstance(data, dict) and 'summary' in data and 'records' in data and 'arguments' in data):
            continue
        a = data['arguments']
        summary = data['summary']
        metrics: dict[str, float] = {}
        flat('', {k: v for k, v in summary.items() if not isinstance(v, list)}, metrics)
        for name, (mean, n) in judged.get(path.name, {}).items():
            metrics[f'judge.{name}.mean'] = mean
            metrics[f'judge.{name}.episodes'] = float(n)
        params = {k: a.get(k) for k in ('prompt', 'split', 'attempts', 'max_turns', 'max_errors', 'max_tokens', 'context', 'temperature',
                                        'lora_route', 'status_check', 'source_dates', 'recovery', 'backend', 'model_label', 'weights_sha256')}
        params['cases'] = len(str(a.get('cases', '')).split(','))
        params['code_revision'] = data.get('code_revision')
        params['uncommitted_changes'] = data.get('uncommitted_changes')
        rel = path.relative_to(REPO / 'reports')
        set_name = rel.parts[1] if rel.parts[0] == 'judge' and len(rel.parts) > 2 else rel.parts[0]
        name = str(rel.relative_to('judge') if rel.parts[0] == 'judge' else rel).removesuffix('.json')
        log.run('aemon-evaluation', name, path, params, metrics,
                {'set': set_name, 'split': a.get('split'), 'adapter_in_label': 'adapter' in str(a.get('model_label')), 'kind': 'evaluation'})


def comparisons(log: Logger) -> None:
    for path in sorted((REPO / 'reports/judge').rglob('report_*.json')):
        data = json.loads(path.read_text())
        if 'judges' not in data:
            continue
        metrics: dict[str, float] = {}
        compared = None
        blocks = dict(data['judges'])
        if data.get('mean_of_judges'):
            blocks['mean_of_judges'] = data['mean_of_judges']
        for judge, block in blocks.items():
            for arm, v in (block.get('by_arm') or {}).items():
                metrics[f'{judge}.{arm}.mean'] = v['mean'] if isinstance(v, dict) else v
            diff = block.get('difference') or {}
            if diff.get('mean_and_95_interval'):
                m, lo, hi = diff['mean_and_95_interval']
                metrics.update({f'{judge}.difference': m, f'{judge}.difference_low': lo, f'{judge}.difference_high': hi,
                                f'{judge}.pairs': float(diff.get('pairs', 0))})
                compared = diff.get('arms')
                for company, value in (diff.get('by_company') or {}).items():
                    metrics[f'{judge}.by_company.{company}'] = value
        agreement = data.get('agreement') or {}
        if agreement.get('spearman_episode_scores') is not None:
            metrics['agreement.spearman'] = agreement['spearman_episode_scores']
        set_name = path.parent.name
        log.run('aemon-comparisons', f'{set_name}/{path.stem.removeprefix("report_")}', path,
                {'set': set_name, 'judges': ','.join(data['judges']), 'compared': compared}, metrics, {'set': set_name, 'kind': 'comparison'})


# name -> what it is, training folder (None for the base), weights, and the runner reports that evaluated it
MODELS = {
    'aemon-v1': ('v1, the submitted adapter: LoRA r16 on Tiny Aya Global, 2 epochs on 3,891 teacher rows plus 51 corrections', 'final_pilot',
                 {'safetensors_sha256': '740c4a9b2f415c7b83162cb463d9eaec56a34feff090d9bf882680914eb3a112',
                  'gguf_sha256': '41794b5756b9e0f87c58dd14e451756d15c897d595886dee9921181298fdb9d1',
                  'location': 'cluster runs/final_pilot/adapter; https://huggingface.co/HatemSaadallah/tiny-aya-global-strategy-agent', 'status': 'submitted'},
                 ('dev_final_adapter', 'final_test_trained_adapter', 'test2_trained_adapter', 'screen3_v1_adapter', 'switch_v1', 'status_aqp_v1', 'status_dev_v1')),
    'aemon-v2': ('v2, DeepSeek corrective rows; failed its development screen', 'v2_deepseek',
                 {'safetensors_sha256': 'f4c419f7aefebbb128c4ecc2d92c1ade156e7dcd59e5d49b966c9068f063b57f', 'location': 'cluster runs/v2_deepseek/adapter',
                  'status': 'failed development screen'}, ()),
    'aemon-v3': ('v3, 7,502 rows (teacher plus extra), 1 epoch; failed its small screen, then better on test set 2 (exploratory)', 'v3',
                 {'safetensors_sha256': '8de2730fefa518a0100cbfd268d9c940ab2cf412c1277597f83a1900fa90a5c4',
                  'gguf_sha256': 'ea9193807fe9d5132878021bdf73de40ee84e2486f6688db9b3c3e29e04e1443', 'location': 'cluster runs/v3/adapter', 'status': 'exploratory'},
                 ('final_test_v3_adapter', 'test2_v3_adapter', 'screen3_v3_adapter', 'switch_v3', 'status_aqp_v3', 'status_dev_v3')),
    'aemon-third': ('the third development adapter', 'third_pilot',
                    {'safetensors_sha256': 'da98c6f33e1ab12c3e041c889f6f718d8b2c6e845982cbbf75fb81e9dc697241', 'location': 'cluster runs/third_pilot/adapter',
                     'status': 'development only'}, ()),
    'tiny-aya-global-base': ('Tiny Aya Global without an adapter (CohereLabs, bf16 GGUF)', None,
                             {'location': 'https://huggingface.co/CohereLabs/tiny-aya-global', 'status': 'baseline'},
                             ('dev_final_base', 'final_test_base_base', 'test2_base_base')),
}
REGISTERED = ('aemon-v1', 'aemon-v2', 'aemon-v3')  # versions 1, 2, 3 of aemon-adapter
LINKED = ('finished', 'end_to_end_success', 'refused_calls', 'mean_calls', 'episodes')


def models(log: Logger) -> None:
    client = log.client
    training_runs = {r.data.tags.get('adapter'): r for r in client.search_runs([log.experiment('aemon-training')], max_results=200)}
    eval_runs = client.search_runs([log.experiment('aemon-evaluation')], max_results=1000)
    experiment = log.experiment('aemon-evaluation')
    existing = {m.name: m for m in client.search_logged_models([experiment], max_results=200)}
    ids = {}
    for name, (description, folder, tags, reports) in MODELS.items():
        if name in existing:
            ids[name] = existing[name].model_id
            log.skipped += 1
            continue
        print(f'{"would register" if log.dry else "register"} model {name}')
        log.logged += 1
        if log.dry:
            continue
        label = TRAINED[folder][0] if folder else None
        source = training_runs.get(label)
        model = mlflow.create_external_model(name=name, source_run_id=source.info.run_id if source else None, experiment_id=experiment,
                                             model_type='peft-lora' if folder else 'base', tags={**tags, 'description': description},
                                             params={k: v for k, v in (source.data.params if source else {}).items() if k.startswith('lora') or k in ('rows', 'epochs', 'code_revision', 'base_model')})
        ids[name] = model.model_id
        for run in eval_runs:
            report = Path(run.data.tags.get('source', '')).stem
            if report in reports:
                set_name = run.data.tags.get('set', 'eval')
                values = {k: v for k, v in run.data.metrics.items() if k in LINKED or (k.startswith('judge.') and k.endswith('.mean'))}
                for k, v in values.items():
                    client.log_metric(run.info.run_id, f'{set_name}.{k}', v, model_id=model.model_id)
    if log.dry:
        return
    try:
        versions = client.search_model_versions("name = 'aemon-adapter'")
    except Exception:
        versions = []
    if not versions:
        client.create_registered_model('aemon-adapter', description='aemon adapters for Tiny Aya Global. v1 is the submission; v3 is exploratory.')
        for name in REGISTERED:
            mlflow.register_model(f'models:/{ids[name]}', 'aemon-adapter', tags={'model': name, 'status': MODELS[name][2]['status']})
        client.set_registered_model_alias('aemon-adapter', 'submitted', '1')
        client.set_registered_model_alias('aemon-adapter', 'exploratory', '3')
        print('registered aemon-adapter versions 1-3')


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args()
    HOME.mkdir(parents=True, exist_ok=True)
    log = Logger(a.dry_run)
    training(log)
    evaluation(log)
    comparisons(log)
    models(log)
    print(json.dumps({'tracking_uri': TRACKING, 'logged': log.logged, 'skipped_already_logged': log.skipped}))


if __name__ == '__main__':
    main()
