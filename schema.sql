-- Workaround for piccolo bugs

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE bot_list (
    id uuid primary key default uuid_generate_v4(),
    name text DEFAULT '' NOT NULL,
    state integer not null default 0,
    claim_bot_api text DEFAULT '' NOT NULL,
    unclaim_bot_api text DEFAULT '' NOT NULL,
    approve_bot_api text DEFAULT '' NOT NULL,
    deny_bot_api text DEFAULT '' NOT NULL,
    domain text not null default '#',
    secret_key text DEFAULT 'default' NOT NULL
);

CREATE TABLE bot_queue (
    bot_id bigint PRIMARY KEY,
    username text DEFAULT ''::text NOT NULL,
    banner text DEFAULT ''::text,
    description text DEFAULT ''::text NOT NULL,
    long_description text DEFAULT ''::text NOT NULL,
    website text DEFAULT ''::text,
    invite text DEFAULT ''::text,
    added_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    state integer DEFAULT 0 NOT NULL,
    list_source uuid not null,
    owner bigint DEFAULT 0 NOT NULL,
    extra_owners bigint[] not null default '{}',
    CONSTRAINT bot_queue_list_source_fkey FOREIGN KEY (list_source) REFERENCES public.bot_list(id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE bot_action (
    id uuid primary key default uuid_generate_v4(),
    bot_id bigint not null,
    action integer DEFAULT 0 NOT NULL,
    reason text DEFAULT ''::text NOT NULL,
    reviewer text DEFAULT ''::text NOT NULL,
    action_time timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    list_source uuid not null,
    CONSTRAINT bot_action_list_source_fkey FOREIGN KEY (list_source) REFERENCES public.bot_list(id) ON UPDATE CASCADE ON DELETE CASCADE
);

