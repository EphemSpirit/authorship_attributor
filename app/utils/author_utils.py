from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.author import Author

def get_or_create_author(db: Session, name: str) -> Author:
    title_cased_name = name.title()

    try:
        author = Author(name=title_cased_name)
        db.add(author)
        db.commit()
    except IntegrityError:
        db.rollback()
        author = db.query(Author).filter(Author.name == title_cased_name).first()
    return author