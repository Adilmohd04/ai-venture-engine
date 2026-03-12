-- ============================================================
-- Public Reports Migration
-- Run this in your Supabase SQL Editor
-- ============================================================

-- Create public_reports table
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

-- Drop existing policies if they exist (to avoid conflicts)
drop policy if exists "Public reports are viewable by anyone" on public.public_reports;
drop policy if exists "Authenticated users can insert public reports" on public.public_reports;

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
