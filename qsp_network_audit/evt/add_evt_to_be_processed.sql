insert or ignore into 
audit_evt(
    request_id,
    requestor,
    contract_uri,
    evt_name, 
    block_nbr,
    status_info,
    fk_status
)
values(?, ?, ?, ?, ?, ?, 'RV')