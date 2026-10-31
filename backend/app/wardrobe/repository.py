from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


def ensure_member(connection, user):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """INSERT INTO members(id,email,name) VALUES (%s,%s,%s)
            ON CONFLICT(id) DO UPDATE SET email=excluded.email,name=excluded.name
            RETURNING id,email,name""",
            (user.id, user.email, user.name),
        )
        return cursor.fetchone()


def list_items(connection, owner):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """SELECT product_snapshot AS product, profile, comment, saved_at AS "savedAt"
            FROM wardrobe_items WHERE member_id=%s ORDER BY saved_at DESC,product_id""",
            (owner,),
        )
        return cursor.fetchall()


def save_item(connection, owner, product_id, product, request):
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            '''INSERT INTO wardrobe_items(member_id,product_id,product_snapshot,profile,comment)
            VALUES(%s,%s,%s,%s,%s) ON CONFLICT(member_id,product_id) DO UPDATE SET
            product_snapshot=excluded.product_snapshot,profile=excluded.profile,comment=excluded.comment
            RETURNING product_snapshot AS product,profile,comment,saved_at AS "savedAt"''',
            (
                owner,
                product_id,
                Jsonb(product.model_dump()),
                Jsonb(request.profile.model_dump()),
                request.comment,
            ),
        )
        return cursor.fetchone()


def remove_item(connection, owner, product_key):
    # Owner and immutable product identity are both checked in SQL.
    with connection.cursor() as cursor:
        cursor.execute(
            """DELETE FROM wardrobe_items WHERE member_id=%s
            AND product_snapshot->>'id'=%s""",
            (owner, product_key),
        )
