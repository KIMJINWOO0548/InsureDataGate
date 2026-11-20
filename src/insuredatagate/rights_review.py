"""Match purpose-specific rights declarations to a checked synthetic dataset."""

from hashlib import sha256
from pathlib import Path

from . import validator


PURPOSES = ('internal-eval', 'external-redistribution')
RECORDS_SCHEMA = 'insuredatagate.rights-records.v1'
REVIEW_SCHEMA = 'insuredatagate.rights-review.v1'
MAX_BYTES = 256 * 1024
MAX_RECORDS = 200
DECLARATIONS = {'SUPPORTS_USE': 'DECLARED_SUPPORT', 'RESTRICTS_USE': 'DECLARED_RESTRICTION'}


def _parse_records(raw: bytes) -> tuple[str, dict]:
    data = validator.strict_json(raw)
    if (not validator._keys(data, 'schema_version manifest_sha256 records')
            or data['schema_version'] != RECORDS_SCHEMA
            or type(data['manifest_sha256']) is not str
            or not validator.SHA256.fullmatch(data['manifest_sha256'])
            or type(data['records']) is not list or len(data['records']) > MAX_RECORDS):
        raise ValueError('Invalid rights records')

    records = {}
    for record in data['records']:
        if (not validator._keys(record, 'source_id source_sha256 purpose declaration reviewer_id evidence')
                or not validator._id(record['source_id']) or not validator._id(record['reviewer_id'])
                or type(record['source_sha256']) is not str
                or not validator.SHA256.fullmatch(record['source_sha256'])
                or record['purpose'] not in PURPOSES
                or type(record['declaration']) is not str or record['declaration'] not in DECLARATIONS):
            raise ValueError('Invalid rights record')
        evidence = record['evidence']
        if evidence is not None and (not validator._keys(evidence, 'document_id version section')
                                     or not all(validator._id(item) for item in evidence.values())):
            raise ValueError('Invalid evidence reference')
        key = (record['source_id'], record['purpose'])
        if key in records:
            raise ValueError('Duplicate source and purpose')
        records[key] = record

    return data['manifest_sha256'], records


def review_rights(manifest_path: Path, records_path: Path, purpose: str) -> dict:
    """Check the snapshot before looking at human declarations for one purpose."""
    if purpose not in PURPOSES:
        raise ValueError('Invalid rights review purpose')
    report = dict(
        schema_version=REVIEW_SCHEMA, purpose=purpose, status='UNAVAILABLE', reason='GATE_BLOCKED',
        snapshot=None, records_sha256=None, counts=None, sources=[],
    )
    gate = validator.verify(manifest_path)
    if gate['status'] != 'PASS':
        return report
    try:
        manifest = validator.read_snapshot(manifest_path, gate)['manifest']
    except (ValueError, OSError):
        return dict(report, reason='SNAPSHOT_CHANGED')
    report['snapshot'] = {key: gate[key] for key in ('dataset_id', 'version', 'manifest_sha256')}

    try:
        raw = validator.safe_read(records_path, MAX_BYTES)
    except (ValueError, OSError):
        return dict(report, reason='RECORDS_UNREADABLE')
    try:
        manifest_hash, records = _parse_records(raw)
    except ValueError:
        return dict(report, reason='RECORDS_INVALID')

    sources = {source['source_id']: source['sha256'] for source in manifest['sources']}
    matched_manifest = manifest_hash == gate['manifest_sha256']
    if matched_manifest and any(source_id not in sources for source_id, _ in records):
        return dict(report, reason='RECORDS_INVALID')

    counts = dict(sources=len(sources), declared_support=0, declared_restriction=0, manual_review_required=0)
    rows = []
    for source_id, source_hash in sorted(sources.items()):
        record = records.get((source_id, purpose))
        state, reason, evidence = 'MANUAL_REVIEW_REQUIRED', None, None
        if not matched_manifest:
            reason = 'MANIFEST_CHANGED'
        elif record is None:
            reason = 'MISSING_RECORD'
        elif record['source_sha256'] != source_hash:
            reason = 'SOURCE_CHANGED'
        elif record['evidence'] is None:
            reason = 'MISSING_EVIDENCE'
        else:
            state, evidence = DECLARATIONS[record['declaration']], record['evidence']
        counts[state.lower()] += 1
        rows.append(dict(source_id=source_id, source_sha256=source_hash, state=state, reason=reason, evidence=evidence))

    return dict(report, status='COMPLETE', reason=None, records_sha256=sha256(raw).hexdigest(), counts=counts, sources=rows)
