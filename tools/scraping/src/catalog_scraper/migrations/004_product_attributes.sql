CREATE TABLE product_attributes (
    product_id BIGINT PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
    service_category TEXT CHECK (service_category IN ('TOP','BOTTOM','SHOES','BAG','OUTER')),
    attributes JSONB NOT NULL CHECK (jsonb_typeof(attributes)='object'),
    source_fingerprint TEXT NOT NULL CHECK (source_fingerprint ~ '^[0-9a-f]{64}$'),
    extractor_version TEXT NOT NULL,
    analyzed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX product_attributes_category_idx ON product_attributes(service_category);
