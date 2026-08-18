# Author Attribution

A stylometry-based authorship attribution backend. It builds a statistical
"fingerprint" of how each known author writes, from a corpus of documents
credited to them, and exposes those fingerprints over a small FastAPI
service.

It implements classic **authorship attribution**: given a document of
disputed or unknown authorship, it extracts the same style features used
for known authors, compares them against every candidate author's
fingerprint, and reports which one it most likely came from, with a
confidence score.

## How it works

1. **Upload.** A `.docx` file is uploaded via `POST /documents/upload-known`
   along with the name(s) of the author(s) it should be credited to.
   Content is hashed (SHA-256) so the same document uploaded twice is
   treated as one row — a second upload just adds new co-authors to it
   rather than duplicating it.
2. **Cache stats at upload time.** The document's raw text is tokenized once
   (word tokens + sentence boundaries via NLTK) and the resulting counts are
   cached on the `Document` row. This means later profile rebuilds work off
   cheap cached counts instead of re-tokenizing every document's raw text
   every time.
3. **Rebuild profiles in the background.** After every upload, a background
   task recomputes **every** author's style profile from the current state
   of the whole corpus:
   - The corpus's N most frequent words (default 100) are recomputed and
     used as the "function word" feature set — this is the classic
     [Burrows' Delta](https://en.wikipedia.org/wiki/Delta_(letter)#Stylometry)
     approach of using the corpus's own most-frequent words rather than a
     fixed function-word list, so profiles can pick up author-specific tics
     beyond closed-class words.
   - Each author with at least one document gets a new, versioned
     `AuthorStyleProfile` (`v1`, `v2`, `v3`, ...) built from **three**
     feature families:

     | Feature type          | What it captures                                   |
     |------------------------|----------------------------------------------------|
     | `function_word_freq`   | Relative frequency of each corpus function word    |
     | `avg_sentence_length`  | Mean words per sentence                            |
     | `vocabulary_richness`  | Type-token ratio (unique words / total words)      |

   - Old profiles are never overwritten, so an author's fingerprint history
     is preserved and later model versions can be compared against earlier
     baselines.
4. **Read a profile.** `GET /authors/{id}/style-profile` returns an
   author's most recently computed profile and all of its features.
5. **Attribute a disputed document.** A `.docx` file of unknown authorship
   is uploaded via `POST /documents/upload-disputed`. It's analyzed the same
   way known documents are (same tokenization, same function-word list,
   same three feature families) but never persisted or folded into any
   author's profile. Its feature vector is then compared against every
   candidate author's latest profile per Burrows' Delta: each feature
   dimension is z-scored against the distribution of that dimension across
   the candidate authors, and the disputed document's z-scored vector is
   compared to each author's by mean absolute distance (lower = closer
   match). Distances are converted to a confidence score via softmax, so
   scores sum to 1 across candidates and the closest match gets the
   highest score. Requires at least two candidate authors with a style
   profile to compare against.

## Data model

```
Author ──< document_authors >── Document
  │
  └──< AuthorStyleProfile ──< AuthorStyleFeature
```

- **Author** — `id`, `name` (unique), `author_metadata` (free-form JSON).
  Not meant to hold any stylometric data itself.
- **Document** — one ingested writing sample. `content_hash` is globally
  unique; `status`/`error_message` track the (separate) analysis stage;
  `token_counts` / `sentence_count` / `total_sentence_word_count` are the
  stats cached at upload time.
- **document_authors** — many-to-many join table between `Document` and
  `Author`, so co-authored documents are supported and deleting an author
  only removes their credit, not the document.
- **AuthorStyleProfile** — one stylometric fingerprint "run" for an author
  under a given `model_version`. Kept around historically rather than
  overwritten.
- **AuthorStyleFeature** — one feature family's vector (`function_word_freq`,
  `avg_sentence_length`, or `vocabulary_richness`) belonging to a profile.

## API reference

### `POST /documents/upload-known`

Upload a `.docx` document and credit it to one or more known authors. New
author names are created automatically (title-cased) if they don't already
exist.

```bash
curl -X POST "http://localhost:8000/documents/upload-known?author_names=Stephen%20King" \
  -F "file=@manuscript.docx"

# Co-authored document:
curl -X POST "http://localhost:8000/documents/upload-known?author_names=Jane%20Doe&author_names=John%20Smith" \
  -F "file=@paper.docx"
```

