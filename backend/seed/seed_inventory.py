from sqlalchemy.orm import Session

from .seed_b import seed_person_b


def seed_inventory(db: Session) -> None:
    seed_person_b(db)
