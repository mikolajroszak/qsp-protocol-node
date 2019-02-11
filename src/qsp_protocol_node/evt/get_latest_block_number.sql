select coalesce(max(block_nbr), -1) as block_nbr
from audit_evt
