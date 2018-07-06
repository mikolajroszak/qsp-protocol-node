select count(*) as pending_count
from audit_evt
where fk_status not in ('DN', 'ER')
