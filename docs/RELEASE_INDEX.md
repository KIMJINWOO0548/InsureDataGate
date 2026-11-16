# Checked-snapshot release index

`python -m insuredatagate release-index MANIFEST --output NEW_JSON`

Creates a deterministic `insuredatagate.release-index.v1` JSON inventory after full validation and checked rereading of every declared file. It binds the manifest digest, file digests/byte counts, dataset/version and split counts to case/group/split/source references. Sources include their declared path, digest, license and status. Raw inputs, gold answers, source contents and reviewer/creator names are omitted.

This is a local release inventory, not an authenticated approval, rights certificate, semantic/paraphrase leakage detector or automatic publishing workflow. Rights/status strings are declarations. Metadata including dataset/case/group/source IDs, paths and license text remains visible: inspect it before sharing. Hashes prove consistency, not authenticity. The index describes the checked snapshot, not subsequent dataset mutations; rerun after changes. No background monitoring or transactional filesystem guarantee is provided.

Invalid inputs or mutation between validation and checked reread return 1 and create no index. Existing outputs are never overwritten (exit 2); write/close failures use the same cleanup as other commands. Output is exclusive creation and is independent of model-input export. Existing v1 reports and export format are unchanged. Runtime remains offline and standard-library only.

## Verification (2026-11-16)

- Implementer: four tests failed before the command existed; final focused suite passed 5/5, including deterministic redaction, tampering refusal, existing-output preservation and repinned snapshot identity.
- Independent reviewer: focused suite 5/5; separate manifest/cases/gold mutation after verification each returned 1 without creating an index or exposing injected private contents.
- Independent reviewer: `PYTHONPATH=src python -m unittest discover -s tests -q` ran 179 tests, OK with 14 skipped (70.677 seconds). Skips are not passing coverage. No remote CI result is claimed.
- Existing filesystem concurrent-replacement/hardlink limitations remain unchanged. Generated metadata still requires disclosure review before publication.
