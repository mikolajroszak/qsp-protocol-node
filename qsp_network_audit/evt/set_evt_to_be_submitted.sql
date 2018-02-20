update audit_evt 
set fk_status = 'TS',
    report = ?
where id = ?