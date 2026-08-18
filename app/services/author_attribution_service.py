'''
AuthorAttributionService compares a disputed document's style against every
candidate author's latest AuthorStyleProfile and returns the closest match
with a confidence score, using an extension of Burrows' Delta: every feature
dimension across all three feature families (function word frequencies, avg
sentence length, vocabulary richness) is z-scored against the distribution
of that dimension across the candidate authors, then the disputed document's
z-scored vector is compared to each author's by mean absolute distance.
Lower delta means a closer style match.

Deltas are converted to a confidence score via softmax over negative delta,
so scores sum to 1 across candidates and the closest match gets the highest
score.

Needs at least two author profiles to compare against - z-scoring a single
profile against itself is meaningless, since every dimension would have
zero variance.

Assumes every candidate's latest profile was built from the same corpus-wide
function word list, which holds as long as they were all produced by the
same StyleProfileRebuildService.rebuild_all pass (see
test_shares_the_same_function_word_list_across_authors).
'''

import math
import statistics

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.author import Author
from app.models.author_style_feature import AuthorStyleFeature
from app.models.author_style_profile import AuthorStyleProfile
from app.services.document_analysis_service import DocumentAnalysisService

FeatureKey = tuple[str, str]


class AuthorAttributionService:
    def __init__(self, document_analysis_service: DocumentAnalysisService):
        self._document_analysis_service = document_analysis_service

    def attribute(self, db: Session, document_text: str) -> tuple[Author, float]:
        profiles = self._latest_profiles(db)
        if len(profiles) < 2:
            raise ValueError("At least two author profiles are required to attribute a disputed document")

        feature_keys = self._shared_feature_keys(profiles)
        function_words = next(
            (
                feature.feature_names for feature in profiles[0].features
                if feature.feature_type == "function_word_freq"
            ),
            None,
        )
        if function_words is None:
            raise ValueError(
                f"Author profile for '{profiles[0].author.name}' is missing function word "
                "frequency data; rebuild author profiles before attributing a disputed document"
            )

        disputed_features = self._document_analysis_service.analyze(document_text, function_words)
        disputed_vector = self._vector(disputed_features, feature_keys)
        author_vectors = {
            profile.author: self._vector(profile.features, feature_keys) for profile in profiles
        }

        deltas = self._deltas(disputed_vector, author_vectors)
        return self._best_match(deltas)

    @staticmethod
    def _latest_profiles(db: Session) -> list[AuthorStyleProfile]:
        # One max(id) per author, same "latest per group" pattern as
        # StyleProfileRebuildService._latest_model_versions.
        latest_profile_ids = (
            db.query(func.max(AuthorStyleProfile.id))
            .group_by(AuthorStyleProfile.author_id)
            .scalar_subquery()
        )

        return (
            db.query(AuthorStyleProfile)
            .options(joinedload(AuthorStyleProfile.features), joinedload(AuthorStyleProfile.author))
            .filter(AuthorStyleProfile.id.in_(latest_profile_ids))
            .all()
        )

    @staticmethod
    def _feature_keys(features: list[AuthorStyleFeature]) -> list[FeatureKey]:
        return [
            (feature.feature_type, name)
            for feature in sorted(features, key=lambda feature: feature.feature_type)
            for name in feature.feature_names
        ]

    def _shared_feature_keys(self, profiles: list[AuthorStyleProfile]) -> list[FeatureKey]:
        # Every profile is expected to come from the same
        # StyleProfileRebuildService.rebuild_all pass and therefore share one
        # feature schema (see class docstring). Verify that rather than
        # silently comparing authors on mismatched dimensions.
        keys_by_author_id = {
            profile.author_id: self._feature_keys(profile.features)
            for profile in profiles
        }

        expected_keys = next(iter(keys_by_author_id.values()), None)
        if expected_keys is None:
            raise ValueError("No author profiles available to attribute a disputed document")

        mismatched_author_ids = [
            author_id for author_id, keys in keys_by_author_id.items() if keys != expected_keys
        ]
        if mismatched_author_ids:
            raise ValueError(
                f"Author profiles have inconsistent feature sets (author_ids={mismatched_author_ids}); "
                "rebuild all author profiles together before attributing a disputed document"
            )

        return expected_keys

    @staticmethod
    def _vector(features: list[AuthorStyleFeature], feature_keys: list[FeatureKey]) -> list[float]:
        values_by_key = {
            (feature.feature_type, name): value
            for feature in features
            for name, value in zip(feature.feature_names, feature.profile_vector)
        }
        return [values_by_key[key] for key in feature_keys]

    @staticmethod
    def _deltas(
        disputed_vector: list[float], author_vectors: dict[Author, list[float]]
    ) -> dict[Author, float]:
        num_dims = len(disputed_vector)
        vectors = list(author_vectors.values())

        means = [statistics.fmean(vector[i] for vector in vectors) for i in range(num_dims)]
        stdevs = [statistics.pstdev(vector[i] for vector in vectors) for i in range(num_dims)]

        def z_score(vector: list[float]) -> list[float]:
            return [
                (vector[i] - means[i]) / stdevs[i] if stdevs[i] else 0.0
                for i in range(num_dims)
            ]

        disputed_z = z_score(disputed_vector)
        return {
            author: statistics.fmean(abs(d - a) for d, a in zip(disputed_z, z_score(vector)))
            for author, vector in author_vectors.items()
        }

    @staticmethod
    def _best_match(deltas: dict[Author, float]) -> tuple[Author, float]:
        min_delta = min(deltas.values())
        weights = {author: math.exp(-(delta - min_delta)) for author, delta in deltas.items()}
        total_weight = sum(weights.values())
        scores = {author: weight / total_weight for author, weight in weights.items()}

        best_author = max(scores, key=scores.get)
        return best_author, scores[best_author]
