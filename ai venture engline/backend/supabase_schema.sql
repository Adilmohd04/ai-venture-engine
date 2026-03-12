-- ============================================================
-- AI Venture Intelligence Engine — Supabase Schema
-- Run this in your Supabase SQL Editor (Dashboard → SQL Editor)
-- ============================================================

-- 1. Profiles table (extends Supabase auth.users)
create table if not exists public.profiles (
  id uuid references auth.users(id) on delete cascade primary key,
  email text,
  full_name text,
  plan text not null default 'free' check (plan in ('free', 'pro', 'business')),
  credits_used int not null default 0,
  credits_limit int not null default 3,
  stripe_customer_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- 2. Analyses table (stores every analysis run)
create table if not exists public.analyses (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles(id) on delete cascade not null,
  analysis_id text not null,
  startup_name text not null default 'Unknown Startup',
  industry text,
  stage text,
  final_score float,
  verdict text,
  memo_json jsonb,
  created_at timestamptz not null default now()
);

-- Index for fast lookups
create index if not exists idx_analyses_user_id on public.analyses(user_id);
create index if not exists idx_analyses_startup_name on public.analyses(startup_name);
create index if not exists idx_analyses_created_at on public.analyses(created_at desc);

-- 3. Row Level Security
alter table public.profiles enable row level security;
alter table public.analyses enable row level security;

-- Profiles: users can only read/update their own profile
create policy "Users can view own profile"
  on public.profiles for select
  using (auth.uid() = id);

create policy "Users can update own profile"
  on public.profiles for update
  using (auth.uid() = id);

-- Analyses: users can only CRUD their own analyses
create policy "Users can view own analyses"
  on public.analyses for select
  using (auth.uid() = user_id);

create policy "Users can insert own analyses"
  on public.analyses for insert
  with check (auth.uid() = user_id);

create policy "Users can delete own analyses"
  on public.analyses for delete
  using (auth.uid() = user_id);

-- 4. Auto-create profile on signup
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email, full_name)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'full_name', split_part(new.email, '@', 1))
  );
  return new;
end;
$$ language plpgsql security definer;

-- Drop trigger if exists, then create
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- 5. Grant service_role full access (for backend)
grant all on public.profiles to service_role;
grant all on public.analyses to service_role;

-- 6. Public Reports table (shareable public reports)
create table if not exists public.public_reports (
  id uuid primary key default gen_random_uuid(),
  analysis_id text not null unique,
  user_id uuid references public.profiles(id) on delete cascade not null,
  startup_name text not null,
  investor_readiness_overall float not null,
  deal_breakers jsonb not null,
  key_strengths jsonb not null,
  created_at timestamptz not null default now()
);

-- Index for fast lookups by analysis_id
create unique index if not exists idx_public_reports_analysis_id 
  on public.public_reports(analysis_id);

-- Row Level Security for public reports
alter table public.public_reports enable row level security;

-- Public reports are viewable by anyone (no auth required)
create policy "Public reports are viewable by anyone"
  on public.public_reports for select
  using (true);

-- Only authenticated users can insert (via backend)
create policy "Authenticated users can insert public reports"
  on public.public_reports for insert
  with check (auth.uid() = user_id);

-- Grant service_role full access
grant all on public.public_reports to service_role;
