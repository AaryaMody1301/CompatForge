-- Phase 7C: least-privilege accepted-community refresh automation.
--
-- Refresh automation may read only immutable accepted/unpublished candidates.
-- It cannot review submissions or record publication receipts.

create table private.refresh_automation_memberships (
  user_id uuid primary key references auth.users(id) on delete cascade,
  created_at timestamptz not null default pg_catalog.now()
);

comment on table private.refresh_automation_memberships is
  'Dedicated identities allowed to prepare repository refresh PRs from immutable accepted community candidates. Membership grants no review or publication authority.';

revoke all on table private.refresh_automation_memberships from public, anon, authenticated;

create or replace function private.can_prepare_community_refresh()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select auth.uid() is not null
    and (
      private.get_current_moderator_role() = 'admin'
      or exists (
        select 1
        from private.refresh_automation_memberships membership
        where membership.user_id = auth.uid()
      )
    );
$$;

revoke all on function private.can_prepare_community_refresh() from public, anon, authenticated;

create or replace function private.get_community_refresh_batch_impl()
returns table (
  submission_id uuid,
  observation_id text,
  device_id text,
  observation jsonb,
  observation_text text,
  observation_sha256 text,
  source_payload_sha256 text,
  created_at timestamptz
)
language plpgsql
stable
security definer
set search_path = ''
as $$
begin
  if not private.can_prepare_community_refresh() then
    raise exception 'community refresh authorization required';
  end if;

  return query
  select
    candidate.submission_id,
    candidate.observation_id,
    candidate.device_id,
    candidate.observation,
    candidate.observation::text,
    candidate.observation_sha256,
    candidate.source_payload_sha256,
    candidate.created_at
  from private.community_observation_candidates candidate
  join public.evidence_submissions submission
    on submission.id = candidate.submission_id
  where submission.state = 'accepted'
    and candidate.published_at is null
  order by candidate.created_at asc, candidate.observation_id asc
  limit 200;
end;
$$;

revoke all on function private.get_community_refresh_batch_impl() from public, anon;
grant execute on function private.get_community_refresh_batch_impl() to authenticated;

create or replace function public.get_community_refresh_batch()
returns table (
  submission_id uuid,
  observation_id text,
  device_id text,
  observation jsonb,
  observation_text text,
  observation_sha256 text,
  source_payload_sha256 text,
  created_at timestamptz
)
language sql
stable
security invoker
set search_path = ''
as $$
  select * from private.get_community_refresh_batch_impl();
$$;

revoke all on function public.get_community_refresh_batch() from public, anon;
grant execute on function public.get_community_refresh_batch() to authenticated;
