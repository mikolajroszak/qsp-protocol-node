update audit_evt 
set fk_status = 'AS',
    evt_name = ?,
    status_info = ?,
    is_persisted = 1
where request_id = ? and fk_status in ('RQ')
