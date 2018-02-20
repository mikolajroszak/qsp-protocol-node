update audit_evt 
set fk_status = 'TS',
    status_info = ?,
    report = ?
where id = ?