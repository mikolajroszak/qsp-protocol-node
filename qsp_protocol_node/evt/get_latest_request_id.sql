select coalesce(max(request_id), -1) as request_id
from audit_evt
