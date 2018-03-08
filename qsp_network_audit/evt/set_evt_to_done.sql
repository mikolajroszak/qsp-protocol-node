update audit_evt 
set fk_status = 'DN',
    status_info = ?,
    is_persisted = 1
where request_id = ?