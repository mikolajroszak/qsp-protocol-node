insert or ignore into 
audit_evt(
    request_id,
    requestor,
    contract_uri,
    evt_name, 
    block_nbr, 
    fk_status
)
values(?, ?, ?, ?, ?, 'RV')