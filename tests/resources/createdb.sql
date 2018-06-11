drop table if exists evt_status;
drop table if exists audit_evt;

create table evt_status (
    id CHAR(2) primary key,
    description varchar(20) not null
);

insert into evt_status(id, description) values ('RV', 'Received'),
    ('TS', 'To be submitted'),
    ('SB', 'Submitted'),
    ('DN', 'Done'),
    ('ER', 'Error');

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
    report_uri          text default null,
    report_hash         text default null,
    audit_state         smallint default null,
    foreign key(fk_status) references evt_status(id)
);
