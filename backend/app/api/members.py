from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Response

from app.auth.session import AuthUser, require_member
from app.catalog.repository import load_catalog
from app.tofi.service import product_key, product_view
from app.wardrobe import repository
from app.wardrobe.schemas import SavedItem, SaveWardrobe, WardrobeResponse

from .recommendations import get_connection

router = APIRouter(tags=["members"])
Member = Annotated[AuthUser, Depends(require_member)]
Connection = Annotated[psycopg.Connection, Depends(get_connection)]


@router.get("/auth/me", response_model=AuthUser, summary="현재 Google 회원 조회")
def me(user: Member, connection: Connection):
    repository.ensure_member(connection, user)
    return user


@router.get("/wardrobe", response_model=WardrobeResponse, summary="내 옷장 조회")
def wardrobe(user: Member, connection: Connection):
    return WardrobeResponse(items=repository.list_items(connection, user.id))


@router.put("/wardrobe/{key}", response_model=SavedItem, summary="내 옷장에 상품 저장")
def save(key: str, request: SaveWardrobe, user: Member, connection: Connection):
    products, _ = load_catalog(connection)
    product = next((p for p in products if product_key(p) == key), None)
    if product is None:
        raise HTTPException(404, "상품을 찾을 수 없습니다")
    try:
        view = product_view(product)
    except ValueError as error:
        raise HTTPException(409, "현재 상품 정보를 확인할 수 없습니다") from error
    with connection.transaction():
        repository.ensure_member(connection, user)
        return repository.save_item(connection, user.id, product.id, view, request)


@router.delete("/wardrobe/{key}", status_code=204, summary="내 옷장에서 상품 삭제")
def remove(key: str, user: Member, connection: Connection):
    repository.remove_item(connection, user.id, key)
    return Response(status_code=204)
