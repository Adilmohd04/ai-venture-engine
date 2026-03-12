-- ============================================================
-- Payments Table Migration
-- Stores all payment transactions for audit and duplicate prevention
-- ============================================================

-- Create payments table
create table if not exists public.payments (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles(id) on delete cascade not null,
  order_id text not null unique,
  amount numeric(10,2) not null,
  credits_added int not null,
  plan text not null,
  status text not null check (status in ('pending', 'completed', 'failed', 'refunded')),
  payment_method text not null default 'paypal',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Index for fast lookups
create unique index if not exists idx_payments_order_id on public.payments(order_id);
create index if not exists idx_payments_user_id on public.payments(user_id);
create index if not exists idx_payments_created_at on public.payments(created_at desc);

-- Row Level Security
alter table public.payments enable row level security;

-- Users can view their own payments
create policy "Users can view own payments"
  on public.payments for select
  using (auth.uid() = user_id);

-- Only backend can insert payments (via service_role)
grant all on public.payments to service_role;
