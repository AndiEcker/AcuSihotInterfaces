ALTER TABLE public.res_groups
    ADD COLUMN rgr_source character varying(3);

COMMENT ON COLUMN public.res_groups.rgr_source
    IS 'Source/Department';

ALTER TABLE public.res_groups
    ADD COLUMN rgr_group_no character varying(96);

COMMENT ON COLUMN public.res_groups.rgr_group_no
    IS 'Group number and extra info';

ALTER TABLE public.res_groups
    ADD COLUMN rgr_sh_pack character varying(3);

COMMENT ON COLUMN public.res_groups.rgr_sh_pack
    IS 'Board/Meal plan';
