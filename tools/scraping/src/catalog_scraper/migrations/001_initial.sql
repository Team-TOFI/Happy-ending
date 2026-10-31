CREATE TABLE products (
    id BIGINT PRIMARY KEY CHECK (id > 0),
    product_url TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL CHECK (name <> ''),
    brand TEXT,
    category_code TEXT,
    category_path JSONB NOT NULL DEFAULT '[]',
    gender_raw TEXT,
    season_raw TEXT,
    price_text TEXT,
    notice JSONB NOT NULL DEFAULT '{}',
    size_status TEXT NOT NULL CHECK (size_status IN ('available', 'not_provided')),
    raw_snapshot JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    collected_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX products_category_idx ON products(category_code);

CREATE TABLE product_images (
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    position INTEGER NOT NULL CHECK (position >= 0),
    image_url TEXT NOT NULL,
    PRIMARY KEY (product_id, position),
    UNIQUE (product_id, image_url)
);

CREATE TABLE product_size_tables (
    product_id BIGINT PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
    unit TEXT NOT NULL,
    measurement_columns JSONB NOT NULL
);

CREATE TABLE product_sizes (
    product_id BIGINT NOT NULL REFERENCES product_size_tables(product_id) ON DELETE CASCADE,
    size_label TEXT NOT NULL,
    position INTEGER NOT NULL CHECK (position >= 0),
    measurements JSONB NOT NULL,
    PRIMARY KEY (product_id, size_label),
    UNIQUE (product_id, position)
);
