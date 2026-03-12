-- ============================================================
-- Teams Migration
-- Adds teams, team_members, team_invitations tables,
-- profiles.team_id column, team credit columns, indexes,
-- RLS policies, and service_role grants
-- ============================================================

-- 1. Teams table
create table if not exists public.teams (
  id uuid primary key default gen_random_uuid(),
  name text not null check (char_length(name) <= 100),
  owner_id uuid references public.profiles(id) on delete cascade not null,
  team_credits_used int not null default 0,
  team_credits_limit int not null default 999999,
  created_at timestamptz not null default now()
);

-- 2. Team members junction table
create table if not exists public.team_members (
  id uuid primary key default gen_random_uuid(),
  team_id uuid references public.teams(id) on delete cascade not null,
  user_id uuid references public.profiles(id) on delete cascade not null,
  role text not null default 'member' check (role in ('owner', 'member')),
  joined_at timestamptz not null default now(),
  unique(team_id, user_id)
);

-- 3. Team invitations table
create table if not exists public.team_invitations (
  id uuid primary key default gen_random_uuid(),
  team_id uuid references public.teams(id) on delete cascade not null,
  email text not null,
  status text not null default 'pending' check (status in ('pending', 'accepted', 'declined')),
  invited_by uuid references public.profiles(id) on delete cascade not null,
  created_at timestamptz not null default now()
);

-- 4. Add team_id to profiles
alter table public.profiles add column if not exists team_id uuid references public.teams(id) on delete set null;

-- 5. Indexes for fast lookups
create index if not exists idx_team_members_team_id on public.team_members(team_id);
create index if not exists idx_team_members_user_id on public.team_members(user_id);
create index if not exists idx_team_invitations_email on public.team_invitations(email);
create index if not exists idx_team_invitations_team_id on public.team_invitations(team_id);
create index if not exists idx_profiles_team_id on public.profiles(team_id);

-- 6. Row Level Security
alter table public.teams enable row level security;
alter table public.team_members enable row level security;
alter table public.team_invitations enable row level security;

-- 7. RLS Policies: teams
create policy "Team members can view their team"
  on public.teams for select
  using (id in (select team_id from public.team_members where user_id = auth.uid()));

create policy "Business users can create teams"
  on public.teams for insert
  with check (auth.uid() = owner_id);

-- 8. RLS Policies: team_members
create policy "Team members can view members of their team"
  on public.team_members for select
  using (team_id in (select team_id from public.team_members where user_id = auth.uid()));

-- 9. RLS Policies: team_invitations
create policy "Invitees can view their invitations"
  on public.team_invitations for select
  using (email = (select email from public.profiles where id = auth.uid()));

create policy "Team owners can manage invitations"
  on public.team_invitations for all
  using (invited_by = auth.uid());

-- 10. Grant service_role full access
grant all on public.teams to service_role;
grant all on public.team_members to service_role;
grant all on public.team_invitations to service_role;
