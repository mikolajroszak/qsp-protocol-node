/***************************************************************************************************
 *                                                                                                 *
 * (c) 2018 Quantstamp, Inc. All rights reserved.  This content shall not be used, copied,         *
 * modified, redistributed, or otherwise disseminated except to the extent expressly authorized by *
 * Quantstamp for credentialed users. This content and its use are governed by the Quantstamp      *
 * Demonstration License Terms at <https://s3.amazonaws.com/qsp-protocol-license/LICENSE.txt>.     *
 *                                                                                                 *
 **************************************************************************************************/

create table evt_status (
    id CHAR(2) primary key,
    description varchar(20) not null
);

insert into evt_status(id, description) values
    ('AS', 'Assigned'),
    ('TS', 'To be submitted'),
    ('SB', 'Submitted'),
    ('DN', 'Done'),
    ('ER', 'Error');

create table audit_type (
    id CHAR(2) primary key,
    description varchar(20) not null
);

insert into audit_type(id, description) values
    ('AU', 'Audit'),
    ('PC', 'Police check');

create table audit_evt (
    request_id          string not null,
    requestor           text not null,
    contract_uri        text not null,
    evt_name            varchar(100) not null,
    block_nbr           text not null,
    fk_status           char(2) not null,
    fk_type             char(2) not null,
    price               text not null,
    status_info         text,
    tx_hash             text default null,
    submission_attempts smallint not null default 0,
    is_persisted        boolean not null default false,
    audit_uri           text default null,
    audit_hash          text default null,
    audit_state         smallint default null,
    full_report         text default null,
    compressed_report   text default null,
    primary key(request_id, fk_type),
    foreign key(fk_type) references audit_type(id),
    foreign key(fk_status) references evt_status(id)
);
