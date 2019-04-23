select coalesce(max(assigned_block_nbr), -1) as assigned_block_nbr
from audit_evt
