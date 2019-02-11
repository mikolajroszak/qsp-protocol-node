update audit_evt
set fk_status = 'ER',
    status_info = ?
where request_id = ?
