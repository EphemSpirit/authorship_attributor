'''
DocumentAnalysisService turns a disputed document's raw text into the same
AuthorStyleFeature vectors StyleProfileService builds for known authors, so
the two are directly comparable. Unlike a known-author upload, a disputed
document never has cached per-document stats or an Author to attach a
profile to - it's measured once, at request time, against a function-word
list borrowed from whichever author profiles it's about to be compared
against, and nothing here is persisted.
'''

from collections import Counter

from app.models.author_style_feature import AuthorStyleFeature
from app.services.style_profile_service import StyleProfileService


class DocumentAnalysisService:
    def __init__(self, style_profile_service: StyleProfileService | None = None):
        self._style_profile_service = style_profile_service or StyleProfileService()

    def analyze(self, text: str, function_words: list[str]) -> list[AuthorStyleFeature]:
        stats = self._style_profile_service.compute_document_stats(text)

        return self._style_profile_service.build_features(
            Counter(stats["token_counts"]),
            stats["sentence_count"],
            stats["total_sentence_word_count"],
            function_words,
        )
