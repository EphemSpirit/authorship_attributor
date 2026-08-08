'''
StyleProfileService turns an author's raw document text into the feature
vectors AUTHOR_STYLE_PROFILE / AUTHOR_STYLE_FEATURE are built from, following
Burrows' Delta: relative frequencies of the corpus's most frequent words,
z-scored against other authors at comparison time (comparison itself isn't
implemented here). "Most frequent words" rather than a fixed function-word
list, because that's what classic Delta uses and it keeps the door open to
picking up author-specific tics beyond closed-class words.

Because that word list is a property of the whole corpus, not any single
author, it has to be computed once and reused: call determine_function_words
with every document you're building profiles from this run, then pass the
result into build_profile for each author. Building two authors' profiles
against different word lists would make their vectors incomparable.

determine_function_words and build_profile work entirely off cached
per-document stats (Document.token_counts/sentence_count/
total_sentence_word_count) rather than re-tokenizing raw text, so rebuilding
every author's profile from the whole corpus - which happens on every
upload - stays cheap as the corpus grows. Those cached stats are produced
once, at upload time, by compute_document_stats.

Two more feature families ride alongside function words:
  - avg_sentence_length: mean words per sentence, a cheap syntactic signal.
  - vocabulary_richness: type-token ratio (unique words / total words)
    rather than raw vocabulary size, since raw size mostly just measures
    how much text an author has uploaded rather than how they write.

This service only computes AuthorStyleProfile/AuthorStyleFeature objects; it
does not add or commit them, so callers decide persistence.
'''

from collections import Counter

from nltk.tokenize import sent_tokenize, word_tokenize

from app.models.author import Author
from app.models.author_style_feature import AuthorStyleFeature
from app.models.author_style_profile import AuthorStyleProfile
from app.models.document import Document

DEFAULT_MODEL_VERSION = "v1"
DEFAULT_NUM_FUNCTION_WORDS = 100


class StyleProfileService:
    def compute_document_stats(self, text: str) -> dict:
        tokens = self._tokenize_words(text)
        sentence_lengths = [
            len(self._tokenize_words(sentence)) for sentence in sent_tokenize(text)
        ]

        return {
            "token_counts": dict(Counter(tokens)),
            "sentence_count": len(sentence_lengths),
            "total_sentence_word_count": sum(sentence_lengths),
        }

    @staticmethod
    def determine_function_words(
        self,
        corpus_documents: list[Document],
        num_words: int = DEFAULT_NUM_FUNCTION_WORDS,
    ) -> list[str]:
        total_counts = Counter()
        for document in corpus_documents:
            total_counts.update(document.token_counts)

        return [word for word, _count in total_counts.most_common(num_words)]

    def build_profile(
        self,
        author: Author,
        documents: list[Document],
        function_words: list[str],
        model_version: str = DEFAULT_MODEL_VERSION,
    ) -> AuthorStyleProfile:
        token_counts = Counter()
        sentence_count = 0
        total_sentence_word_count = 0
        for document in documents:
            token_counts.update(document.token_counts)
            sentence_count += document.sentence_count
            total_sentence_word_count += document.total_sentence_word_count

        features = [
            self._function_word_freq_feature(token_counts, function_words),
            self._avg_sentence_length_feature(sentence_count, total_sentence_word_count),
            self._vocabulary_richness_feature(token_counts),
        ]

        return AuthorStyleProfile(
            author_id=author.id,
            num_documents_used=len(documents),
            model_version=model_version,
            features=features,
        )

    @staticmethod
    def _tokenize_words(self, text: str) -> list[str]:
        return [token.lower() for token in word_tokenize(text) if token.isalpha()]


    @staticmethod
    def _function_word_freq_feature(
        self, token_counts: Counter, function_words: list[str]
    ) -> AuthorStyleFeature:
        total_tokens = sum(token_counts.values()) or 1
        profile_vector = [token_counts[word] / total_tokens for word in function_words]

        return AuthorStyleFeature(
            feature_type="function_word_freq",
            profile_vector=profile_vector,
            feature_names=function_words,
        )

    @staticmethod
    def _avg_sentence_length_feature(
        self, sentence_count: int, total_sentence_word_count: int
    ) -> AuthorStyleFeature:
        avg_length = total_sentence_word_count / sentence_count if sentence_count else 0.0

        return AuthorStyleFeature(
            feature_type="avg_sentence_length",
            profile_vector=[avg_length],
            feature_names=["avg_sentence_length"],
        )

    @staticmethod
    def _vocabulary_richness_feature(self, token_counts: Counter) -> AuthorStyleFeature:
        total_tokens = sum(token_counts.values())
        richness = len(token_counts) / total_tokens if total_tokens else 0.0

        return AuthorStyleFeature(
            feature_type="vocabulary_richness",
            profile_vector=[richness],
            feature_names=["type_token_ratio"],
        )
