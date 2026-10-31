CREATE TABLE public.members (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE public.wardrobe_items (
    member_id UUID NOT NULL REFERENCES public.members(id) ON DELETE CASCADE,
    product_id BIGINT NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
    product_snapshot JSONB NOT NULL CHECK (jsonb_typeof(product_snapshot)='object'),
    profile JSONB NOT NULL CHECK (jsonb_typeof(profile)='object'),
    comment TEXT NOT NULL DEFAULT '' CHECK (length(comment)<=1000),
    saved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY(member_id,product_id)
);
ALTER TABLE public.members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.wardrobe_items ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.members,public.wardrobe_items FROM anon,authenticated;
GRANT SELECT ON public.members,public.wardrobe_items TO authenticated;
CREATE POLICY members_read_own ON public.members FOR SELECT TO authenticated USING (id=(SELECT auth.uid()));
CREATE POLICY wardrobe_read_own ON public.wardrobe_items FOR SELECT TO authenticated USING (member_id=(SELECT auth.uid()));
-- Writes use FastAPI's verified identity and explicit owner WHERE/INSERT values.
-- Data API cannot write client-supplied product snapshots or another owner's rows.
