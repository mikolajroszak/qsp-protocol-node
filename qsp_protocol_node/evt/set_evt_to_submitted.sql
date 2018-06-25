update audit_evt 
set fk_status = 'SB',
    tx_hash = ?,
    status_info = ?,
    audit_uri = ?,
    audit_hash = ?,
    audit_state = ?
where request_id = ? and fk_status = 'TS'
