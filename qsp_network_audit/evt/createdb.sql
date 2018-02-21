create table if not exists evt_status (
    id CHAR(2) primary key,
    description varchar(20) not null
);

insert or ignore into evt_status values (
    'RV', 'Received'
);

insert or ignore into evt_status values (
    'TS', 'To be submitted'
);
insert or ignore into evt_status values (
    'SB', 'Submitted'
);
insert or ignore into evt_status values (
    'DN', 'Done'
);
insert or ignore into evt_status values (
    'ER', 'Error'
);

create table if not exists audit_evt (
    id                  integer primary key,
    request_id          text not null,
    requestor           text not null,
    contract_uri        text not null,
    beep                integer not null,
    evt_name            varchar(100) not null,
    block_nbr           bigint not null,
    fk_status           char(2) not null,
    status_info         varchar(300) not null, 
    tx_hash             varchar(100) default null,
    submission_attempts smallint not null default -1,
    is_persisted        boolean not null default false,
    report              text default null,
    foreign key(fk_status) references evt_status(id)
);