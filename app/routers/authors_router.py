from fastapi import Depends, HTTPException, Path, APIRouter, status
from app.extensions import get_db
from typing import Annotated
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from app.models import Author, AuthorStyleProfile
from app.schemas.author_request import AuthorRequest
from app.schemas.author_response import AuthorResponse
from app.schemas.author_style_profile_response import AuthorStyleProfileResponse

router = APIRouter(
    prefix="/authors",
    tags=["Authors"]
)


@router.get("", response_model=list[AuthorResponse], status_code=status.HTTP_200_OK)
def get_authors(db: Annotated[Session, Depends(get_db)]):
    return db.query(Author).all()

"""
Main way to create an author is via document upload. This route exists for
if you want to register an author in the database, but don't yet have any documents to feed
the documents_router/upload endpoint
"""
@router.post("", response_model=AuthorResponse, status_code=status.HTTP_201_CREATED)
def create_author(author_request: AuthorRequest, db: Annotated[Session, Depends(get_db)]):
    try:
        author = Author(name=author_request.name, author_metadata=author_request.author_metadata)
        db.add(author)
        db.commit()
        db.refresh(author)
        return author
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=422, detail="Author with that name already exists.")


@router.get("/{author_id}", response_model=AuthorResponse, status_code=status.HTTP_200_OK)
def get_author(author_id: Annotated[int, Path()], db: Annotated[Session, Depends(get_db)]):
    author = (
        db.query(Author)
        .options(joinedload(Author.style_profiles).joinedload(AuthorStyleProfile.features))
        .filter(Author.id == author_id)
        .first()
    )
    if author is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Author not found")
    return author


@router.put("/{author_id}", response_model=AuthorResponse, status_code=status.HTTP_200_OK)
def update_author(
        author_request: AuthorRequest,
        db: Annotated[Session, Depends(get_db)],
        author_id: int = Path(gt=0)
):
    author = db.get(Author, author_id)
    if author is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Author not found")
    author.name = author_request.name
    author.author_metadata = author_request.author_metadata
    db.commit()
    db.refresh(author)
    return author


@router.delete("/{author_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_author(author_id: Annotated[int, Path()], db: Annotated[Session, Depends(get_db)]):
    author = db.get(Author, author_id)
    if author is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Author not found")
    db.delete(author)
    db.commit()


@router.get(
    "/{author_id}/style-profile",
    response_model=AuthorStyleProfileResponse,
    status_code=status.HTTP_200_OK
)
async def get_author_profile(db: Annotated[Session, Depends(get_db)], author_id: int = Path(gt=0)):
    author_profile = (
        db.query(AuthorStyleProfile)
        .options(joinedload(AuthorStyleProfile.features))
        .filter(AuthorStyleProfile.author_id == author_id)
        .order_by(AuthorStyleProfile.computed_at.desc())
        .first()
    )
    if author_profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile for author not found")
    return author_profile