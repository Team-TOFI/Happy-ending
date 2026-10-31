ALTER TABLE products DROP CONSTRAINT products_size_status_check;
ALTER TABLE products ADD CONSTRAINT products_size_status_check
    CHECK (size_status IN ('available', 'not_provided', 'standard_guide_only'));

-- Reference/conversion charts are not product-specific actual measurements.
CREATE TABLE product_size_guides (
    product_id BIGINT PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
    guide JSONB NOT NULL
);
