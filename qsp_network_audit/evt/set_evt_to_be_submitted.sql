update audit_evt 
set fk_status = 'TS',
    status_info = ?,
    tx_hash = ?,
    report_uri = ?,
    audit_state = ?,
    report_hash = ?,
    submission_attempts = audit_evt.submission_attempts + 1
where request_id = ? and fk_status = 'RV'
