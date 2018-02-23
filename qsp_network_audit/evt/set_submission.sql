update audit_evt 
set submission_attempts = evt.submission_attempts + 1,
    tx_hash = ?,
    fk_status = 'ST'
where id = ? 