FROM python:3.12-slim

# CPU-only PyTorch; torch headers aren't needed to run the model
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir --no-compile \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        -r /tmp/requirements.txt \
    && rm -rf /usr/local/lib/python3.12/site-packages/torch/include /tmp/requirements.txt

WORKDIR /app
COPY normalize.py server.py ./

# The voice model is not part of the image: it's downloaded from Silero
# into /data on first start (see README for its license)
CMD ["python", "-u", "server.py", "--uri", "tcp://0.0.0.0:10200", "--data-dir", "/data", "--options", "/data/options.json"]

LABEL \
    io.hass.type="addon" \
    org.opencontainers.image.source="https://github.com/dnlrz42/ha-silero-tts" \
    org.opencontainers.image.licenses="MIT"
