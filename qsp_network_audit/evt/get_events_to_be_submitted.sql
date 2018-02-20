select *
from audit_evt
where status = 'TS' and submission_attempts <= ?