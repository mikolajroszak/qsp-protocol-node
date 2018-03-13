update audit_evt 
set fk_status = 'SB',
    tx_hash = ?,
    status_info = ?,
    report_uri = ?,
    audit_state = ?,
    report_hash = ?
where request_id = ? and fk_status in ('RV', 'TS')
