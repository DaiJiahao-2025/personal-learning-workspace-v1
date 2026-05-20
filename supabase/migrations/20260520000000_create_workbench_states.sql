create table if not exists public.workbench_states (
  user_id uuid primary key references auth.users(id) on delete cascade,
  state jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

alter table public.workbench_states enable row level security;

drop policy if exists "Users can read their own workbench state" on public.workbench_states;
create policy "Users can read their own workbench state"
  on public.workbench_states
  for select
  to authenticated
  using (user_id = (select auth.uid()));

drop policy if exists "Users can insert their own workbench state" on public.workbench_states;
create policy "Users can insert their own workbench state"
  on public.workbench_states
  for insert
  to authenticated
  with check (user_id = (select auth.uid()));

drop policy if exists "Users can update their own workbench state" on public.workbench_states;
create policy "Users can update their own workbench state"
  on public.workbench_states
  for update
  to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

drop policy if exists "Users can delete their own workbench state" on public.workbench_states;
create policy "Users can delete their own workbench state"
  on public.workbench_states
  for delete
  to authenticated
  using (user_id = (select auth.uid()));
