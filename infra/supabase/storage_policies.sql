-- Supabase private storage policy notes for qcm-artifacts-private.
-- Apply after creating the private bucket.

drop policy if exists "owners read own artifact objects" on storage.objects;
drop policy if exists "owners upload own artifact objects" on storage.objects;

create policy "owners read own artifact objects"
on storage.objects
for select
to authenticated
using (
  bucket_id = 'qcm-artifacts-private'
  and (storage.foldername(name))[1] = auth.uid()::text
);

create policy "owners upload own artifact objects"
on storage.objects
for insert
to authenticated
with check (
  bucket_id = 'qcm-artifacts-private'
  and (storage.foldername(name))[1] = auth.uid()::text
);
