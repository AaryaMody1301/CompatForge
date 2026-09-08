begin;

create extension if not exists pgtap with schema extensions;

create temporary table phase6c_fixture(payload jsonb) on commit drop;
insert into phase6c_fixture(payload) values (
  '{
    "record_type": "community_evidence_submission",
    "schema_version": "1.0.0",
    "client_submission_id": "22222222-2222-2222-2222-222222222222",
    "prepared_at": "2026-09-08T04:00:00Z",
    "evidence_ready": false,
    "target_device_id": "usb:0403:6001",
    "handoff": {
      "schema_version": "1.0.0",
      "sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
      "user_approved_export": true
    },
    "configuration": {
      "host": {
        "manufacturer": "Acer",
        "model": "Aspire 14 AI"
      },
      "operating_system": {
        "family": "windows",
        "version": "11",
        "build": "25H2"
      },
      "architecture": "arm64",
      "connection_path": "direct_port",
      "drivers": [
        {
          "name": "FTDI D2XX",
          "provider": "FTDI",
          "version": "1.2.3"
        }
      ]
    },
    "reproduction": {
      "outcome": "works_with_conditions",
      "observed_at": "2026-09-01T10:00:00Z",
      "steps_summary": "Connected the reviewed FT232R target directly and reproduced the documented operation successfully on the stated host.",
      "conditions": ["The tested workflow used the stated driver version."],
      "limitations": ["This is a single-host community reproduction."],
      "firmware_version": "1.0",
      "software_version": "8.1"
    },
    "publication": {
      "anonymized_publication": true,
      "consent_version": "1.0"
    },
    "privacy": {
      "contains_raw_diagnostic": false,
      "contains_serial_numbers": false,
      "contains_network_identifiers": false,
      "contains_unrelated_usb_inventory": false,
      "automatic_publication": false
    },
    "references": []
  }'::jsonb
);

select plan(25);

select ok(
  to_regclass('private.community_observation_candidates') is not null,
  'private canonical observation candidate table exists'
);

select ok(
  not has_table_privilege(
    'authenticated',
    'private.community_observation_candidates',
    'SELECT'
  ),
  'authenticated users cannot directly read canonical observation candidates'
);

select ok(
  not has_table_privilege(
    'authenticated',
    'private.community_observation_candidates',
    'UPDATE'
  ),
  'authenticated users cannot directly mutate canonical observation candidates'
);

select ok(
  has_function_privilege('authenticated', 'public.get_moderator_role()', 'EXECUTE'),
  'authenticated users can ask for their bounded moderator role'
);

select ok(
  not has_function_privilege('anon', 'public.get_moderator_role()', 'EXECUTE'),
  'anonymous users cannot ask for moderator context'
);

select ok(
  has_function_privilege('authenticated', 'public.get_moderation_queue()', 'EXECUTE'),
  'authenticated sessions can invoke the moderation queue wrapper'
);

select ok(
  has_function_privilege(
    'authenticated',
    'public.review_community_submission(uuid,text,text)',
    'EXECUTE'
  ),
  'authenticated sessions can invoke the review wrapper which performs its own role check'
);

select ok(
  has_function_privilege(
    'authenticated',
    'public.publish_community_submission(uuid,text,text)',
    'EXECUTE'
  ),
  'authenticated sessions can invoke the publish wrapper which performs its own admin check'
);

select ok(
  not has_function_privilege(
    'anon',
    'public.publish_community_submission(uuid,text,text)',
    'EXECUTE'
  ),
  'anonymous sessions cannot invoke the publication RPC'
);

select ok(
  not (
    select p.prosecdef
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'public'
      and p.proname = 'get_moderation_queue'
  ),
  'public moderation queue is a security-invoker wrapper'
);

select ok(
  (
    select p.prosecdef
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'private'
      and p.proname = 'get_moderation_queue_impl'
  ),
  'private moderation queue implementation is security definer'
);

select ok(
  (
    select p.prosecdef
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'private'
      and p.proname = 'review_community_submission_impl'
  ),
  'private review implementation is security definer'
);

