select coalesce(max(beep), -1) as beep
from audit_evt