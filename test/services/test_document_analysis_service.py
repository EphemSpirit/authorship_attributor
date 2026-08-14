import pytest

from app.models import Author, Document
from app.services.document_analysis_service import DocumentAnalysisService
from app.services.style_profile_service import StyleProfileService


@pytest.fixture
def service():
    return DocumentAnalysisService()


class TestAnalyze:
    def test_returns_the_three_feature_families(self, service):
        features = service.analyze("The quick brown fox jumps.", function_words=["the"])

        assert {feature.feature_type for feature in features} == {
            "function_word_freq", "avg_sentence_length", "vocabulary_richness",
        }

    def test_function_word_freq_uses_the_given_word_list(self, service):
        features = service.analyze("the cat sat on the mat", function_words=["the", "cat", "dog"])
        feature = next(f for f in features if f.feature_type == "function_word_freq")

        # 6 alpha tokens total: "the" x2, "cat" x1, "dog" x0
        assert feature.feature_names == ["the", "cat", "dog"]
        assert feature.profile_vector == pytest.approx([2 / 6, 1 / 6, 0.0])

    def test_avg_sentence_length_feature(self, service):
        features = service.analyze("One two three. Four five.", function_words=[])
        feature = next(f for f in features if f.feature_type == "avg_sentence_length")

        assert feature.profile_vector == pytest.approx([2.5])

    def test_matches_style_profile_service_output_for_an_equivalent_document(self, service):
        text = "One two three. Four five six seven."
        function_words = ["one", "four"]

        stats = StyleProfileService().compute_document_stats(text)
        document = Document(text=text, word_count=len(text.split()), **stats)
        profile = StyleProfileService().build_profile(
            Author(id=1, name="Reference"), [document], function_words
        )

        disputed_features = service.analyze(text, function_words)

        actual = {(f.feature_type, tuple(f.profile_vector)) for f in disputed_features}
        expected = {(f.feature_type, tuple(f.profile_vector)) for f in profile.features}
        assert actual == expected
