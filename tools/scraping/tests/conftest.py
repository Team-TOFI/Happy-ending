import pytest


@pytest.fixture
def snapshot():
    # Hand-checked values from product 7428042. The editable row is not a size.
    return {
        "product_url": "https://www.musinsa.com/products/7428042",
        "name": "LABEL INCISION LONG SLEEVE T-SHIRT, PURPLE",
        "brand": "런던다다",
        "categories": [
            {"code": "001", "name": "상의"},
            {"code": "001010", "name": "긴소매 티셔츠"},
        ],
        "details": {"성별": "여", "시즌": "2025 FW"},
        "price_text": "24%60,730원",
        "images": [
            "https://image.msscdn.net/thumbnails/images/goods_img/20260930/7428042/front.jpg?w=1200",
            "https://image.msscdn.net/thumbnails/images/goods_img/20260930/7428042/front.jpg?w=192",
            "https://image.msscdn.net/thumbnails/images/prd_img/20260930/7428042/side.jpg?w=1200",
            "https://image.msscdn.net/thumbnails/images/goods_img/20260930/999/banner.jpg?w=1200",
        ],
        "notice": {
            "제품 소재": "리오셀 46.5% + 레이온 33.5% + 울 20%",
            "색상": "상품 상세설명 참조",
        },
        "size_table": {
            "labels": ["cm", "내 사이즈", "S", "M", "L"],
            "headers": ["1\n총장", "2\n어깨너비", "3\n가슴단면", "4\n소매길이", "5\n밑단단면"],
            "rows": [
                ["사이즈를 직접 입력해주세요"],
                ["60", "40", "43", "68", "-"],
                ["61", "42", "45", "69", "-"],
                ["62", "44", "47", "70", "-"],
            ],
        },
    }
