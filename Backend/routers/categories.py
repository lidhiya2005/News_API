"""Category endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Article, Category, User
from schemas import CategoryCreate, CategoryOut, CategoryUpdate
from utils import unique_slug

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)) -> list[Category]:
    """List all categories ordered by name."""
    return db.query(Category).order_by(Category.name.asc()).all()


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Category:
    """Create a new category (authenticated users only)."""
    if db.query(Category).filter(Category.name == payload.name).first():
        raise HTTPException(status_code=409, detail="Category already exists")

    category = Category(**payload.model_dump(), slug=unique_slug(db, Category, payload.name))
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.put("/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Category:
    """Update a category (authenticated users only)."""
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if payload.name is not None:
        existing = db.query(Category).filter(
            Category.name == payload.name, Category.id != category.id
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="Category already exists")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, field, value)

    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> None:
    """Delete a category (authenticated users only). Articles keep existing but lose the link."""
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    db.query(Article).filter(Article.category_id == category.id).update(
        {Article.category_id: None}
    )
    db.delete(category)
    db.commit()
