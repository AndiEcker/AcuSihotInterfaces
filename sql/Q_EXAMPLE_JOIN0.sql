-- nice example to see the difference to specify a filter in an outer join in the ON clause and in the WHERE clause
-- taken from http://www.tech-recipes.com/rx/47637/inner-and-left-outer-join-with-where-clause-vs-on-clause/


CREATE TABLE FRUIT (
name VARCHAR2(25),
color INT
);


CREATE TABLE FRUIT_COLOR
(
id INT,
name VARCHAR(25)
);

INSERT into FRUIT_COLOR VALUES (1,'orange');
INSERT into FRUIT_COLOR VALUES(2,'yellow');
INSERT into FRUIT_COLOR VALUES (3,'red');
INSERT into FRUIT_COLOR VALUES (4,'blue');

INSERT into FRUIT VALUES ('banana',2);
INSERT into FRUIT VALUES ('mango',2);
INSERT into FRUIT VALUES ('orange',1);
INSERT into FRUIT VALUES ('apple',3);
INSERT into FRUIT VALUES ('grapes',null);
INSERT into FRUIT VALUES ('avocado',null);


SELECT * from FRUIT;

SELECT * from FRUIT_COLOR;

-- this what we would exception to filter on apple in an outer join
SELECT  *
FROM    FRUIT F LEFT outer join FRUIT_COLOR FC
ON      F.color = FC.id
WHERE   F.name='apple';

-- this one shows all 6 fruits although we are filtering on apple !!!!! so the filter in the ON clause is only filtering the outer joined table
SELECT  *
from    FRUIT F LEFT outer join FRUIT_COLOR FC
ON      F.color = FC.id AND F.name='apple';