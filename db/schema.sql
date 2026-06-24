-- ============================================================
-- AI Customer Support Agent — Supabase Schema
-- Run this in the Supabase SQL editor before running seed_data.py
-- ============================================================

-- Clean slate (safe to re-run during development)
drop table if exists agent_logs cascade;
drop table if exists refund_requests cascade;
drop table if exists orders cascade;
drop table if exists customers cascade;

-- ----------------------------------------------------------------
-- CRM: customers
-- ----------------------------------------------------------------
create table customers (
    customer_id   text primary key,
    name          text not null,
    email         text not null unique,
    phone         text,
    signup_date   date not null,
    loyalty_tier  text not null check (loyalty_tier in ('standard','silver','gold','platinum')),
    total_orders  int  not null default 0,
    account_flag  text not null default 'none' check (account_flag in ('none','fraud_watch'))
);

-- ----------------------------------------------------------------
-- Orders
-- ----------------------------------------------------------------
create table orders (
    order_id        text primary key,
    customer_id     text not null references customers(customer_id),
    product_name    text not null,
    category        text not null check (
        category in ('electronics','apparel','beauty','furniture','books','grocery','final_sale')
    ),
    order_date      date not null,
    delivery_date   date,
    amount          numeric(10,2) not null,
    shipping_amount numeric(10,2) not null default 0,
    status          text not null check (
        status in ('delivered','in_transit','cancelled','refunded')
    )
);

-- ----------------------------------------------------------------
-- Refund decisions made by the agent (audit trail)
-- ----------------------------------------------------------------
create table refund_requests (
    id              bigserial primary key,
    order_id        text not null references orders(order_id),
    customer_id     text not null references customers(customer_id),
    reason          text,
    claimed_defective boolean default false,
    decision        text not null check (decision in ('approved','denied','escalated')),
    refund_amount   numeric(10,2) default 0,
    explanation     text,
    created_at      timestamptz not null default now()
);

-- ----------------------------------------------------------------
-- Agent reasoning logs (powers the real-time admin dashboard)
-- ----------------------------------------------------------------
create table agent_logs (
    id          bigserial primary key,
    session_id  text not null,
    node_name   text,
    step_type   text not null check (
        step_type in ('user_message','agent_thought','tool_call','tool_result','final_response')
    ),
    content     text,
    created_at  timestamptz not null default now()
);

create index idx_orders_customer on orders(customer_id);
create index idx_refund_requests_customer on refund_requests(customer_id);
create index idx_agent_logs_session on agent_logs(session_id);

-- Disable RLS for this demo project (use service-role key or proper
-- policies in a production deployment).
alter table customers disable row level security;
alter table orders disable row level security;
alter table refund_requests disable row level security;
alter table agent_logs disable row level security;
