update audit_evt 
set fk_status = 'TS',
    status_info = ?,
    tx_hash = ?,
    report = ?,
    submission_attempts = audit_evt.submission_attempts + 1
where request_id = ?