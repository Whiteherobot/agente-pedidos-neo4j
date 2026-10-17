FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY agente ./agente
COPY api ./api
COPY front ./front
COPY data ./data
RUN useradd --create-home agente
USER agente
EXPOSE 8000
CMD ["uvicorn", "api.main:crear_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