select ok(
  (
    select p.prosecdef
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'private'
      and p.proname = 'publish_community_submission_impl'
  ),
  'private publication implementation is security definer'
);

select ok(
  (
    select pg_catalog.jsonb_array_length(
      private.community_canonicalization_errors(payload)
    )
    from phase6c_fixture
  ) = 0,
  'review fixture has no canonicalization blockers'
);

select ok(
  (
    select pg_catalog.jsonb_array_length(
      private.community_canonicalization_errors(
        pg_catalog.jsonb_set(payload, '{configuration,architecture}', '"unknown"'::jsonb)
      )
    )
    from phase6c_fixture
  ) > 0,
  'unknown architecture blocks canonical publication'
);

select ok(
  (
    select pg_catalog.jsonb_array_length(
      private.community_canonicalization_errors(
        pg_catalog.jsonb_set(
          payload,
          '{reproduction,limitations}',
          pg_catalog.jsonb_build_array(pg_catalog.repeat('x', 501))
        )
      )
    )
    from phase6c_fixture
  ) > 0,
  'canonical observation length limits are enforced before acceptance'
);

select is(
  (
    select private.build_community_observation(
      '11111111-1111-1111-1111-111111111111'::uuid,
      payload,
      'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
      '2026-09-08T05:00:00Z'::timestamptz
    ) ->> 'observation_id'
    from phase6c_fixture
  ),
  'obs_community_11111111111111111111111111111111',
  'community observation ID is deterministic from the private submission ID'
);

select is(
  (
    select private.build_community_observation(
      '11111111-1111-1111-1111-111111111111'::uuid,
      payload,
      'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
      '2026-09-08T05:00:00Z'::timestamptz
    ) #>> '{evidence,source_type}'
    from phase6c_fixture
  ),
  'community_report',
  'accepted candidate is explicitly classified as community evidence'
);

select is(
  (
    select private.build_community_observation(
      '11111111-1111-1111-1111-111111111111'::uuid,
      payload,
      'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
      '2026-09-08T05:00:00Z'::timestamptz
    ) #>> '{evidence,source_url}'
    from phase6c_fixture
  ),
  'https://compatforge.dev/evidence/obs_community_11111111111111111111111111111111',
  'canonical community evidence reserves a stable public evidence URL'
);

select ok(
  (
    select not (
      private.build_community_observation(
        '11111111-1111-1111-1111-111111111111'::uuid,
        payload,
        'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
        '2026-09-08T05:00:00Z'::timestamptz
      ) ? 'submitter_id'
    )
    from phase6c_fixture
  ),
  'canonical observation does not contain submitter identity'
);

select ok(
  (
    select private.build_community_observation(
      '11111111-1111-1111-1111-111111111111'::uuid,
      payload,
      'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
      '2026-09-08T05:00:00Z'::timestamptz
    ) = private.build_community_observation(
      '11111111-1111-1111-1111-111111111111'::uuid,
      payload,
      'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
      '2026-09-08T05:00:00Z'::timestamptz
    )
    from phase6c_fixture
  ),
  'canonical conversion is deterministic for identical inputs and recorded_at'
);

select ok(
  pg_catalog.strpos(
    pg_get_functiondef('private.review_community_submission_impl(uuid,text,text)'::regprocedure),
    'canonicalization blockers'
  ) > 0,
  'acceptance refuses submissions with canonicalization blockers'
);

select ok(
  pg_catalog.strpos(
    pg_get_functiondef('private.publish_community_submission_impl(uuid,text,text)'::regprocedure),
    'observation SHA-256 does not match the accepted candidate'
  ) > 0,
  'publication verifies the exact accepted observation hash'
);

select ok(
  pg_catalog.strpos(
    pg_get_functiondef('private.publish_community_submission_impl(uuid,text,text)'::regprocedure),
    'admin authorization required'
  ) > 0,
  'publication is guarded by an admin-only authorization check'
);

select ok(
  pg_catalog.strpos(
    pg_get_functiondef('private.record_submission_state_event()'::regprocedure),
    'compatforge.transition_reason'
  ) > 0,
  'state-event audit trail records moderator and publication reasons'
);

select * from finish();
rollback;
