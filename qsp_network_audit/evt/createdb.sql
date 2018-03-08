create table evt_status (
    id CHAR(2) primary key,
    description varchar(20) not null
);

insert into evt_status values (
    'RV', 'Received'
);

insert into evt_status values (
    'TS', 'To be submitted'
);
insert into evt_status values (
    'SB', 'Submitted'
);
insert into evt_status values (
    'DN', 'Done'
);
insert into evt_status values (
    'ER', 'Error'
);

create table audit_evt (
    request_id          string primary key,
    requestor           text not null,
    contract_uri        text not null,
    evt_name            varchar(100) not null,
    block_nbr           text not null,
    fk_status           char(2) not null,
    price               text not null,
    status_info         text,
    tx_hash             text default null,
    submission_attempts smallint not null default 0,
    is_persisted        boolean not null default false,
    report              text default null,
    foreign key(fk_status) references evt_status(id)
);