"""Pre-downloads the NLTK tokenizer data used by word_tokenize/sent_tokenize
so it doesn't have to be fetched (and can't silently fail) at runtime.

Uses the Python API (not the `nltk.downloader` CLI) with raise_on_error=True:
the CLI prompts interactively on a failed download, which hangs/EOFs under
`docker build`'s non-interactive stdin. Retries absorb transient DNS blips
from nltk's SSRF-hardened urlopen (nltk/pathsec.py) failing a resolution.
"""

import os
import time

import nltk

DOWNLOAD_DIR = os.environ.get("NLTK_DATA", "/usr/local/share/nltk_data")

for pkg in ("punkt", "punkt_tab"):
    for attempt in range(1, 4):
        try:
            nltk.download(pkg, download_dir=DOWNLOAD_DIR, quiet=True, raise_on_error=True)
            break
        except Exception as e:
            print(f"[{pkg}] attempt {attempt} failed: {e}")
            if attempt == 3:
                raise
            time.sleep(5)
