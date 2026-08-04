from sqlalchemy.orm import Session

from app.extensions import SessionLocal
from app.models.author import Author
from app.models.author_style_profile import AuthorStyleProfile
from app.models.document import Document
from app.services.style_profile_service import StyleProfileService

'''
Rebuilds every author's style profile from the current state of the whole
corpus. Triggered as a background task after each document upload (see
documents_router) so uploads don't block on it.

Each author gets a new AuthorStyleProfile row rather than an overwritten
one - model_version is incremented per author on every rebuild, so old
profiles stick around as a history of how an author's profile has been
refined over time. Authors with no documents are skipped; they have
nothing to build a profile from.
'''


class StyleProfileRebuildService:
    def __init__(self, style_profile_service: StyleProfileService | None = None):
        self._style_profile_service = style_profile_service or StyleProfileService()

    def rebuild_all_in_background(self) -> None:
        # Opens its own session rather than reusing the request's: this runs
        # as a FastAPI background task, after the response is sent, by which
        # point the request's session may already be closed.
        db = SessionLocal()
        try:
            self.rebuild_all(db)
        finally:
            db.close()

    def rebuild_all(self, db: Session) -> None:
        all_documents = db.query(Document).all()
        function_words = self._style_profile_service.determine_function_words(all_documents)

        authors = db.query(Author).all()
        for author in authors:
            if not author.documents:
                continue

            model_version = self._next_model_version(db, author.id)
            profile = self._style_profile_service.build_profile(
                author, author.documents, function_words, model_version=model_version
            )
            db.add(profile)

        db.commit()

    def _next_model_version(self, db: Session, author_id: int) -> str:
        latest_profile = (
            db.query(AuthorStyleProfile)
            .filter(AuthorStyleProfile.author_id == author_id)
            .order_by(AuthorStyleProfile.id.desc())
            .first()
        )

        if latest_profile is None:
            return "v1"

        latest_version_number = int(latest_profile.model_version.removeprefix("v"))
        return f"v{latest_version_number + 1}"
