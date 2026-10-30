import math
from typing import Any, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

T = TypeVar("T")


def paginate(db: Session, stmt: Select[Any], page: int, page_size: int) -> dict[str, Any]:
    """Run ``stmt`` with LIMIT/OFFSET and return a dict matching ``schemas.common.Page``."""
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = db.scalars(stmt.limit(page_size).offset((page - 1) * page_size)).unique().all()
    return {
        "items": list(items),
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total else 0,
    }


def like_pattern(term: str) -> str:
    """Escape LIKE wildcards in user input and wrap it for a contains-match."""
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
