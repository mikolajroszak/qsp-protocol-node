update audit_evt 
set fk_status = 'SB',
    tx_hash = ?,
    status_info = ?,
    report_uri = ?,
    report_hash = ?,
    audit_state = ?
where request_id = ? and fk_status = 'TS'
