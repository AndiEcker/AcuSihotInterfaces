-- fully delete AssServer cache and re-insert only hotel ids 
-- .. (mostly done together with full delete of Reservation/Allocation objects within SF)

delete
--select * 
from res_group_clients;

delete
--select *
from res_groups;

delete
--select *
from res_inventories;

delete
--select *
from client_products;

delete
--select *
from product_types;

delete
--select *
from products;

delete
--select *
from external_refs;

delete
--select * 
from clients;

delete
--select *
from hotels;

INSERT INTO hotels VALUES ('1', 'BHC');
INSERT INTO hotels VALUES ('2', 'BHH');
INSERT INTO hotels VALUES ('3', 'HMC');
INSERT INTO hotels VALUES ('4', 'PBC');
INSERT INTO hotels VALUES ('107', 'PMA');
INSERT INTO hotels VALUES ('999', 'ANY');
--COMMIT;
