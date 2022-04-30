-- Workaround for piccolo bugs

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE bot_list (
    id serial primary key,
    name text DEFAULT '' NOT NULL,
    state integer not null default 0,
    claim_bot_api text DEFAULT '' NOT NULL,
    unclaim_bot_api text DEFAULT '' NOT NULL,
    approve_bot_api text DEFAULT '' NOT NULL,
    deny_bot_api text DEFAULT '' NOT NULL,
    secret_key text DEFAULT 'default' NOT NULL
);

CREATE TABLE bot_queue (
    bot_id bigint NOT NULL,
    username text DEFAULT ''::text NOT NULL,
    banner text DEFAULT ''::text,
    description text DEFAULT ''::text NOT NULL,
    long_description text DEFAULT ''::text NOT NULL,
    website text DEFAULT ''::text,
    invite text DEFAULT ''::text,
    added_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    state integer DEFAULT 0 NOT NULL,
    list_source integer,
    owner bigint DEFAULT 0 NOT NULL,
    extra_owners bigint[] not null default '{}',
    CONSTRAINT bot_queue_pkey PRIMARY KEY (bot_id),
    CONSTRAINT bot_queue_list_source_fkey FOREIGN KEY (list_source) REFERENCES public.bot_list(id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE bot_action (
    bot_id bigint NOT NULL,
    action integer DEFAULT 0 NOT NULL,
    reason text DEFAULT ''::text NOT NULL,
    reviewer text DEFAULT ''::text NOT NULL,
    action_time timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    list_source integer,
    CONSTRAINT bot_action_pkey PRIMARY KEY (bot_id),
    CONSTRAINT bot_action_list_source_fkey FOREIGN KEY (list_source) REFERENCES public.bot_list(id) ON UPDATE CASCADE ON DELETE CASCADE
);

