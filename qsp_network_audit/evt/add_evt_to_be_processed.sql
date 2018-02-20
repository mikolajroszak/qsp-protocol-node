insert or ignore into 
audit_evt(
    request_id,
    requestor,
    contract_uri,
    beep, 
    evt_name, 
    block_nbr, 
    fk_status
)
values(?, ?, ?, ?, ?, ?, 'RV')