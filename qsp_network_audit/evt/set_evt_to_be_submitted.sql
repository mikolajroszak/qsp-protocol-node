update evt 
set fk_status = 'TS',
    tx_hash = ?,
    audit_report = ?,
    submission_attempts = evt.submission_attempts + 1
where id = ?