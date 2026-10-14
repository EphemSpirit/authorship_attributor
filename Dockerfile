FROM python:3.14-slim

WORKDIR /app

# Install Python deps first so this layer is cached unless deps change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the NLTK tokenizer data used by word_tokenize/sent_tokenize
# so it doesn't have to be fetched (and can't silently fail) at runtime.
ENV NLTK_DATA=/usr/local/share/nltk_data
COPY docker/download_nltk_data.py .
RUN python download_nltk_data.py && rm download_nltk_data.py

COPY . .

RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Apply migrations, then start the API.
CMD ["sh", "-c", "alembic upgrade head && fastapi dev main.py --host 0.0.0.0 --port 8000"]