Response (`200 OK`):

```json
{
  "id": 1,
  "authors": [{ "id": 1, "name": "Stephen King" }],
  "filename": "manuscript.docx",
  "content_hash": "3f786850e387550fdab836ed7e6dc881de23001b",
  "text": "It was a dark and stormy night...",
  "word_count": 5123,
  "status": "pending",
  "error_message": null,
  "created_at": "2026-07-21T17:25:46.221560"
}
```

Fails with `422` if the file isn't a readable `.docx`, no `author_names`
are supplied, or this exact content is already credited to every author
named in the request.

### `POST /documents/upload-disputed`

Upload a `.docx` document of disputed/unknown authorship and get back the
most likely author from those already registered, with a confidence score.
Nothing is persisted — the document is analyzed and discarded.

```bash
curl -X POST "http://localhost:8000/documents/upload-disputed" \
  -F "document=@questioned.docx"
```

Response (`200 OK`):

```json
{
  "predicted_author": { "id": 1, "name": "Stephen King" },
  "confidence_score": 0.87
}
```

Fails with `422` if the file isn't a readable `.docx`, or fewer than two
candidate authors have a style profile to compare against.

### `GET /documents/{document_name}`

Look up a document by filename.

### `GET /authors`

List every registered author.

### `POST /authors`

Register an author directly, without uploading a document for them yet.

```json
{
  "name": "Stephen King",
  "author_metadata": { "bio": "He was a man", "age": 65 }
}
```

### `GET /authors/{author_id}` · `PUT /authors/{author_id}` · `DELETE /authors/{author_id}`

Standard fetch / update / delete for a single author.

### `GET /authors/{author_id}/style-profile`

Returns the author's latest style profile.

```json
{
  "id": 1,
  "author_id": 1,
  "num_documents_used": 12,
  "model_version": "v2",
  "computed_at": "2026-07-21T17:25:46.221560",
  "features": [
    {
      "id": 1,
      "feature_type": "function_word_freq",
      "profile_vector": [0.021, 0.104, 0.0087],
      "feature_names": ["the", "of", "and"]
    },
    {
      "id": 2,
      "feature_type": "avg_sentence_length",
      "profile_vector": [18.4],
      "feature_names": ["avg_sentence_length"]
    },
    {
      "id": 3,
      "feature_type": "vocabulary_richness",
      "profile_vector": [0.31],
      "feature_names": ["type_token_ratio"]
    }
  ]
}
```

`num_documents_used` and `model_version` tell you how much evidence this
fingerprint is based on, and let you tell a fresh, thin profile (`v1`, one
document) apart from a well-established one (`v6`, forty documents).

Interactive Swagger docs are available at `/docs` once the app is running.

## Getting started

### Prerequisites

- Python 3.11+ (developed against 3.14)
- A running PostgreSQL instance
- `pip`

### Install

```bash
python3 -m venv .venv
source .venv/bin/activate

pip install "fastapi[standard]" "sqlalchemy>=2.0" alembic psycopg2-binary \
            python-dotenv nltk python-docx pytest
```

> No `requirements.txt` is checked in yet — the command above installs the
> versions this project was built against.

Download the NLTK tokenizer data used by `word_tokenize`/`sent_tokenize`:

```bash
python -m nltk.downloader punkt punkt_tab
```

### Set up the database

```bash
alembic upgrade head
```

(The app also calls `Base.metadata.create_all` on startup, so tables will
be created even without running migrations first — but `alembic upgrade
head` is the source of truth for schema history.)

### Run

```bash
fastapi dev
```

The API is now available at `http://localhost:8000`, with interactive docs
at `http://localhost:8000/docs`.

## Running tests

```bash
pytest
```

Tests run against the SQLite database at `TEST_DATABASE_URL` (not your dev
Postgres database), with tables created fresh and rows cleaned up between
tests. Background style-profile rebuilds are redirected to the same test
session so upload tests don't leak into your real database.

## Roadmap

- **Ranked candidate list.** `upload-disputed` currently returns only the
  single closest-matching author; returning the full ranked list of
  candidates with their scores would give more visibility into close calls.
- **Authentication.** `APP_SECRET_KEY` is present in `.env` but not yet
  read anywhere; the API currently has no auth.
- A `requirements.txt`/`pyproject.toml` for reproducible installs.
