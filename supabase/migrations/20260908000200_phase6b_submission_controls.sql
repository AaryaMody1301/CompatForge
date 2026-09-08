create or replace function private.enforce_submission_rate_limit()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  hourly_count integer;
  daily_count integer;
begin
  select
    count(*) filter (
      where submission.created_at >= pg_catalog.now() - interval '1 hour'
    )::integer,
    count(*)::integer
  into hourly_count, daily_count
  from public.evidence_submissions submission
  where submission.submitter_id = new.submitter_id
    and submission.created_at >= pg_catalog.now() - interval '24 hours';

  if hourly_count >= 5 then
    raise exception 'submission rate limit exceeded: 5 per hour';
  end if;

  if daily_count >= 20 then
    raise exception 'submission rate limit exceeded: 20 per 24 hours';
  end if;

  return new;
end;
$$;

revoke all on function private.enforce_submission_rate_limit() from public, anon, authenticated;

create trigger evidence_submissions_rate_limit
before insert on public.evidence_submissions
for each row execute function private.enforce_submission_rate_limit();

create or replace function private.flag_submission_duplicate_candidate()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  duplicate_exists boolean;
begin
  select exists (
    select 1
    from public.evidence_submissions candidate
    where candidate.submission_fingerprint = new.submission_fingerprint
      and candidate.id <> new.id
      and candidate.state <> 'rejected'
  ) into duplicate_exists;

  if duplicate_exists then
    insert into private.submission_moderation (
      submission_id,
      risk_flags
    ) values (
      new.id,
      array['duplicate_candidate']::text[]
    )
    on conflict (submission_id) do update
    set risk_flags = case
      when 'duplicate_candidate' = any(private.submission_moderation.risk_flags)
        then private.submission_moderation.risk_flags
      else pg_catalog.array_append(
        private.submission_moderation.risk_flags,
        'duplicate_candidate'
      )
    end,
    updated_at = pg_catalog.timezone('utc', pg_catalog.now());
  end if;

  return new;
end;
$$;

revoke all on function private.flag_submission_duplicate_candidate() from public, anon, authenticated;

create trigger evidence_submissions_flag_duplicate
  after insert on public.evidence_submissions
  for each row execute function private.flag_submission_duplicate_candidate();

create or replace function public.get_my_submission_dashboard()
returns table (
  id uuid,
  client_submission_id uuid,
  device_id text,
  observed_outcome text,
  state public.submission_state,
  created_at timestamptz,
  updated_at timestamptz,
  duplicate_candidate boolean
)
language sql
stable
security definer
set search_path = ''
as $$
  select
    submission.id,
    submission.client_submission_id,
    submission.device_id,
    submission.observed_outcome,
    submission.state,
    submission.created_at,
    submission.updated_at,
    exists (
      select 1
      from public.evidence_submissions candidate
      where candidate.submission_fingerprint = submission.submission_fingerprint
        and candidate.id <> submission.id
        and candidate.state <> 'rejected'
    ) as duplicate_candidate
  from public.evidence_submissions submission
  where submission.submitter_id = auth.uid()
  order by submission.created_at desc
  limit 100;
$$;

revoke all on function public.get_my_submission_dashboard() from public, anon;
grant execute on function public.get_my_submission_dashboard() to authenticated;

comment on function public.get_my_submission_dashboard() is
  'Returns only the current user''s submission status plus an opaque duplicate-candidate flag.';
