-- Sprint 2: catálogo de materiais + histórico de orçamentos
-- Execute no SQL Editor do Supabase

create extension if not exists "pgcrypto";

create table if not exists public.materials (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  synonyms text[] not null default '{}',
  default_unit text not null default 'unidade',
  unit_price numeric(12, 2) not null default 0,
  category text,
  active boolean not null default true,
  updated_at timestamptz not null default now()
);

create index if not exists materials_active_name_idx
  on public.materials (active, name);

create table if not exists public.budgets (
  id uuid primary key default gen_random_uuid(),
  wa_id text not null,
  obra_type text not null default 'obra',
  materials jsonb not null default '[]'::jsonb,
  total_amount numeric(12, 2) not null default 0,
  status text not null default 'sent',
  created_at timestamptz not null default now()
);

create index if not exists budgets_wa_id_created_at_idx
  on public.budgets (wa_id, created_at desc);

comment on table public.materials is 'Catálogo de materiais com preço unitário';
comment on table public.budgets is 'Histórico de orçamentos gerados por número WhatsApp';
