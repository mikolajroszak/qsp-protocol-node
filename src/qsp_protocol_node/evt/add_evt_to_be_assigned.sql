insert into
audit_evt(
    request_id,
    requestor,
    contract_uri,
    evt_name,
    assigned_block_nbr,
    status_info,
    fk_status,
    fk_type,
    price
)
values(?, ?, ?, ?, ?, ?, 'AS', ?, ?)
