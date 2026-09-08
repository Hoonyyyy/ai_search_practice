from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import board

router = APIRouter()


class NewCard(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    detail: str = Field(default="", max_length=2000)
    assignee: str = "후니"
    tag: str = "feature"


class PatchCard(BaseModel):
    column: str | None = None
    assignee: str | None = None
    tag: str | None = None


@router.get("/board/cards")
def cards():
    return board.list_cards()


@router.post("/board/cards")
def new_card(c: NewCard):
    try:
        return board.add_card(c.title, c.detail, c.assignee, c.tag)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.patch("/board/cards/{card_id}")
def patch(card_id: str, p: PatchCard):
    try:
        return board.patch_card(
            card_id, column=p.column, assignee=p.assignee, tag=p.tag
        )
    except KeyError:
        raise HTTPException(404, "card not found")
    except ValueError as e:
        raise HTTPException(400, str(e))
