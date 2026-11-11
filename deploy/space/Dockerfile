# aemon as a hosted demo: the React interface, the FastAPI app and llama.cpp serving Tiny Aya with both adapters,
# in one container. Built for a Hugging Face Docker Space (port 7860, user 1000); it runs anywhere Docker does.
FROM node:22-slim AS web
WORKDIR /web
COPY app/web/package.json app/web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY app/web ./
RUN npm run build

FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv ca-certificates curl libgomp1 \
    && rm -rf /var/lib/apt/lists/*
# llama.cpp b12032, the release the evaluated runs used (CPU build), checked against its digest
RUN mkdir -p /opt/llama && cd /tmp \
    && curl -fsSL -o llama.tar.gz https://github.com/ggml-org/llama.cpp/releases/download/b12032/llama-b12032-bin-ubuntu-x64.tar.gz \
    && echo "9f10432ca3f66ef003a7a540aaffb9da0acadaefd05404521b9ab7a2436af304  llama.tar.gz" | sha256sum -c \
    && tar -xzf llama.tar.gz -C /opt/llama --strip-components=1 && rm llama.tar.gz
COPY app/requirements-app.txt /tmp/requirements-app.txt
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements-app.txt huggingface_hub==1.33.0
# The 4-bit base model (CohereLabs, CC-BY-NC 4.0), fetched at build time at a fixed revision
RUN /opt/venv/bin/python -c "from huggingface_hub import hf_hub_download; hf_hub_download('CohereLabs/tiny-aya-global-GGUF', 'tiny-aya-global-q4_k_m.gguf', revision='a602ea7eeec3a4ad6f77a1b8cf6a53512824922b', local_dir='/opt/model')" \
    && rm -rf /opt/model/.cache
WORKDIR /home/ubuntu/aemon
COPY --chown=1000:1000 . .
COPY --chown=1000:1000 --from=web /web/dist app/web/dist
RUN chmod +x start.sh
USER 1000
ENV HOME=/home/ubuntu AEMON_SEED=/home/ubuntu/aemon/seed/history.json LEXSI_DATA=/tmp/aemon-data \
    MAX_TURNS=45 PYTHONDONTWRITEBYTECODE=1 LD_LIBRARY_PATH=/opt/llama
# The shared test account comes from two secrets set where this is hosted: AEMON_TEST_USER and AEMON_TEST_PASSWORD
EXPOSE 7860
CMD ["./start.sh"]
