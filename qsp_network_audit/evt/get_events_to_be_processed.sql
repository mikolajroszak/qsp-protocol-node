select *
from evt
where (evt.fk_status == 'PG' and evt.beep < ? ) or evt.fk_status == 'RV'