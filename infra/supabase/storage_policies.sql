-- Supabase private storage policy notes for qcm-artifacts-private.
-- Apply after creating the private bucket.

create policy if not exists "owners read own artifact objects"
on storage.objects
for select
to authenticated
using (
  bucket_id = 'qcm-artifacts-private'
  and (storage.foldername(name))[1] = auth.uid()::text
);

create policy if not exists "owners upload own artifact objects"
on storage.objects
for insert
to authenticated
with check (
  bucket_id = 'qcm-artifacts-private'
  and (storage.foldername(name))[1] = auth.uid()::text
);
