select count(*) as pending_count
from audit_evt
where fk_status <> 'DN'
