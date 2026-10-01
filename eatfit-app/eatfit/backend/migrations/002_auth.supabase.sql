-- 002: Supabase-only extras. Skipped automatically on plain Postgres.
-- 1) Deleting a user in Supabase Auth deletes all their data.
-- 2) Row Level Security: even if someone calls Supabase's auto-generated API
--    directly with the public key, they can only ever touch their own rows.
--    (Our backend connects as the database owner, so RLS doesn't slow it down.)

alter table profiles      add constraint profiles_user_fk  foreign key (user_id)  references auth.users (id) on delete cascade;
alter table menus         add constraint menus_user_fk     foreign key (user_id)  references auth.users (id) on delete cascade;
alter table meal_logs     add constraint logs_user_fk      foreign key (user_id)  references auth.users (id) on delete cascade;
alter table skipped_meals add constraint skips_user_fk     foreign key (user_id)  references auth.users (id) on delete cascade;
alter table foods         add constraint foods_owner_fk    foreign key (owner_id) references auth.users (id) on delete cascade;

alter table profiles      enable row level security;
alter table menus         enable row level security;
alter table meal_logs     enable row level security;
alter table skipped_meals enable row level security;
alter table foods         enable row level security;

create policy own_profile on profiles      for all to authenticated
  using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy own_menus   on menus         for all to authenticated
  using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy own_logs    on meal_logs     for all to authenticated
  using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy own_skips   on skipped_meals for all to authenticated
  using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy read_foods  on foods for select to authenticated
  using (owner_id is null or owner_id = (select auth.uid()));
