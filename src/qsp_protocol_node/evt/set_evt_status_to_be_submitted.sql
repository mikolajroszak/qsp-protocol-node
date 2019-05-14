update audit_evt
set fk_status = 'TS',
    status_info = ?,
    tx_hash = ?,
    audit_uri = ?,
    audit_hash = ?,
    audit_state = ?,
    full_report = ?,
    compressed_report = ?,
    submission_block_nbr = ?,
    submission_attempts = audit_evt.submission_attempts + 1
where request_id = ? and (fk_status = 'AS' or fk_status = 'TS' or fk_status = 'SB')
