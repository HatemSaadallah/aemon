"""aemon on Modal: the interface, the app and llama.cpp (base model, version 1 and version 3 adapters) in one container
that sleeps when nobody is using it. Without AEMON_GPU it runs on CPU cores with the plain CPU build of llama.cpp.

    python scripts/release/build_space.py --out /tmp/aemon_build      # the files: app, agent package, dossier, adapters, seed
    npm --prefix app/web run build                                    # the interface
    AEMON_BUILD=/tmp/aemon_build [AEMON_GPU=T4] modal deploy deploy/modal/aemon_modal.py

The shared test account comes from the Modal secret `aemon-test-account` (AEMON_TEST_USER, AEMON_TEST_PASSWORD).
History lives on the volume `aemon-data`, so it survives the container sleeping.
"""

import os
import subprocess
from pathlib import Path

import modal

BUILD = os.environ.get('AEMON_BUILD', '/tmp/aemon_build')
# this file is imported again inside the container, at /root/aemon_modal.py, where there is no repository above it:
# .parent never raises (parents[2] did, and the container crash-looped)
DIST = str(Path(__file__).resolve().parent.parent.parent / 'app/web/dist')
RELEASE = 'https://github.com/ggml-org/llama.cpp/releases/download/b12032/'  # the evaluated release
# Modal asks for a payment method before a GPU can be used; with AEMON_GPU unset the container has CPU cores only
GPU = os.environ.get('AEMON_GPU')
CORES = 8
if GPU:
    BASE, LLAMA, SHA, HARDWARE = 'nvidia/cuda:12.8.1-runtime-ubuntu24.04', 'llama-b12032-bin-ubuntu-cuda-12.8-x64.tar.gz', None, {'gpu': GPU}
else:
    BASE, LLAMA, SHA = 'ubuntu:24.04', 'llama-b12032-bin-ubuntu-x64.tar.gz', '9f10432ca3f66ef003a7a540aaffb9da0acadaefd05404521b9ab7a2436af304'
    HARDWARE = {'cpu': float(CORES), 'memory': 12288}
REQUIREMENTS = ['fastapi==0.162.0', 'uvicorn==0.54.0', 'pydantic==2.14.2', 'starlette==1.10.0', 'python-multipart==0.0.33', 'orjson==3.13.0',
                'email-validator==2.3.0', 'ddgs==9.16.1', 'primp==2.0.1', 'websocket-client==1.9.2', 'pdfminer.six==20251230', 'jsonschema==4.26.0',
                'tenacity==9.2.1', 'python-dotenv==1.2.4', 'huggingface_hub==1.33.0']  # app/requirements-app.txt

image = (
    modal.Image.from_registry(BASE, add_python='3.12')
    .apt_install('curl', 'ca-certificates', 'libgomp1')
    .run_commands(f'mkdir -p /opt/llama && curl -fsSL -o /tmp/llama.tgz {RELEASE}{LLAMA}'
                  + (f' && echo "{SHA}  /tmp/llama.tgz" | sha256sum -c -' if SHA else '')
                  + ' && tar -xzf /tmp/llama.tgz -C /opt/llama --strip-components=1 && rm /tmp/llama.tgz && test -x /opt/llama/llama-server')
    .pip_install(*REQUIREMENTS)
    .run_commands("python -c \"from huggingface_hub import hf_hub_download; hf_hub_download('CohereLabs/tiny-aya-global-GGUF', "
                  "'tiny-aya-global-q4_k_m.gguf', revision='a602ea7eeec3a4ad6f77a1b8cf6a53512824922b', local_dir='/opt/model')\"")
    # the hardware choice is made at deploy time and fixed in the image, so the container does not have to guess it
    .env({'AEMON_LLAMA_HW': '-ngl 99' if GPU else f'-ngl 0 -t {CORES}'})
    .add_local_dir(BUILD, '/aemon', copy=True, ignore=['Dockerfile', 'start.sh', 'README.md', '.gitattributes', '.dockerignore'])
    .add_local_dir(DIST, '/aemon/app/web/dist', copy=True)
)
app = modal.App('aemon', image=image)
data = modal.Volume.from_name('aemon-data', create_if_missing=True)


@app.function(**HARDWARE, volumes={'/data': data}, secrets=[modal.Secret.from_name('aemon-test-account')],
              max_containers=1, scaledown_window=300, timeout=24 * 3600)
@modal.concurrent(max_inputs=200)
@modal.web_server(7860, startup_timeout=600)
def serve() -> None:
    import sys
    env = {**os.environ, 'LD_LIBRARY_PATH': '/opt/llama:' + os.environ.get('LD_LIBRARY_PATH', ''), 'LEXSI_DATA': '/data',
           'AEMON_SEED': '/aemon/seed/history.json', 'CODE_REVISION': Path('/aemon/REVISION').read_text().strip(), 'PYTHONDONTWRITEBYTECODE': '1'}
    subprocess.Popen(['/opt/llama/llama-server', '-m', '/opt/model/tiny-aya-global-q4_k_m.gguf', '--lora', '/aemon/adapters/final_adapter.gguf',
                      '--lora', '/aemon/adapters/v3_adapter.gguf', '--lora-init-without-apply', *os.environ['AEMON_LLAMA_HW'].split(),
                      '-c', '12288', '--parallel', '1', '--jinja', '--reasoning-format', 'none', '--host', '127.0.0.1', '--port', '8091', '--no-webui'], env=env)
    subprocess.Popen([sys.executable, '-m', 'uvicorn', 'server:app', '--host', '0.0.0.0', '--port', '7860', '--app-dir', '/aemon/app', '--log-level', 'warning'],
                     env=env, cwd='/aemon')
