create table if not exists evt_status (
    id CHAR(2) primary key,
    description varchar(20) not null
);

insert or ignore into evt_status values (
    'RV', 'Received'
);
insert or ignore into evt_status values (
    'PG', 'In progress'
);
insert or ignore into evt_status values (
    'TS', 'To be submitted'
);
insert or ignore into evt_status values (
    'DN', 'Done'
);

create table if not exists evt (
    id                  integer primary key,
    beep                integer not null,
    evt_name            varchar(100) not null,
    block_nbr           bigint not null,
    fk_status           char(2) not null, 
    tx_hash             varchar(100) default null,
    submission_attempts smallint not null default 0,
    is_persisted        boolean not null default false,
    audit_report        text default null,
    foreign key(fk_status) references evt_status(id) 
);