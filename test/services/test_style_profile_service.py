import pytest

from app.models import Author, Document
from app.services.style_profile_service import StyleProfileService


@pytest.fixture
def service():
    return StyleProfileService()


def _document(text: str) -> Document:
    stats = StyleProfileService().compute_document_stats(text)
    return Document(text=text, word_count=len(text.split()), **stats)


class TestComputeDocumentStats:
    def test_counts_alpha_tokens_case_insensitively(self, service):
        stats = service.compute_document_stats("The the CAT sat.")

        assert stats["token_counts"] == {"the": 2, "cat": 1, "sat": 1}

    def test_ignores_punctuation_only_tokens(self, service):
        stats = service.compute_document_stats("Wait -- really?")

        assert stats["token_counts"] == {"wait": 1, "really": 1}

    def test_counts_sentences_and_their_total_word_length(self, service):
        stats = service.compute_document_stats("One two three. Four five.")

        assert stats["sentence_count"] == 2
        assert stats["total_sentence_word_count"] == 5

    def test_empty_text(self, service):
        stats = service.compute_document_stats("")

        assert stats["token_counts"] == {}
        assert stats["sentence_count"] == 0
        assert stats["total_sentence_word_count"] == 0


class TestDetermineFunctionWords:
    def test_ranks_words_by_corpus_wide_frequency(self, service):
        documents = [
            _document("the cat sat on the mat"),
            _document("the dog sat on the log"),
        ]

        function_words = service.determine_function_words(documents, num_words=3)

        assert function_words == ["the", "sat", "on"]

    def test_respects_num_words(self, service):
        documents = [_document("apple banana cherry date")]

        function_words = service.determine_function_words(documents, num_words=2)

        assert len(function_words) == 2

    def test_lowercases_and_ignores_punctuation(self, service):
        documents = [_document("Hello, hello! HELLO.")]

        function_words = service.determine_function_words(documents, num_words=1)

        assert function_words == ["hello"]


class TestBuildProfile:
    def test_sets_profile_metadata(self, service):
        author = Author(id=1, name="Test Author")
        documents = [_document("The quick brown fox.")]

        profile = service.build_profile(author, documents, function_words=["the"])

        assert profile.author_id == author.id
        assert profile.num_documents_used == 1
        assert profile.model_version == "v1"

    def test_function_word_freq_feature_is_relative_frequency(self, service):
        author = Author(id=1, name="Test Author")
        documents = [_document("the cat sat on the mat")]

        profile = service.build_profile(author, documents, function_words=["the", "cat", "dog"])
        feature = next(f for f in profile.features if f.feature_type == "function_word_freq")

        # 6 alpha tokens total: "the" x2, "cat" x1, "dog" x0
        assert feature.feature_names == ["the", "cat", "dog"]
        assert feature.profile_vector == pytest.approx([2 / 6, 1 / 6, 0.0])

    def test_avg_sentence_length_feature(self, service):
        author = Author(id=1, name="Test Author")
        documents = [_document("One two three. Four five.")]

        profile = service.build_profile(author, documents, function_words=[])
        feature = next(f for f in profile.features if f.feature_type == "avg_sentence_length")

        # sentences of length 3 and 2 -> average 2.5
        assert feature.profile_vector == pytest.approx([2.5])

    def test_vocabulary_richness_feature(self, service):
        author = Author(id=1, name="Test Author")
        documents = [_document("the the cat sat")]

        profile = service.build_profile(author, documents, function_words=[])
        feature = next(f for f in profile.features if f.feature_type == "vocabulary_richness")

        # 3 unique tokens ("the", "cat", "sat") out of 4 total
        assert feature.profile_vector == pytest.approx([3 / 4])

    def test_handles_empty_documents_without_dividing_by_zero(self, service):
        author = Author(id=1, name="Test Author")
        documents = [_document("")]

        profile = service.build_profile(author, documents, function_words=["the"])

        function_words_feature = next(f for f in profile.features if f.feature_type == "function_word_freq")
        sentence_feature = next(f for f in profile.features if f.feature_type == "avg_sentence_length")
        vocab_feature = next(f for f in profile.features if f.feature_type == "vocabulary_richness")

        assert function_words_feature.profile_vector == [0.0]
        assert sentence_feature.profile_vector == [0.0]
        assert vocab_feature.profile_vector == [0.0]

    def test_aggregates_across_multiple_documents(self, service):
        author = Author(id=1, name="Test Author")
        documents = [_document("the cat"), _document("the dog")]

        profile = service.build_profile(author, documents, function_words=["the"])
        feature = next(f for f in profile.features if f.feature_type == "function_word_freq")

        assert profile.num_documents_used == 2
        # "the" appears twice out of 4 total alpha tokens across both docs
        assert feature.profile_vector == pytest.approx([2 / 4])
