FROM python:3.12-slim

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# The natural voice (app/voice/): Piper's Spanish model, with the woman's voice
# the family chose. In its own layer, downloaded once: about 77 MB, never changes.
ARG VOICE=es_ES-sharvard-medium
ARG VOICE_URL=https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/sharvard/medium
RUN mkdir -p /opt/voices && python -c "import urllib.request as u; \
[u.urlretrieve(f'${VOICE_URL}/${VOICE}{ext}?download=true', f'/opt/voices/${VOICE}{ext}') \
 for ext in ('.onnx', '.onnx.json')]"
ENV MISSIONBOARD_VOICE_MODEL=/opt/voices/es_ES-sharvard-medium.onnx

COPY app ./app

ENV MISSIONBOARD_DATA_DIR=/srv/data
EXPOSE 8003

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
