"""Who may see which document.

Every route that reaches a document goes through `visible_documents` or
`load_visible_document`. Neither is a convenience: a department boundary
enforced by remembering to add a `where` clause is a boundary that will be
missed, and one missed clause is one office reading another's files.

The rules, in one place:

- An officer sees documents assigned to them, in their own department.
- A head of department sees every document in their own department.
- Nobody sees another department's documents, whatever their role.

`tests/test_department_scope.py` asserts that every route reaching a document
uses one of these two functions, so a new route cannot quietly skip them.
"""

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.user import User

NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="document_not_found",
)


def visible_documents(user: User) -> Select:
    """A SELECT already narrowed to what this user may see."""
    query = select(Document).where(Document.department_id == user.department_id)
    if user.role != "dept_head":
        query = query.where(Document.assigned_to == user.id)
    return query


def load_visible_document(session: Session, user: User, document_id: int) -> Document:
    """Fetch one document, or refuse.

    A document in another department answers 404, not 403. A 403 would confirm
    the document exists, which tells one office something about another's
    caseload; 404 tells them only that it is not theirs.
    """
    document = session.scalar(
        visible_documents(user).where(Document.id == document_id)
    )
    if document is None:
        raise NOT_FOUND
    return document


def visible_users(user: User) -> Select:
    """The people this user may see. Officers see only themselves."""
    query = select(User).where(User.department_id == user.department_id)
    if user.role != "dept_head":
        query = query.where(User.id == user.id)
    return query


def load_managed_user(session: Session, actor: User, user_id: int) -> User:
    """Fetch a colleague a head of department may act on.

    Refuses anyone outside their department, and refuses the head themselves —
    nobody deactivates their own account by accident, and nobody escapes their
    own department by editing their own row.
    """
    target = session.scalar(visible_users(actor).where(User.id == user_id))
    if target is None or target.id == actor.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="user_not_found")
    return target
