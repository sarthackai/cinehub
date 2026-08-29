-- ============================================================================
-- STREAMSYNC AI — Phase 2: Initial Database Schema
-- Run this in Supabase SQL Editor (or via `supabase db push` with the CLI)
-- ============================================================================

-- Extensions
create extension if not exists "uuid-ossp";
create extension if not exists pgcrypto;

-- ============================================================================
-- 1. PROFILES  (extends Supabase auth.users)
-- ============================================================================
create table if not exists profiles (
    id uuid primary key references auth.users(id) on delete cascade,
    display_name text,
    avatar_url text,
    favorite_genres text[] default '{}',
    favorite_languages text[] default '{}',
    favorite_platforms text[] default '{}',
    is_admin boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- ============================================================================
-- 2. GENRES
-- ============================================================================
create table if not exists genres (
    id serial primary key,
    name text not null unique,
    slug text not null unique
);

-- ============================================================================
-- 3. PEOPLE (cast & crew, shared table)
-- ============================================================================
create table if not exists people (
    id uuid primary key default uuid_generate_v4(),
    external_id text,               -- id from metadata provider
    provider text default 'tmdb',
    name text not null,
    profile_image_url text,
    created_at timestamptz not null default now(),
    unique (external_id, provider)
);

-- ============================================================================
-- 4. OTT PLATFORMS (generic, not hardcoded per-brand logic)
-- ============================================================================
create table if not exists ott_platforms (
    id serial primary key,
    name text not null unique,
    slug text not null unique,
    logo_url text
);

-- ============================================================================
-- 5. CONTENT (core table — movies & tv shows share this)
-- ============================================================================
create table if not exists content (
    id uuid primary key default uuid_generate_v4(),
    external_id text not null,           -- id from metadata provider
    provider text not null default 'tmdb',
    content_type text not null check (content_type in ('movie', 'tv')),
    title text not null,
    original_title text,
    overview text,
    poster_url text,
    backdrop_url text,
    release_date date,
    language text,
    country text,
    runtime_minutes int,
    number_of_seasons int,
    number_of_episodes int,
    age_rating text,
    provider_rating numeric(3,1),        -- e.g. TMDB rating
    provider_vote_count int,
    popularity numeric,
    trending_score numeric default 0,
    source_last_updated timestamptz,     -- when provider data was last refreshed
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (external_id, provider)
);

create index if not exists idx_content_type on content(content_type);
create index if not exists idx_content_release_date on content(release_date desc);
create index if not exists idx_content_popularity on content(popularity desc);
create index if not exists idx_content_trending on content(trending_score desc);
create index if not exists idx_content_title on content using gin (to_tsvector('english', title));

-- ============================================================================
-- 6. CONTENT_GENRES (many-to-many)
-- ============================================================================
create table if not exists content_genres (
    content_id uuid not null references content(id) on delete cascade,
    genre_id int not null references genres(id) on delete cascade,
    primary key (content_id, genre_id)
);

-- ============================================================================
-- 7. CONTENT_CAST
-- ============================================================================
create table if not exists content_cast (
    id uuid primary key default uuid_generate_v4(),
    content_id uuid not null references content(id) on delete cascade,
    person_id uuid not null references people(id) on delete cascade,
    character_name text,
    cast_order int,
    unique (content_id, person_id, character_name)
);

create index if not exists idx_content_cast_content on content_cast(content_id);
create index if not exists idx_content_cast_person on content_cast(person_id);

-- ============================================================================
-- 8. CONTENT_CREW (directors, creators, writers)
-- ============================================================================
create table if not exists content_crew (
    id uuid primary key default uuid_generate_v4(),
    content_id uuid not null references content(id) on delete cascade,
    person_id uuid not null references people(id) on delete cascade,
    role text not null,   -- 'Director' | 'Creator' | 'Writer' | ...
    unique (content_id, person_id, role)
);

create index if not exists idx_content_crew_content on content_crew(content_id);
create index if not exists idx_content_crew_person on content_crew(person_id);

-- ============================================================================
-- 9. CONTENT_AVAILABILITY (per-platform, per-region, versioned & sourced)
-- ============================================================================
create table if not exists content_availability (
    id uuid primary key default uuid_generate_v4(),
    content_id uuid not null references content(id) on delete cascade,
    platform_id int not null references ott_platforms(id) on delete cascade,
    region text,                       -- ISO country code, if provider supplies it
    availability_type text,            -- 'subscription' | 'rent' | 'buy' | 'free'
    source text not null default 'tmdb',
    source_last_updated timestamptz not null default now(),
    unique (content_id, platform_id, region, availability_type)
);

create index if not exists idx_availability_content on content_availability(content_id);

-- ============================================================================
-- 10. RATINGS (in-app user ratings — separate from provider_rating on content)
-- ============================================================================
create table if not exists ratings (
    id uuid primary key default uuid_generate_v4(),
    user_id uuid not null references profiles(id) on delete cascade,
    content_id uuid not null references content(id) on delete cascade,
    rating numeric(2,1) not null check (rating >= 0.5 and rating <= 5.0),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (user_id, content_id)
);

create index if not exists idx_ratings_content on ratings(content_id);

-- ============================================================================
-- 11. REVIEWS
-- ============================================================================
create table if not exists reviews (
    id uuid primary key default uuid_generate_v4(),
    user_id uuid not null references profiles(id) on delete cascade,
    content_id uuid not null references content(id) on delete cascade,
    body text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_reviews_content on reviews(content_id);

-- ============================================================================
-- 12. FAVORITES
-- ============================================================================
create table if not exists favorites (
    user_id uuid not null references profiles(id) on delete cascade,
    content_id uuid not null references content(id) on delete cascade,
    created_at timestamptz not null default now(),
    primary key (user_id, content_id)
);

-- ============================================================================
-- 13. WATCHLIST
-- ============================================================================
create table if not exists watchlist (
    user_id uuid not null references profiles(id) on delete cascade,
    content_id uuid not null references content(id) on delete cascade,
    created_at timestamptz not null default now(),
    primary key (user_id, content_id)
);

-- ============================================================================
-- 14. WATCH_HISTORY
-- ============================================================================
create table if not exists watch_history (
    id uuid primary key default uuid_generate_v4(),
    user_id uuid not null references profiles(id) on delete cascade,
    content_id uuid not null references content(id) on delete cascade,
    watched_at timestamptz not null default now(),
    progress_percent numeric default 0
);

create index if not exists idx_watch_history_user on watch_history(user_id, watched_at desc);

-- ============================================================================
-- 15. SEARCH_HISTORY
-- ============================================================================
create table if not exists search_history (
    id uuid primary key default uuid_generate_v4(),
    user_id uuid not null references profiles(id) on delete cascade,
    query text not null,
    created_at timestamptz not null default now()
);

create index if not exists idx_search_history_user on search_history(user_id, created_at desc);

-- ============================================================================
-- 16. USER_PREFERENCES (derived/weighted profile, rebuilt periodically)
-- ============================================================================
create table if not exists user_preferences (
    user_id uuid primary key references profiles(id) on delete cascade,
    preference_vector jsonb,     -- serialized weighted genre/actor/director vector
    last_computed_at timestamptz not null default now()
);

-- ============================================================================
-- 17. USER_INTERACTIONS (like / dislike / not_interested / click / view)
-- ============================================================================
create table if not exists user_interactions (
    id uuid primary key default uuid_generate_v4(),
    user_id uuid not null references profiles(id) on delete cascade,
    content_id uuid not null references content(id) on delete cascade,
    interaction_type text not null check (
        interaction_type in ('like', 'dislike', 'not_interested', 'click', 'view')
    ),
    created_at timestamptz not null default now()
);

create index if not exists idx_interactions_user on user_interactions(user_id, created_at desc);
create index if not exists idx_interactions_content on user_interactions(content_id);

-- ============================================================================
-- 18. RECOMMENDATION_LOGS (for evaluation: precision@k, recall@k, etc.)
-- ============================================================================
create table if not exists recommendation_logs (
    id uuid primary key default uuid_generate_v4(),
    user_id uuid references profiles(id) on delete set null,
    content_id uuid not null references content(id) on delete cascade,
    strategy text not null,        -- 'content_based' | 'semantic' | 'hybrid' | 'trending'
    score numeric,
    explanation text,
    was_clicked boolean default false,
    created_at timestamptz not null default now()
);

create index if not exists idx_reco_logs_user on recommendation_logs(user_id, created_at desc);

-- ============================================================================
-- 19. CONTENT_EMBEDDINGS (sentence-transformer vectors; pgvector-ready)
-- ============================================================================
create table if not exists content_embeddings (
    content_id uuid primary key references content(id) on delete cascade,
    model_name text not null,
    embedding float8[] not null,     -- swap to `vector` type if pgvector extension enabled
    updated_at timestamptz not null default now()
);

-- ============================================================================
-- 20. SYNC_LOGS
-- ============================================================================
create table if not exists sync_logs (
    id uuid primary key default uuid_generate_v4(),
    job_name text not null,          -- 'trending_sync' | 'new_releases_sync' | ...
    provider text not null default 'tmdb',
    status text not null check (status in ('success', 'partial', 'failed')),
    rows_processed int default 0,
    error_message text,
    started_at timestamptz not null,
    finished_at timestamptz
);

-- ============================================================================
-- 21. ADMIN_LOGS
-- ============================================================================
create table if not exists admin_logs (
    id uuid primary key default uuid_generate_v4(),
    admin_id uuid references profiles(id) on delete set null,
    action text not null,
    details jsonb,
    created_at timestamptz not null default now()
);

-- ============================================================================
-- updated_at auto-touch trigger (reused across tables)
-- ============================================================================
create or replace function set_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create trigger trg_profiles_updated before update on profiles
    for each row execute function set_updated_at();
create trigger trg_content_updated before update on content
    for each row execute function set_updated_at();
create trigger trg_ratings_updated before update on ratings
    for each row execute function set_updated_at();
create trigger trg_reviews_updated before update on reviews
    for each row execute function set_updated_at();

-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================

-- Reference/content tables: public read, no public write (writes go through
-- the backend using the service-role key, which bypasses RLS by design).
alter table content enable row level security;
alter table genres enable row level security;
alter table people enable row level security;
alter table ott_platforms enable row level security;
alter table content_genres enable row level security;
alter table content_cast enable row level security;
alter table content_crew enable row level security;
alter table content_availability enable row level security;
alter table content_embeddings enable row level security;

create policy "Public read content" on content for select using (true);
create policy "Public read genres" on genres for select using (true);
create policy "Public read people" on people for select using (true);
create policy "Public read platforms" on ott_platforms for select using (true);
create policy "Public read content_genres" on content_genres for select using (true);
create policy "Public read content_cast" on content_cast for select using (true);
create policy "Public read content_crew" on content_crew for select using (true);
create policy "Public read availability" on content_availability for select using (true);
create policy "Public read embeddings" on content_embeddings for select using (true);

-- Reviews & ratings: public read (like any OTT site), owner-only write.
alter table ratings enable row level security;
alter table reviews enable row level security;

create policy "Public read ratings" on ratings for select using (true);
create policy "Users manage own ratings" on ratings for all
    using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "Public read reviews" on reviews for select using (true);
create policy "Users manage own reviews" on reviews for all
    using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Fully private, per-user tables.
alter table profiles enable row level security;
alter table favorites enable row level security;
alter table watchlist enable row level security;
alter table watch_history enable row level security;
alter table search_history enable row level security;
alter table user_preferences enable row level security;
alter table user_interactions enable row level security;

create policy "Users read own profile" on profiles for select using (auth.uid() = id);
create policy "Users update own profile" on profiles for update using (auth.uid() = id);
create policy "Users insert own profile" on profiles for insert with check (auth.uid() = id);

create policy "Users manage own favorites" on favorites for all
    using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "Users manage own watchlist" on watchlist for all
    using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "Users manage own watch_history" on watch_history for all
    using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "Users manage own search_history" on search_history for all
    using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "Users manage own preferences" on user_preferences for all
    using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "Users manage own interactions" on user_interactions for all
    using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Admin-only / backend-only tables: no public policies at all.
-- (recommendation_logs, sync_logs, admin_logs stay RLS-enabled with zero
-- policies, so only the service-role key — used exclusively by the FastAPI
-- backend — can touch them. Regular users get zero access, even read.)
alter table recommendation_logs enable row level security;
alter table sync_logs enable row level security;
alter table admin_logs enable row level security;

-- ============================================================================
-- SEED DATA: OTT platforms (extend anytime — no code changes needed)
-- ============================================================================
insert into ott_platforms (name, slug) values
    ('Netflix', 'netflix'),
    ('Amazon Prime Video', 'prime-video'),
    ('Disney+', 'disney-plus'),
    ('JioHotstar', 'jiohotstar'),
    ('Apple TV+', 'apple-tv-plus'),
    ('Sony LIV', 'sony-liv'),
    ('ZEE5', 'zee5'),
    ('Hulu', 'hulu'),
    ('Max', 'max'),
    ('Crunchyroll', 'crunchyroll'),
    ('Paramount+', 'paramount-plus')
on conflict (slug) do nothing;