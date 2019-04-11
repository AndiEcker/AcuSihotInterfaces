# Interface Suite

>This repository is providing tools and processes for to migrate and synchronize system configuration, room status, 
clients, ownerships and reservations between Sihot.PMS, Acumen and Salesforce.

[![Code Size](https://img.shields.io/github/languages/code-size/AndiEcker/AcuSihotInterfaces.svg)](#interface-suite)
[![Issues](https://img.shields.io/github/issues/AndiEcker/AcuSihotInterfaces.svg)](#interface-suite)
[![Last Commit](https://img.shields.io/github/last-commit/AndiEcker/AcuSihotInterfaces.svg)](#interface-suite)

The code-base gets stripped before any push to this repository for to not publish any internals like the names of our
servers, users and the passwords. Therefore this suite cannot be directly used in other environments without additional
configuration steps, but at least we hope that you can still use parts of it for your applications.

Big thanks to our IT managers (Gary and Søren) for to let us developers publish parts of our in-house applications to
the community.


## Available Applications

This interface suite project is including the following commands/tools - most of them are command line applications,
apart from AcuSihotMonitor and SihotResImport, which are providing a (kivy) user interface:

| Command | Description | Used Sihot.PMS Interfaces |
| :--- | :--- | :---: |
| AcuServer | Synchronize room status changes from Sihot.PMS onto Acumen | Sxml, Web |
| [AcuSihotMonitor](#acusihotmonitor-application) | Monitor the Acumen and Sihot interfaces and servers | Kernel, Web, Sxml |
| [BssServer](#bssserver-application) | Listening to Sihot SXML interface and updating AssCache/Postgres and Salesforce | Sxml, Web |
| [ClientQuestionnaireExport](#clientquestionnaireexport-application) | Export check-outs from Sihot to CSV file | Web |
| KernelGuestTester | Client/Guest interface testing tool | Kernel |
| MatchcodeToObjId | Get guest OBJID from passed matchcode | Kernel |
| SfClientValidator | Salesforce Client Data Validator | - |
| ShSfClientMigration | Migrate guests from Sihot to Salesforce | Kernel, Web |
| SihotMigration | Migration of clients and reservations from Acumen to Sihot.PMS | Kernel, Web |
| [SihotOccLogChecker](#sihotocclogchecker-application) | Sihot SXML interface log file checks and optional Acumen room occupation status fixes | Sxml |
| [SihotResImport](#sihotresimport-application) | Create/Update/Cancel reservations from CSV/TXT/JSON files within Sihot.PMS | Kernel, Web |
| SihotResSync | Synchronize clients and reservations changed in Sihot.PMS onto Acumen | Kernel, Web |
| [SysDataMan](#sysdataman-application) | Initialize, pull, compare or push data against Acumen, AssCache, Salesforce and/or Sihot | Kernel, Web |
| TestConnectivity | Test connectivity to SMTP and Acumen/Oracle servers | - |
| [WatchPupPy](#watchpuppy-application) | Supervise always running servers or periodically execute command | Kernel, Web |
| WebRestTester | Reservation interface testing tool | Web |


### Installation instructions

Most of the command line tools don't have a GUI (graphical user interface) - these need only to be distributed/provided
into any folder where the user has execution permissions (e.g. in Windows in C:\Program Files or on any network drive).

For applications of this project with an GUI (like e.g. SihotResImport or AcuSihotMonitor) please first copy the EXE
file and KV file of the application to any folder where the user has execution privileges. Then the following steps 
have to be done to install it for each single user on the users machine:

* Create a new folder with the name if the application (e.g. SihotResImport) under %LOCALAPPDATA% (in Windows situated
 normally under C:\users\<user name>\AppData\Local\ if the user has the profile on the local C: drive, else within the
 AppData\Local folder of the user profile located on our servers).

* Copy the INI file of the application (e.g. SihotResImport.ini) into this folder (created in the last step).

* Create a new shortcut on the user’s desktop with the application name (e.g. “Sihot Reservation Import”). Then within
 the target field put the full absolute path to application EXE file (e.g. “U:\SihotResImport\SihotResImport.exe”).
 And finally put the path of the new folder created in the first step (e.g. 
 “C:\Users\<user name>\AppData\Local\SihotResImport”) into the Start In field of the shortcut. 

 
### Command line arguments

Most of the available commands are using the same command line options. All names of the following command line options
are case-sensitive. The following table is listing them ordered by the option name (see the first column named Option):

| Option | Description | Default | Short option | Commands |
| --- | --- | --- | --- | --- |
| acuDSN | Data source name of the Acumen/Oracle database system | SP.TEST | d | AcuServer, AcuSihotMonitor, SysDataMan, KernelGuestTester, SihotMigration, SihotOccLogChecker, SihotResImport, SihotResSync, TestConnectivity, WatchPupPy |
| acuPassword | User account password on Acumen/Oracle system | - | p | AcuServer, AcuSihotMonitor, SysDataMan, KernelGuestTester, SihotMigration, SihotOccLogChecker, SihotResImport, SihotResSync, TestConnectivity, WatchPupPy |
| acuUser | User name of Acumen/Oracle system | SIHOT_INTERFACE | u | AcuServer, AcuSihotMonitor, SysDataMan, KernelGuestTester, SihotMigration, SihotOccLogChecker, SihotResImport, SihotResSync, TestConnectivity, WatchPupPy |
| addressesToValidate | Post addresses to be validated (invalidated, not validated, ...) | - | A | SfClientValidator |
| assDSN | Database name of the AssCache/Postgres database | ass_cache | N | SysDataMan, BssServer |
| assPassword | User account password for the AssCache/Postgres database | - | P | SysDataMan, BssServer |
| assUser | User account name for the AssCache/Postgres database | 'postgres' | U | SysDataMan, BssServer |
| breakOnError | Abort processing if an error occurs (0=No, 1=Yes) | 0 | b | SihotMigration, SihotResImport, SihotResSync, WatchPupPy |
| client | Acumen client reference / Sihot matchcode to be sent | - | c | KernelGuestTester |
| clientsFirst | Migrate first the clients then the reservations (0=No, 1=Yes) | 0 | q | SihotMigration, SihotResSync |
| cmdLine | Command [line] to execute | - | x | WatchPupPy |
| cmdInterval | synchronization interval in seconds | 3600 | l | BssServer, WatchPupPy |
| compare | Compare/Check ass_cache database against (ac=Acumen, sh=Sihot, sf=Salesforce) for (C=Clients, P=Products, R=Reservations) data | - | V | SysDataMan |
| correctSystem | Correct/Fix data for system (Acu=Acumen, Ass=AssCache) | - | A | SihotOccLogChecker |
| dateFrom | Start date/time of date range | (depends on command) | F | ClientQuestionnaireExport, ShSfClientMigration, SihotOccLogChecker |
| dateTill | End date/time of date range | (depends on command) | T | ClientQuestionnaireExport, ShSfClientMigration, SihotOccLogChecker |
| debugLevel | Display additional debugging info on console output (0=disable, 1=enable, 2=verbose, 3=verbose with timestamp) | 0 | D | (all) |
| emailsToValidate | Emails to be validated (invalidated, not validated, ...) | not validated | E | SfClientValidator |
| envChecks | Number of environment checks per command interval | 4 | n | WatchPupPy |
| exportFile | full path and name of the export CSV file | - | x | ClientQuestionnaireExport |
| filterSfClients | Additional WHERE filter clause for Salesforce SOQL client fetch query | - | W | SfClientValidator |
| filterSfRecTypes | List o fSalesforce client record type(s) to be processed | ['Rentals'] | R | SfClientValidator |
| help | Show help on all the available command line argument options | - | h | (all) |
| includeCxlRes | Include also cancelled reservations (0=No, 1=Yes) | 0 | I | SihotMigration |
| init | Initialize/Recreate AssCache/Postgres database (0=No, 1=Yes) | 0 | I | SysDataMan |
| jsonPath | Import path and file mask for OTA JSON files | C:/JSON_Import/R*.txt | j | SihotResImport |
| logFile | Duplicate stdout and stderr message into a log file | - | L | (all) |
| matchcode | Guest matchcode to convert to the associated object ID | - | m | MatchcodeToObjId |
| migrationMode | Skip room swap and hotel movement requests (0=No, 1=Yes) | - | M | SihotResSync |
| phonesToValidate | Phones to be validated (invalidated, not validated, ...) | - | P | SfClientValidator |
| pull | Pull (C=Clients, P=Products, R=Reservations) data from Acumen/Sihot/Salesforce into AssCache | - | S | SysDataMan |
| push | Push/Update (C=Clients, P=Products, R=Reservations) data from AssCache onto Acumen/Salesforce/Sihot | - | W | SysDataMan |
| rciPath | Import path and file mask for RCI CSV-tci_files | C:/RCI_Import/*.csv | Y | SihotResImport |
| sfIsSandbox | Use Salesforce sandbox (instead of production) | True | s | SysDataMan, SfClientValidator, ShSfClientMigration, SihotResImport |
| sfPassword | Salesforce user account password | - | a | SysDataMan, SfClientValidator, ShSfClientMigration, SihotResImport |
| sfToken | Salesforce user account token | - | o | SysDataMan, SfClientValidator, ShSfClientMigration, SihotResImport |
| sfUser | Salesforce account user name | - | y | SysDataMan, SfClientValidator, ShSfClientMigration, SihotResImport |
| shClientPort | IP port of the Sxml interface of this server | 11000 (AcuServer) or 12000 (BssServer) | m | AcuServer, BssServer |
| shMapClient | Guest/Client mapping of xml to db items | SH_CLIENT_MAP | m | SihotResImport, SihotResSync |
| shMapRes | Reservation mapping of xml to db items | SH_RES_MAP | n | SihotResImport, SihotResSync |
| shServerIP | IP address of the Sihot interface server | localhost | i | AcuServer, AcuSihotMonitor, SysDataMan, BssServer, ClientQuestionnaireExport, KernelGuestTester, ShSfClientMigration, SihotMigration, SihotResImport, SihotResSync, WatchPupPy |
| shServerKernelPort | IP port of the KERNEL interface of this server | 14772 | k | AcuSihotMonitor, SysDataMan, KernelGuestTester, SihotMigration, SihotResImport, SihotResSync, WatchPupPy |
| shServerPort | IP port of the WEB interface of the Sihot server | 14777 | w | AcuSihotMonitor, SysDataMan, ClientQuestionnaireExport, ShSfClientMigration, SihotMigration, SihotResImport, SihotResSync, WatchPupPy |
| shTimeout | Timeout in seconds for TCP/IP connections | 1869.3 | t | AcuServer, AcuSihotMonitor, SysDataMan, BssServer, ClientQuestionnaireExport, KernelGuestTester, ShSfClientMigration, SihotMigration, SihotResImport, SihotResSync, WatchPupPy |
| shUseKernelForClient | Used interface for clients (0=web, 1=kernel) | 1 | g | SihotResImport, SihotResSync |
| shUseKernelForRes | Used interface for reservations (0=web, 1=kernel) | 0 | z | SihotResImport, SihotResSync |
| shXmlEncoding | Charset used for the xml data | cp1252 | e | AcuServer, AcuSihotMonitor, SysDataMan, BssServer, ClientQuestionnaireExport, KernelGuestTester, ShSfClientMigration, SihotMigration, SihotResImport, SihotResSync, WatchPupPy |
| smtpServerUri | SMTP error notification server URI [user[:pw]@]host[:port] | - | c | AcuServer, SysDataMan, BssServer, SfClientValidator, ShSfClientMigration, SihotOccLogChecker, SihotResImport, SihotResSync, TestConnectivity, WatchPupPy |
| smtpFrom | SMTP Sender/From address | - | f | AcuServer, SysDataMan, BssServer, SfClientValidator, ShSfClientMigration, SihotOccLogChecker, SihotResImport, SihotResSync, TestConnectivity, WatchPupPy |
| smtpTo | List/Expression of SMTP Receiver/To addresses | - | r | AcuServer, SysDataMan, BssServer, SfClientValidator, ShSfClientMigration, SihotOccLogChecker, SihotResImport, SihotResSync, TestConnectivity, WatchPupPy |
| syncDateRange | Restrict sync. of res. to: H=historical, M=present and 1 month in future, P=present and all future, F=future only, Y=present and 1 month in future and all for hotels 1 4 and 999, Y<nnn>=like Y plus the nnn oldest records in the sync queue | - | R | SihotMigration, SihotResSync |
| tciPath | Import path and file mask for Thomas Cook R*.TXT-tci_files | C:/TourOp_Import/R*.txt | j | SihotResImport |
| warningsMailToAddr | List/Expression of warnings SMTP receiver/to addresses (if differs from smtpTo) | - | v | SysDataMan, BssServer, SfClientValidator, ShSfClientMigration, SihotOccLogChecker, SihotResImport, SihotResSync |

Currently all the 26 ascii lower case letters are used for the command line argument short options, some of them are
hard-coded by python (like e.g. the -h switch for to show the help screen). The upper case character options -D and -L
are hard-coded by the ae_console_app module. Some options like -m are used and interpreted differently in several
command line applications.

The following lower case letters could be used more easily as short options than others (for to prevent
duplicates/conflicts) for future/upcoming command line options with less conflicts: | l | m | n | q | M | X | Y | Z |.


### System Data Fields

#### Available Client Fields

The table underneath is listing all the fields - alphabetically ordered by the field name - for to store the data of
each of our clients/guests:

 Field Name | Field Type | Description | Example Values |
| --- | --- | --- | --- |
| AcuId | String | Acumen Client Reference, Sihot Matchcode | X123456, E234567 |
| AssId | Integer | Primary key value of ass_cache.clients table | 123456789 |
| City | String | City name of Client/Guest | Madrid, London, Berlin |
| Comment | String | Client/Guest Comment | Disabled, Wheel Chair, Has Kids, Has Pets |
| Country | String | ISO2 Country code of Client/Guest | ES, DE, UK |
| Currency | String | Currency code of Client/Guest | GBP, EUR, USD |
| DOB | Date | Birthdate of Client/Guest | 15-12-1962 |
| Email | String | First email address of Client/Guest | john.smith@provider.com |
| EmailB | String | Second email address of Client/Guest | jim.knopf@company.com |
| ExtRefs | String or List(Type, Id) | External Client/Guest Ids/Reference-numbers | ((RCI, 5-67890), (SF, 001234ABC67890QEI1)) |
| ExtRefs\<n\>Type | String | Type of External Client/Guest Id | RCI, SF, KEYS |
| ExtRefs\<n\>Id | String | Id/Reference-number of External Client/Guest Id | 5-67890, 001234ABC67890QEI1 |
| Fax | String | Fax number of Client/Guest | 004898765432 |
| Forename | String | Firstname of Client/Guest | John, Walter |
| GuestType | String | Sihot Type of Client/Guest | 1=Individual, 6=Company |
| Language | String | ISO2 Language code of Client/Guest | ES, EN, DE |
| MarketSource | String | Marketing Source | TO, BK |
| MobilePhone | String | Main mobile phone number of Client/Guest | 0034678901234 |
| MobilePhoneB | String | Second mobile phone number of Client/Guest | 0046789012345 |
| Name | String | Full name of Client/Guest | John Smith |
| Nationality | String | Nationality of Client/Guest (ISO2 Country code) | ES, DE, UK |
| Password | String | Password of Client/Guest | secRet12345, MyPassword |
| Phone | String | Home phone number of Client/Guest | 0034678901234, 004987654321 |
| POBox | String | Postbox of Client/Guest | 12345, ABC123 |
| Postal | String | ZIP code of Client/Guest city | A1234, 234567 |
| ProductTypes | String or List(Char) | Product types owned by this client (O=owner, I=investor, K=keys, E=ELPP) | OIK |
| RciId | String | First/Main RCI reference of Client/Guest | 5-123456, 9876-54321 |
| Salutation | String | Client/Guest Salutation | Mr., Mrs, Herr, Fru |
| SfId | String | Salesforce Client Id | 001ABC234DEF567GHI |
| ShId | String | Sihot Client/Guest Object Id | 123456789 |
| State | String | Province of Client/Guest | Tenerife, California, Yorkshire |
| Street | String | Street of Client/Guest | Main Street 45, Road 69, Hauptstrasse 12 |
| Surname | String | Lastname of Client/Guest | Smith, Johnson |
| Title | String | Client/Guest Title | Dr., Prof. |
| WorkPhone | String | Working phone number of Client/Guest | 004567891234 |


#### Available Reservation Fields

The table underneath is showing most of the fields that can be used to specify a reservation created within Sihot.
Additionally most of the [client fields](#available-client-fields) can be added for to specify the orderer of a
reservation.

The fields marked with an asterisk (*) after their field name in the table underneath are mandatory. Additionally
the reservation orderer has to be specified by at least one of the client fields `ShId`, `AcuId` or `Surname`.

The fields names marked with an plus character (+)
are optional only if the reservation gets sent the first time to Sihot, so for every change/update of an already 
existing reservation these fields need to be included in the send to Sihot:

Field Name | Field Type | Description | Example Values |
| --- | --- | --- | --- |
| ResAccount | String | Sihot Payment Instructions | '0'=Guest Account, '1'=Group Account, '3'=Client Account |
| ResAction | String | Reservation Booking Action | 'INSERT'=new booking, 'UPDATE'=modify booking, 'CANCEL'=cancel b. |
| ResAdults | Integer | Number of Adults | 1, 2, 4 |
| ResAllotmentNo | Integer | Sihot Allotment Number (optional) | e.g. 11 in BHC, 12 in PBC for Thomas Cook bookings | 
| ResArrival * | Date | Arrival Date | 28-02-2017 |
| ResAssId | Integer | Primary key of AssCache.res_groups table (auto-incrementing value) | 12345 |
| ResBoard | String | Sihot Meal-Plan/Board | 'RO'=room only, 'BB'=Breakfast, 'HB'=Half Board |
| ResBooked | Date | Sihot Reservation Booking Date | 24-12-2016 |
| ResCheckIn | Datetime | Room Check-/Move-In date and time | 01-02-2018 10:11:12 |
| ResCheckOut | Datetime | Room Check-/Move-Out date and time | 10-02-2018 09:10:11 |
| ResChildren | Integer | Number of Children | 0, 1, 2 |
| ResDeparture * | Date | Departure Date | 07-03-2017 |
| ResFlightETA | Datetime | ETA of flight | 11-12-2019 16:17:18 |
| ResFlightETD | Datetime | Departure of flight | 29-12-2019 14:45 |
| ResFlightArrComment | String | Arrival Flight Comment (flight number, ...) | 'ABC-2345 to Tenerife' |
| ResFlightDepComment | String | Departure Flight Comment (flight number, airport, ...) | 'TFS-1234 London' |
| ResGdsNo * | String | Sihot GDS number | <OTA-channel-prefix><Voucher number>, e.g. 'OTS-abc123456789' |
| ResGroupNo | String | Reservation Grouping Info | 345678, <123456> |
| ResHotelId * | String | Sihot Hotel Id | '1'=PBC, ... '4'=BHC, '999'=ANY |
| ResId + | String | Sihot Reservation Number | 123456789' |
| ResLongNote | String | Sihot Reservation Technical Comment (long) | 'extra info' (use '&#124;CR&#124;' for to separate various comments) |
| ResMktGroup | String | Sihot Reservation Channel | 'OW'=Owner |
| ResMktGroupNN | String | Reservation Marketing Group | 'RS'=Rental SP | 
| ResMktSegment * | String | Sihot Marketing Segment / OTA Channel | 'TO', 'PA', 'TC' |
| ResNote | String | Sihot Reservation Comment (short) | 'extra info' (use ';' for to separate various comments) |
| ResObjId | String | Sihot Internal Reservation Object Id | '123456789' |
| ResPersons | List | List of Occupants | ((Smith, John, 24-12-1962, ...), (Knopf, Jim, 27-01-1955, ...)) |
| ResPersons\<n\>AutoGen | String | Autogenerated entry | '1' if auto-generated else '0' |
| ResPersons\<n\>Board | String | Board-Rate | 'RO'=room only |
| ResPersons\<n\>FlightArrComment | String | Flight Arrival Comment | 'Flight-No, Airport' |
| ResPersons\<n\>FlightETA | Datetime | Flight estimated time of arrival | 11-12-2022 13:14 |
| ResPersons\<n\>FlightDepComment | String | Flight Departure Comment | 'Flight-no, Airport' |
| ResPersons\<n\>FlightETD | Datetime | Flight estimated time of departure | 18-12-2022 18:19 |
| ResPersons\<n\>PersAcuId | String | Sihot Occupant Matchcode | E123456 |
| ResPersons\<n\>PersAssId | Integer | Sihot Occupant AssCache clients primary key | 123456 |
| ResPersons\<n\>PersCountry | String | Country code (ISO2/3) | 'DE', 'ES', 'GB' |
| ResPersons\<n\>PersDOB | Date | Birthdate of n-th Occupant | 24-12-1962 |
| ResPersons\<n\>PersEmail | String | Email address of Occupant | 'name@host.xxx' |
| ResPersons\<n\>PersForename | String | Firstname of n-th occupant | John |
| ResPersons\<n\>PersLanguage | String | Language/Nationality code (ISO2/3) | 'DE', 'EN' |
| ResPersons\<n\>PersPhone | String | Phone number of occupant | '00234568899822' |
| ResPersons\<n\>PersShId | String | Sihot occupant Object Id | 1234567 |
| ResPersons\<n\>PersSurname | String | Lastname of n-th occupant | Smith |
| ResPersons\<n\>RoomNo | String | Room number of occupant | 'A234' |
| ResPersons\<n\>RoomPersSeq | String | Person sequence within room | '0' |
| ResPersons\<n\>RoomSeq | String | Room sequence number of occupant | '0' |
| ResPersons\<n\>TypeOfPerson | String | Age/Type of n-th occupant | '1A', '2B' |
| ResPriceCat | String | Paid Sihot Room Category (mostly same as `ResRoomCat`) | '1STS', '1JNP', '2BSS' |
| ResRateBoard | String | ID of the mealplan/board/package for ResRates | 'RO', 'BB', 'HB' |
| ResRates | List | List of daily price rates | (('120.60', '2019-12-24'), ('140.70', '2019-12-25'), ...) |
| ResRates\<n\>RateDay | Date | date of the price/rate segment | 24-12-2019 |
| ResRates\<n\>RateAmount | String | daily amount (including board) as float string | '120.50' |
| ResRateSegment | String | Sihot Price Rate/Segment (mostly same as `ResMktSegment`, but SIT for Siteminder) | 'XY', 'TK', 'TC' |
| ResRoomCat * | String | Requested Sihot Room Category | '1STS', '1JNP', '2BSS' |
| ResRoomNo | String | Sihot Room Number (optional) | '0426', 'A112' |
| ResSfId | String | Salesforce Reservation Opportunity Id | '006000000QACjZZYpLk' |
| ResSource | Char | Sihot Reservation Source | 'A'=Admin, 'S'=Sales, 'T'=Tour Operator |
| ResStatus | Char | Sihot Reservation Type | 'S'=cancelled, '1'=guaranteed |
| ResSubId + | String | Sihot Reservation Sub-number | '1' |
| ResVoucherNo | String | Sihot Voucher number / OTA channel booking reference | 'abc123456789' |

Please note that the first value of the ResPersons index value (represented by \<n\> in the above table) is 0 (zero) and
not 1.

All the field specifying the orderer of a reservation as well as the `ResPersons` fields are identical to the 
[client fields](#available-client-fields), the only difference is that the field names within `ResPersons` are
having the prefix `Pers`.

The soon deprecated Acumen system is additionally using extra reservation fields for to specify the occupants of a
guest reservation. `OccuAcuId` and `OccuShId` are specifying the first occupant and `OccuAcuId_P` and `OccuShId_P` the
second occupant (respectively the partner of the couple).


#### Available Reservation Inventory Fields

The table underneath is listing all the fields - alphabetically ordered by the field name - for to store the data of
each of each reservation inventory:

 Field Name | Field Type | Description | Example Values |
| --- | --- | --- | --- |
| RinUsageYear | Integer | Usage year | 2019 |
| RinType | String | Reservation Inventory Type | TO, RX |
| RinSwappedWith | String | Product Id of swapped Reservation Inventory | B234-52, 1024-44 |
| RinGrantedTo | String | Company to which Reservation Inventory got granted to | XL, SP |
| RinUsedPoints | String | Used Points for this Reservation Inventory | 23456, i56789 |
| RinUsageComment | String | User comment on the usage | Granted twice because last year her father passed away |   


#### Available Product Fields

The table underneath is listing all the fields - alphabetically ordered by the field name - for to store the data of
each of our products:

 Field Name | Field Type | Description | Example Values |
| --- | --- | --- | --- |
| ProId | String | Id of a certain product article | A123-45, 0345-52, KEYS-1234, ELPP-5678 |
| ProTypGroup | Char | Product type group code | O=owner, I=investor, K=keys |
| ProTypName | String | Product type name | BHH, PBC, KEYS, ELPP |


#### Field Mapping of our systems
 
The table underneath is showing the association between the Record Fields and the fields/columns/element names used
for them within our systems (Acumen, Salesforce, Sihot and AssCache):

| Field Name | Acumen Column | Salesforce Field | Sihot Element | AssCache Column |
| --- | --- | --- | --- | --- |
| AcuId | OC_CODE+CD_CODE | AcumenClientRef__pc | MATCHCODE+RESERVATION.MATCHCODE | rgr_order_cl_fk->cl_ac_id | 
| AssId | - | AssCache_Id__pc | - | cl_pk |
| City | CD_CITY | PersonMailingCity, City__pc | CITY | - |
| Comment | CD_NOTE | Client_Comments_pc | COMMENT | - |
| Country | SIHOT_COUNTRY | PersonMailingCountry, Country__pc | T-COUNTRY-CODE+COUNTRY+PERSON.COUNTRY-CODE | rgc_country |
| Currency | - | CurrencyIsoCode | T-STANDARD-CURRENCY | - |
| DOB | CD_DOB1 | DOB1__pc, KM_DOB__pc | D-BIRTHDAY, DOB | rgc_dob |
| Email | CD_EMAIL | PersonEmail | EMAIL-1+EMAIL+PERSON.EMAIL | cl_email+rgc_email |
| EmailB | - | - | EMAIL-2 | - |
| ExtRefs | T_CR | - | EXTID | external_refs |
| ExtRefs\<n\>Type | CR_TYPE+CD_RCI_REF+CD_SF_ID1 | - | EXTID.TYPE | er_type | 
| ExtRefs\<n\>Id | CR_REF | - | EXTID.ID | er_id |
| Fax | CD_FAX | Fax | FAX-1 | - |
| Forename | CD_FNAM1 | FirstName | NAME-2 | cl_firstname+rgc_firstname |
| GuestType | SIHOT_GUESTTYPE1+SIHOT_GUESTTYPE2 | - | T-GUEST | - |
| Language | SIHOT_LANG | Language__pc | T-LANGUAGE+LANG+PERSON.LANG | rgc_language |
| MobilePhone | CD_MOBILE1 | PersonMobilePhone | MOBIL-1, MOBIL | - |
| MobilePhoneB | - | - | MOBIL-2 | - |
| Nationality | SIHOT_LANG | Nationality__pc | T-NATION | - |
| OccuAcuId | CD_CODE | - | MATCHCODE | cl_ac_id | 
| OccuShId | CD_SIHOT_OBJID | - | OBJID+GUEST-ID | cl_sh_id |
| Password | CD_PASSWORD | - | INTERNET-PASSWORD | - |
| Phone | CD_HTEL1 | PersonHomePhone | PHONE-1+PHONE+PERSON.PHONE | cl_phone+rgc_phone |
| POBox | CD_ADD12 | - | PO-BOX | - |
| Postal | CD_POSTAL | PersonMailingPostalCode | ZIP | - |
| ProTypGroup | RS_SIHOT_GUEST_TYPE | - | - | pt_group |
| ProTypName | RS_NAME | - | - | pt_name |
| ProId | WK_CODE | - | - | pr_pk |
| RciId | CD_RCI_REF, CR_REF | RCI_Reference__pc | MATCH-ADM | - |
| ResAccount | SIHOT_PAYMENT_INST | - | RESERVATION.PAYMENT-INST | rgr_payment_inst |
| ResAction | RUL_ACTION | - | - | - |
| ResAdults | RU_ADULTS | Adults__c | RESERVATION.NOPAX+NO | rgr_adults |
| ResAllotmentNo | - | - | ALLOTMENT-EXT-NO(oc=RES)+ALLOTMENT-NO(oc=RES-SEARCH) | - | 
| ResArrival | ARR_DATE | Arrival__c | RESERVATION.ARR | rgr_arrival |
| ResBoard | RUL_SIHOT_PACK | - | PERSON.R | rgr_sh_pack |
| ResBooked | RH_EXT_BOOK_DATE | - | RESERVATION.SALES-DATE | rgr_ext_book_day |
| ResCheckIn | ARO_TIMEIN | CheckIn__c | ARR-TIME | rgr_time_in |
| ResCheckOut | ARO_TIMEOUT | CheckOut__c | DEP-TIME | rgr_time_out |
| ResChildren | RU_CHILDREN | Children__c | RESERVATION.NOCHILDS+NO | rgr_children |
| ResDeparture | DEP_DATE | Departure__c | RESERVATION.DEP | rgr_departure |
| ResFlightETA | RU_FLIGHT_LANDS | - | PICKUP-TIME-ARRIVAL | rgc_flight_arr_time |
| ResFlightETD | - | - | PICKUP-TIME-DEPARTURE | rgc_flight_dep_time |
| ResFlightArrComment | SH_EXT_REF | - | EXT-REFERENCE+PICKUP-COMMENT-ARRIVAL | rgc_flight_arr_comment |
| ResFlightDepComment | - | - | PICKUP-COMMENT-DEPARTURE | rgc_flight_dep_comment |
| ResGdsNo | SIHOT_GDSNO | GdsNo__c | GDSNO | rgr_gds_no |
| ResGroupNo | SIHOT_LINK_GROUP | - | EXT-KEY | rgr_group_no |
| ResHotelId | RUL_SIHOT_HOTEL | HotelId__c | ID, HN, RES-HOTEL | rgr_ho_fk |
| ResId | - | Number__c | RES-NR | rgr_res_id |
| ResLongNote | SIHOT_TEC_NOTE | - | RESERVATION.TEC-COMMENT | rgr_long_comment |
| ResMktGroup | RO_SIHOT_RES_GROUP | MktGroup__c | RESERVATION.CHANNEL | rgr_mkt_group |
| ResMktGroupNN | RO_SIHOT_SP_GROUP | - | NN | - |
| ResMktSegment | SIHOT_MKT_SEG | MktSegment__c (Marketing_Source__pc) | RESERVATION.MARKETCODE(oc=SS/RES-SEARCH)+MARKETCODE-NO(oc=RES) | rgr_mkt_segment |
| ResNote | SIHOT_NOTE | Note__c | RESERVATION.COMMENT | rgr_comment |
| ResObjId | RU_SIHOT_OBJID+RU_CODE+RUL_PRIMARY | SihotResvObjectId__c | RESERVATION.OBJID | rgr_obj_id |
| ResPersons | - | - | PERSON | res_group_clients.* |
| ResPersons\<n\>AutoGen | - | - | PERSON.AUTO-GENERATED | rgc_auto_generated |
| ResPersons\<n\>Board | - | - | PERSON.PERS-RATE.R | rgc_sh_pack |
| ResPersons\<n\>FlightArrComment | SH_EXT_REF | - | PERSON.PICKUP-COMMENT-ARRIVAL | rgc_flight_arr_comment |
| ResPersons\<n\>FlightETA | RU_FLIGHT_LANDS | - | PERSON.PICKUP-TIME-ARRIVAL | rgc_flight_arr_time |
| ResPersons\<n\>FlightDepComment | - | - | PERSON.PICKUP-COMMENT-DEPARTURE | rgc_flight_dep_comment |
| ResPersons\<n\>FlightETD | - | - | PERSON.PICKUP-TIME-DEPARTURE | rgc_flight_dep_time |
| ResPersons\<n\>PersAcuId | CD_CODE | - | PERSON.MATCHCODE | rgc_occup_cl_fk->cl_ac_id |
| ResPersons\<n\>PersAssId | CD_CODE | - | PERSON.MATCHCODE | rgc_occup_cl_fk |
| ResPersons\<n\>PersCountry | - | - | PERSON.COUNTRY-CODE | rgc_country |
| ResPersons\<n\>PersDOB | CD_DOB1+CD_DOB2 | - | PERSON.DOB | rgc_dob |
| ResPersons\<n\>PersEmail | - | - | PERSON.EMAIL | rgc_email |
| ResPersons\<n\>PersForename | CD_FNAM1, CD_FNAM2 | - | PERSON.NAME2 | rgc_firstname |
| ResPersons\<n\>PersLanguage | - | - | PERSON.LANG | rgc_language |
| ResPersons\<n\>PersPhone | - | - | PERSON.PHONE | rgc_phone |
| ResPersons\<n\>PersShId | CD_SIHOT_OBJID | - | PERSON.GUEST-ID | rgc_occup_cl_fk->cl_sh_id |
| ResPersons\<n\>PersSurname | CD_SNAM1, CD_SNAM2 | - | PERSON.NAME | rgc_surname |
| ResPersons\<n\>RoomNo | RUL_SIHOT_CAT | RoomCat__c | PERSON.RN | rgc_room_id |
| ResPersons\<n\>RoomPersSeq | - | - | PERSON.ROOM-PERS-SEQ | rgc_pers_seq |
| ResPersons\<n\>RoomSeq | - | - | PERSON.ROOM-SEQ | rgc_room_seq |
| ResPersons\<n\>TypeOfPerson | - | - | PERSON.PERS-TYPE | rgc_pers_type |
| ResPriceCat | SH_PRICE_CAT | - | PCAT | - |
| ResRateBoard | - | - | - |
| ResRateSegment | RUL_SIHOT_RATE | - | RESERVATION.RATE-SEGMENT | rgr_room_rate |
| ResRates\<n\>RateAcount | - |- | - |
| ResRates\<n\>RateDay | - |- | - |
| ResRoomCat | RUL_SIHOT_CAT | RoomCat__c | RESERVATION.CAT | rgr_room_cat_id |
| ResRoomNo | RUL_SIHOT_ROOM | RoomNo__c | PERSON.RN | rgc_room_id+rgr_room_id |
| ResSfId | MS_SF_DL_ID | ReservationOpportunityId+Opportunity.Id | NN2(?) | rgr_sf_id |
| ResSource | RU_SOURCE | - | SOURCE | rgr_source |
| ResStatus | SH_RES_TYPE | Status__c | RESERVATION.RT | rgr_status |
| ResSubId | - | SubNumber__c | SUB-NR | rgr_sub_id |
| ResVoucherNo | RH_EXT_BOOK_REF | - | RESERVATION.VOUCHERNUMBER | rgr_ext_book_id |
| RinUsageYear | AOWN_YEAR | - | - | ri_usage_year |
| RinType | AOWN_ROREF | - | - | ri_inv_type |
| RinSwappedWith | AOWN_SWAPPED_WITH | - | - | ri_swapped_product_id |
| RinGrantedTo | AOWN_GRANTED_TO | - | - | ri_granted_to |
| RinUsedPoints | - | - | - | ri_used_points |
| RinUsageComment | - | - | -  | ri_usage_comment |   
| Salutation | F_SIHOT_SALUTATION() | Salutation | T-SALUTATION | - |
| SfId | CD_SF_ID1/2, MS_SF_ID | id+PersonAccountId | MATCH-SM | cl_sf_id |
| ShId | OC_SIHOT_OBJID+CD_SIHOT_OBJID | SihotGuestObjId__pc | OBJID+GUEST-ID | rgr_order_cl_fk->cl_sh_id |
| State | (CD_ADD13) | PersonMailingState | T-STATE | - |
| Street | CD_ADD11 | PersonMailingStreet | STREET | - |
| Surname | CD_SNAM1 | LastName | NAME-1 | cl_surname+rgc_surname |
| Title | CD_TITL1 | PersonTitle | T-TITLE | - |
| WorkPhone | CD_WTEL1+CD_WEXT1 | Work_Phone__pc | PHONE-2 | - |


### AcuSihotMonitor Application

AcuSihotMonitor is a kivy application for Windows, Linux, Mac OS X, Android and iOS and allows to check
the correct functionality of the Salesforce, Acumen and Sihot servers and interfaces.


### SysDataMan Application

SysDataMan is a command line tool for to synchronize and compare data between our four systems (Acu=Acumen Ass=AssCache
Sf=Salesforce and Sh=Sihot). The actions performed by this tool get specified by the 
[command line options --pull, --push and --compare](#action-command-line-options),
which can be specify multiple times.

All command line options can be specified in any order, because SysDataMan is always first doing all the pull actions.
After the pull any push actions are performed (if specified/given) and finally the compare actions are processed.

For to run a compare before any additional pull/push action simply execute SysDataMan twice (the first run
with the --compare option and the second run with the pull/push and optionally another compare action).
 
The postgres database AssCache (Ass) can be used for to temporarily store the data pulled from one of our three
systems (the source system) for to speed up large data synchronization tasks.

#### Supported Data Fields

The following client data fields can be used for to optionally specify the fields that are used within the 
`field_names` key-word-arguments of the action command line options `pull`, `push` and `compare`, although not all of
them are implemented for all our three systems (e.g. Sihot only supports the ShId field for filtering and matching):

| Field Name | Description |
| --- | --- |
| AssId | AssCache client primary key |
| AcuId | Acumen client reference |
| SfId | Salesforce client (lead/contact/account) id |  
| ShId | Sihot guest object id |
| Name | Client forename and surname (separated by one space character) |
| Email | Client main email address |
| Phone | Client main phone number |

#### Action Command Line Options

Each run of the SysDataMan tool has to specify at least one (mostly more than one) valid action (which are given with
the --pull, --push and/or the --compare command line option). The option value of these actions consists of a system
identifier (two or three characters long) followed by a record/data type identifier (one character).

The supported system identifiers are:

| System Identifier | Description |
| --- | --- |
| Acu | Acumen |
| Ass | AssCache |
| Sh | Sihot |
| Sf | Salesforce |

The supported record/data type identifiers are:

| Record Type Identifier | Description |
| --- | --- |
| C | Clients |
| P | Products |
| R | Reservations |

So for to compare/compare all client record data (C) from the Acumen (Acu) against Salesforce (Sf) system, use the
following action command line options:

    `--pull=AcuC --compare=SfC`

This will first pull client data from Acumen and then compare it to the same clients within Salesforce. A similar
compare run could be done with:

    `--pull=SfC --compare=AcuC`

The difference is that the first compare run will pull (and optionally filter) the clients from the (source) system
Acumen and then compare the found clients against the (destination) system Salesforce. In contrary the second example
will first pull all the clients from Salesforce (source) and then compare the found clients with associated clients from
the Acumen (destination) system. 

A combination of the --pull and --push command line options allows to synchronize data between several systems.
For example for to synchronize client data from Acumen to Sihot and Salesforce you have to specify the following action
command line arguments:

    `--pull=AcuC --push=SfC --push=ShC`

Multiple options of the same action will be processed in the given order, but only within the same action type. So first
all pull actions (in the given order), then all push actions and finally all compare actions. So on multiple push
actions a field will have the value from the system which last pull action included this field.

#### Additional Action Command Line Options

In most cases you want to restrict the synchronized/compared data from the source system to a small amount of 
data-records and/or -fields and for to prevent heavy data and system loads.

Filters and other input parameters can be specified as action arguments directly after the system and record type of
each Action command line option as a python dictionary literal. The key is identifying the argument type, e.g. 
sql clauses or a list of matching field names. The following action argument dictionary keys are available:

* col_names
* chk_values
* where_group_order
* bind_values
* filter_records
* field_names
* exclude_fields
* match_fields

The `filter_records` key-word-argument specifies a callable that can filter/reduce the amount of data. E.g. in case of
pulling client data (using the --pull option) this callable can be used instead of the `where_group_order` SQL for
to filter/restrict data from a system.

The following command line option - using `where_group_order` - will pull only
Acumen client data with a non-empty email address and compare them against Salesforce:

    `--pull="AcuC{'where_group_order':\"CD_EMAIL is not NULL\"} --compare=SfC`

The same can be achieved by using `filter_records` with:

    `--pull="AcuC{'filter_records': lambda r: not r.val('Email')}" --compare=SfC`

Additionally you can restrict the processed (synchronized/compared) fields with the key-word-arguments `col_names`, 
`field_names` and/or `exclude_fields`. If none of these are specified then SysDataMan is processing all 
[data fields](#supported-data-fields) supported by the system you are working with. So for to restrict the last 
example to only compare the client's email address and phone number you have to specify the following 
command line options:

    `--pull="AcuC{'field_names': ['Email','Phone']}" --compare=SfC`

The same action is done by specifying the system column names of the email and phone fields with the `col_names`
action argument:

    `--pull="AcuC{'col_names': ['CD_EMAIL','CD_HTEL1']}" --compare=SfC`

In contrary the `exclude_fields` action argument is excluding fields from the action, so all the field names
in this list will not be used for this action. E.g. the following command is pulling all fields apart from the
email address:

    `--pull="AcuC{'exclude_fields': ['Email']}" --compare=SfC`

Please note that there is currently no action argument available to exclude fields using the system field names.

#### Additional Matching Action Command Line Options

The `match_fields` and `filter_records` key-word-arguments are also restricting the fields and records of the
destination system (the system pushed-to or compared-against).

The primary key of each system is used by default for to lookup/associate the matching data record in the destination
system. But in the case where you the primary key value is not available in both systems you can a specify with the 
command line option `match_fields` a different field (or a list of fields) for this lookup/association.
So e.g. for to compare the client data between Acumen and Salesforce by using the Email and Phone data for to match 
the client record within Salesforce the following command line options have to be specified:

    `--pull=AcuC --compare=SfC{'match_fields':['Email','Phone']}`

The `filter_records` argument allows to restrict the processed/synchronized/compared data records on the
destination system. The following example is comparing the source client data from Sihot against the (destination)
client data within Acumen, restricted to Acumen client data where the email address and the phone number are not
empty:  

    `--pull=ShC --compare="AcuC{'filter_records':lambda r: not r.val('Email') or not r.val('Phone')"`


### BssServer Application

The BssServer is a server application that is providing a web-service that is listening/waiting for our Sihot system
to connect (as a client) for to propagate/push the following live actions done within Sihot:

* Change of Reservation Data
* Room Check-Ins
* Room Check-Outs
* Room Moves

Any of these Sihot actions will be cashed within the AssCache/Postgres database and later (after the reservations got
fully implemented within Salesforce) also be propagated onto our Salesforce system. We could pass these
notifications directly into the SF system (by-passing AssCache) if SF would be able to act as a server for
web services, but most likely we need to implement a bridge like BssServer here because the Sihot live/push interfaces 
are not compatible to any web-service standards (SOAP/WSDL/REST/XML/…).


### ClientQuestionnaireExport Application

ClientQuestionnaireExport is a command line tool that exports all check-outs within a given date range into a CSV file
for to be sent to a service company for to do the client questionnaires. FYI: this tools is replacing the currently
used Oracle procedure SALES.TRIPADVISOR (runs every Tuesday around 11 am). There is a similar export available
within the Sihot.PMS EXE application via the menu entry `Export / Export stays for Marketing` (with the checkbox
`Email filter` checked) which is exporting a CSV file into the folder U:/transfer/staysformarketing/.

#### HotelNames INI/config section

This section are defining the hotel names that will be included into the CSV file. The variable name is the Sihot
hotel id. Only the check-outs of hotels that have a hotel name defined will be exported/included in the CSV file.

Currently only the PBC and BHC hotels are processed.

#### HotelLocationIds INI/config section

This section are defining the location ids used by the client questionnaire service for to be included into the
CSV file. The variable name is the Sihot hotel id. Only the check-outs of hotels that have a location id 
defined will be exported/included in the CSV file.

The location IDs provided are 535055 for the BHC hotel and 288275 for the PBC hotel.

#### columnSeparator INI/config setting

Allows to specify the character used for to separate the columns of the CSV file. The default value is the comma (`,`).

#### maxLengthOfStay INI/config setting

Because the Sihot WEB interface is only allowing to search for arrival dates a maximum length of a stay can be
specified for to include them into the exported CSV file. The default value is 42 days.

#### resSearchFlags INI/config setting

Allows to specify the flags provided by the Sihot WEB interface `RES-SEARCH` command. The default value is `ALL-HOTELS`.

#### resSearchScope INI/config setting

Allows to specify the scope flags provided by the Sihot WEB interface `RES-SEARCH` command. The default value is 
`NOORDERER;NORATES;NOPERSTYPES`.

#### fileCaption INI/config setting

Allows to specify/change the header/caption of the exported CSV file. The default value is 
`UNIQUEID,CHECKIN,CHECKOUT,FIRSTNAME,LASTNAME,EMAIL,CITY,COUNTRY,RESORT,LOCATIONID,STAYMONTH,STAYYEAR,LANGUAGE`.

#### fileColumns INI/config setting

Allows to specify/change the content of the data row columns exported CSV file. The default value is
`['<unique_id>', 'ARR', 'DEP',
  LIST_MARKER_PREFIX + 'NAME2', LIST_MARKER_PREFIX + 'NAME',
  LIST_MARKER_PREFIX + 'EMAIL', LIST_MARKER_PREFIX + 'CITY',
  LIST_MARKER_PREFIX + 'COUNTRY', '<hotel_id_to_name(hotel_id)>',
  '<hotel_id_to_location_id(hotel_id)>',  # '<"xx-0000-xx">',
  '<check_out.month>', '<check_out.year>',
  'LANG',
  ]`.


### SihotOccLogChecker Application

This command line tool is helping to check and optionally fix any missing occupation data changes (like Room-Checkin,
-Checkout or -Move) within the Acumen system.

The tool is parsing each Check-In (CI), Check-Out (CO) and Room.Move (RM) in the Sihot SXML interface log file for to
compare it with the Acumen data. There will be lots of discrepancies shown for reservations that are imported
into Sihot via Siteminder or created manually (because they not existing in Acumen). Therefore on the first run you only
need to the check the summary at the end of the console output (as well as at the end of the log file, created mostly
in the log sub-folder). 

The summary consists e.g. of the number of fixable reservations - if this value is zero than everything is ok, because
there is nothing that this tool could repair for you. A few line above you should double check if there any gaps between
the specified date range and the log entry timestamps within the specified log file.

Occupation data changes done in Sihot get normally transferred via the Sihot SXML interface first to the AcuServer 
and from there to the Acumen system. So if either the SXML interface
or the AcuServer is not running correctly (like happened recently between 16/10/2017 14:07:32 and 18/10/2017 15:09:53),
then you can use SihotOccLogChecker for to check and repair the related T_ARO data in Acumen.

So for to check the discrepancies for the above date range you have to provide the exact date range with the
command line options `dateFrom` and `dateTill` to SihotOccLogChecker, like shown underneath:

`--dateFrom="2017-10-16 14:07:33.0" -dateTill="2017-10-18 15:09:52.0"`

The default value for `dateFrom` is yesterday at the same time and for `dateTill` it is the current time.

Additionally you have to specify the Acumen server with the `acuDSN` command line option, the Acumen user name and
password with the `acuUser` and `acuPassword` command line options and finally the path and filename of the Sihot
SXML log file as command line parameter (e.g. `E:\sihot\log\SP\SXML_ACUMEN@SP.log` directly from our Sihot production
 server or `\\<sihot-server>\e$\sihot\log\sp\SXML_ACUMEN@SP.log` from the network).

After checking the discrepancies you can add the `correctSystem` command line option for to fix either the Acumen (Acu)
or the AssCache (Ass) occupation status. If you want for example to fix the missing occupation changes in our second big
outage (between 21/10/2017 17:54:38 and 23/10/2017 10:20:50) in Acumen you have to specify the following command
line arguments: 

`-F="2017-10-21 17:54:38.0" -T="2017-10-23 10:20:50.0" -A=Acu -u=AECKER -p=password -d=SP.WORLD`

In the last example the short options got used (see the Short Option column in the section
[Command line arguments](#command-line-arguments) above). For a more verbose output you can also
pass the `debugLevel` command line option (or as short option -D) with a value of 2 (for verbose) or 3 (verbose and
with timestamp).

#### maxDaysDiff INI/config setting

Allows to specify the maximum number of days of difference between the expected and the real check-in/-out day. The
default value is 2 days. FYI: the Oracle procedure P_SIHOT_ALLOC() that is used by AcuServer to pass occupation
changes to Acumen is using 4 days of difference (see constant SihotRoomChangeMaxDaysDiff declared in the K package).

#### daysCheckInBefore INI/config setting

This config variable allows this tool to search also for Acumen reservations that got checked-in the given number
of days before the expected arrival date.
 
Please note that the value of this setting is restricted by the value of the maxDaysDiff INI/config setting (see above).

#### daysCheckOutAfter INI/config setting

This config variable allows this tool to search also for Acumen reservations that got checked-out the given number
of days after the expected departure date.

Please note that the value of this setting is restricted by the value of the maxDaysDiff INI/config setting (see above).


### SihotResImport Application

Combined Console/Kivy Application for to import reservation bookings, changes and cancellations from CSV or JSON files
into the Sihot system.

Apart from the instruction in the [Installation Instructions](#installation-instructions) section (see
above) you also have to create an import path folder for each supported import channel (e.g. C:\JSON_Import). The same
path name has to be specified as command line argument when you start the SihotResImport application (see next 
paragraph). Please note that the user need to have full access (read, write and create folder privileges) within each 
of these import channel folders. 

The provided command line options are documented above in the section
[Command line arguments](#command-line-arguments). The most important one is the `jsonPath` option, 
for to specify the import path and file mask for OTA JSON files - this value defaults to `C:/JSON_Import/*.json`.

For to run this application in console mode (headless without any user interface), simply specify a valid 
Acumen user name (acuUser) and password (acuPassword) as command line parameters (or via one of supported config/INI 
files).

There are four command line parameters specifying the used Sihot server (production or test): `shServerIP` is the DNS 
name or IP address of the SIHOT interface server, `shServerPort` is the IP port of the used WEB interface and optionally
you can specify via `shTimeout` the timeout value in seconds for TCP/IP connections (default=69.3) and 
via `shXmlEncoding` the charset encoding used for the xml data (default='cp1252').

Meanwhile and for to check the client data against our Salesforce system this application needs also a user account for
the Salesforce system. If you start this application using E:\AcuServer\ of the Sihot production system as the current
working directory then you don't need to specify anything to use the Salesforce sandbox, but for production you need at
least to specify the user name (sfUser), the security token (sfToken), the sandbox flag set to False (sfIsSandbox=False)
and the password (the password can be omitted if you use our SihotInterface user account).

Another four command line parameters are for to configure the notification emails: `smtpServerUri` specifies the 
SMTP server URI (including user name, password, host and port). The sender address has to be specified by
`smtpFrom`, the list of SMTP receivers by `smtpTo` (for the protocol) and `warningsMailToAddr` (for the
warnings/discrepancy notifications.

By passing the numeric value 1 to the optional command line argument `breakOnError` you could abort the importation
if an error occurs in one of the JSON files.

#### JSON field names

Reservation details of each booking coming via email from OTA channels and are not supported/included by Siteminder
can be imported from a json file (the tool to convert each email into the json format is written in C#.NET by Nitesh).
The available json field names are documented in the 
section [Available Reservation Fields](#available-reservation-fields) above. 


### SihotServer Web Services

SihotServer is providing several https web services, which are implemented and distributed as pure python package
scripts. These python scripts are prepared to by used on top of a Apache Linux web server as a WSGI web service
extension. For to access one of these services you first have to enter the correct user name and password
(see .console_app_env.cfg).

#### Setup Web Server

After setting up mod_wsgi using embedded mode (instead of daemon mode) the apache/linux server settings are used.

For to change the encoding charsets in embedded mode you could change the environment variables
LANG and LC_ALL of apache in /etc/apache2/envvars. Following the recommendations of the main developer of mod_wsgi
(see http://blog.dscpl.com.au/2014/09/setting-lang-and-lcall-when-using.html) it would be better and saver
to run mod_wsgi in daemon mode and specify there the language and locale settings by adding to the apache .conf file:

    WSGIDaemonProcess my-site lang='en_US.UTF-8' locale='en_US.UTF-8'

More useful hints and workarounds for common mod_wsgi issues and configuration problems you find here:
    https://code.google.com/archive/p/modwsgi/wikis/ApplicationIssues.wiki
Newer version:
    https://modwsgi.readthedocs.io/en/develop/user-guides/application-issues.html

#### Deployment 

The deployment shell scripts `build_ws_res.cmd` and `build_ws_test.cmd` are used to prepare the roll-out of the
web services. The first one available at https://services.signallia.com are the web services for to access our
production servers and the second one is for to check the web services environment (available at 
https://lint.signallia.com).

For to run one of the deployment shell scripts, you first have to change the current working directory to the
source folder. The shell script is copying all the needed python code from the actual source folder and the
python path to the distribution folder on the same machine.

After that you need to use a SFTP tool - like WinSCP.exe for to pass/synchronize the files in the distribution
folder to the web server directories (lint and services underneath /var/www).

#### Insert, Upsert or Delete Reservation

A POST web-service that allows you to INSERT, UPSERT or DELETE reservations within Sihot is available under the URL:

https://services.signallia.com/res/\<action\>.

Depending on the action you want to perform you have to replace the \<action\> part of the URL with either 'insert', 
'upsert' or 'delete'. The fields for to identify and specify the reservations are given in JSON format within
the body of the web-service request.

For to identify a reservation the Sihot XML interface needs at leat the following 9 additionally fields:
ResHotelId, ResGdsNo, ResArrival, ResDeparture, ResAdults, ResChildren, ResRoomCat, ResMktSegment and AcuId. Instead
of the field AcuId you could also use either the fields ShId or Surname for to identify the orderer of the reservation.

For to specify the reservation data use the fields listed in this [section](#available-reservation-fields) and for
to specify extra data of the orderer the fields in this [section](#available-client-fields) can be added.  

#### Retrieve Reservation Data

Another GET web service provides the retrieval of the full data structure of a Sihot reservation:

https://services.signallia.com/res/get?hotel_id=2&gds_no=1098576

The `hotel_id` and `gds_no` query parameters of this web service are mandatory. Instead of passing the GDS number
within `gds_no` you could alternatively also use the reservation number by passing the query parameters `res_id`
and `sub_id` instead of the `gds_no` query parameter.
 
#### Count Existing Reservations

Another GET web-service allows you to get the number of confirmed Sihot reservations:

https://services.signallia.com/res/count?hotel_ids=2&day=2019-10-10&room_cat_prefix=1&res_max_days=21

All query parameters are optional for this web service. If the `hotel_ids` query parameter get not passed then
the service will count the reservations in all our Sihot hotels; The `hotel_ids` parameter does also support
a list of Sihot hotel ids separated by a comma character. The `room_cat_prefix` query parameter does also allow
to specify the full name of a Sihot room category, like e.g. `1JNR`. Please note that the `res_max_days`
query parameter should be greater or equal to the number of days of the counted reservations – the default
value is 27 days).

#### Retrieve Available Units

Another GET web service allows to fetch the currently available units/rooms/apartments of the Sihot system, providing
the query parameters `hotel_ids`, `room_cat_prefix` and `day`. For example the following URL is retrieving from
Sihot all the available 1-Bedroom units within the hotel 2 (BHH) for the 10th of October 2019:

https://services.signallia.com/avail_rooms?hotel_ids=2&room_cat_prefix=1&day=2019-10-10

Additionally web services that are useful for debugging purposes are described in the section [Debugging](#debugging)
underneath.
 
#### Debugging

For debugging you can check the log files in the log folder of the service folder (e.g. for the `services`
web service within `/var/www/services/log`).

Service specific log files created by the Apache server you find on the web server folder `/var/log/apache2`. The log
file names are starting with the name of the service (`lint` or `services`), followed by an underscore character and
the suffixes `error` and `access`. The file extension of these log files is `.log`.

Additional log files you find in the web server folder `/var/log`, e.g. the Apache log files `syslog` and `auth.log`.

There are also some extra web services available for debugging. A simple hello echo service can be reached by the
URL - it will return the string you provided after the hello path ('debug_text' in the following example):

https://services.signallia.com/hello/debug_text

Another debug web service allows you to fetch any file from the web server that is placed in the `static` sub-folder
of the services folder (for example from /var/www/services/static).

Finally under the URL https://lint.signallia.com there is also a small web service available for debugging
purposes that is displaying all the system environment variable of the web server (used by all our python
web services).


### WatchPupPy Application

WatchPupPy is a watchdog tool for to either supervise a always running server or for to execute another application
periodically.

The command line for the re-start a server or application to supervise has to be specified with `cmdLine` option.
For always running servers the `cmdInterval` option has to be specified with the value 0 (zero) - else the specified
value is the period in seconds between two executions of the application/command-line.
  
When you are using WatchPupPy for always running servers (specifying 0 value for the cmdInterval option)
then ensure that you disable Windows Error Reporting to prevent the freeze by the message box showing
"<APP.EXE> has stopped working" and offering "Check online for a solution and close program":
- https://www.raymond.cc/blog/disable-program-has-stopped-working-error-dialog-in-windows-server-2008/
- https://monitormyweb.com/guides/how-to-disable-stopped-working-message-in-windows



## System Configurations And Mappings

Most of the configuration keys/options and mapping tables are stored within the Lookup Tables (`T_LU`) of the Oracle
database of the Acumen server. Others are stored in newly added columns within other Acumen configuration tables.
Some are hard coded within the Acumen Oracle views (e.g. V_ACU_RES_DATA). Default values for the command line arguments
can be specified within different Configuration files (with the file extensions INI or CFG).

### Hotel IDs

The `SIHOT_HOTELS` lookup class is mapping the Acumen hotel IDs (3 characters stored in the column `LU_ID`) onto the
numeric Sihot Hotel Ids (stored in `LU_NUMBER`). Additionally this lookup class is used for to configure the currently
active hotels in the Sihot system (initially only ANY/999, BHC/1 and PBC/4):

| Acumen Hotel Code | Resort Name | Currently Active (Y=yes, n=no) | Sihot Hotel Id |
| :---: | :--- | :---:  | :---: |
| ANY | Pseudo hotel for unspecified resort bookings in Tenerife | Y | 999 |
| ARF | Angler's Reef | n | 101 |
| BHC | Beverly Hills Club  / The Suites At Beverly Hills | Y | 1 |
| BHH | Beverly Hills Heights | Y | 2 |
| DBD | Dorrabay | n | 102 |
| GSA | Golden Sands | n | 103 |
| HMC | Hollywood Mirage Club | Y | 3 |
| KGR | Kentisbury Grange | n | 104 |
| LVI | Luna Villas | n | 105 |
| PBC | Palm Beach Club | Y | 4 |
| PLA | Platinum Sports Cruisers | n | 106 |
| PMA | Paramount | Y | 107 |
| PMY | The Palmyra | n | 108 |
| PSF | Podere San Filippo | n | 109 |
| RHF | Rhinefield Apartments | n | 110 |
| CPS | CP Suites in BHC | n | 199 |


### Room Categories

The Acumen reservation requests are mainly classified by the room size and requested apartment features, whereas the
Sihot.PMS room categories are need to be setup for to include room size and features.

There are several lookup classes with the lookup class name prefix `SIHOT_CATS_` within the Acumen/Oracle lookup table
(or alternatively meanwhile also in the `ResortCats` section of the *.CFG/*.INI configuration files of this suite)
for to map/transform the Acumen unit sizes and optionally also requested apartment features into Sihot room categories.
These mappings can be setup for each hotel individually and the pseudo hotel ANY can be used as fallback for all real
hotels. Therefore the ANY hotel need to specify at least one mapping/transformation for all available Acumen room/unit
sizes: HOTEL/STUDIO/1...4 BED.

| Room Size | Requested Apartment Feature | Sihot room category |
| :---: | --- | :---: |
| HOTEL | - | HOTU |
| STUDIO | - | STDO |
| 1 BED | - | 1JNR |
| 2 BED | - | 2BSU |
| 2 BED | High Floor/757 | 2BSH |
| 3 BED | - | 3BPS |


#### BHC room category overloads

The `SIHOT_CATS_BHC` lookup class is specifying the following room size/feature mappings to the Sihot room categories in
hotel 1:

| Room Size | Requested Apartment Feature | Sihot room category |
| :---: | --- | :---: |
| HOTEL | - | HOTU |
| STUDIO | High Floor/757 | STDS |
| 1 BED | Duplex/752 | 1DSS |
| 1 BED | High Floor/757 | 1JNS |
| 2 BED | - or Duplex/752 | 2DPU |
| 2 BED | High Floor/757 | 2BSH |


#### BHH room category overloads

The `SIHOT_CATS_BHH` lookup class is specifying the following room size/feature mappings to the Sihot room categories in
hotel 2:

| Room Size | Requested Apartment Feature | Sihot room category |
| :---: | --- | :---: |
| 1 BED | - | 1JNP |
| 1 BED | Duplex/752 | 1DDP
| 1 BED | High Floor/757 |  1DDS |
| 1 BED | Sea View/Front/781 |  1JNS|
| 2 BED | - | 2BSP |
| 2 BED | Sterling/748 | 2BSS |
| 2 BED | Duplex/752 | 2DDP |
| 2 BED | High Floor/757 | 2DDP |
| 2 BED | Sea View/Front/781 | 2DDS |
| 3 BED | Duplex/752 | 3BPS |
| 3 BED | High Floor/757 | 3BPS |


#### HMC room category overloads

The `SIHOT_CATS_HMC` lookup class is specifying the following room size/feature mappings to the Sihot room categories in
hotel 3:

| Room Size | Requested Apartment Feature | Sihot room category |
| :---: | --- | :---: |
| STUDIO | High Floor/757 | STDS |
| STUDIO | Sea View/Front/781 | STDS |
| 1 BED | - | 1JNP
| 1 BED | Duplex/752 | 1DDS |
| 1 BED | High Floor/757 | 1JNS |
| 1 BED | Sea View/Front/781 | 1DDS |
| 2 BED | - | 2BSP |
| 2 BED | Sterling/748 | 2BSS |
| 2 BED | Duplex/752 | 2DDO |
| 2 BED | High Floor/757 | 2BSS |
| 2 BED | Sea View/Front/781 | 2DDS |
| 3 BED | - | 3DDS |
| 3 BED | Duplex/752 | 3DDS |
| 3 BED | High Floor/757 | 3DDS |
| 3 BED | Sea View/Front/781 | 3DDS |
| 4 BED | - | 4BPS |
| 4 BED | Duplex/752 | 4BPS |
| 4 BED | High Floor/757 | 4BPS |


#### PBC room category overloads

The `SIHOT_CATS_PBC` lookup class is specifying the following room size/feature mappings to the Sihot room categories in
hotel 4:

| Room Size | Requested Apartment Feature | Sihot room category |
| :---: | --- | :---: |
| STUDIO | - | STDP |
| STUDIO | High Floor/757 | STDH |
| STUDIO | Sea View/Front/781 | STDB |
| 1 BED | - | 1JNP |
| 1 BED | Sterling/748 | 1STS |
| 1 BED | High Floor/757 | 1JNH |
| 1 BED | Sea View/Front/781 | 1JNB |
| 2 BED | - | 2BSP |
| 2 BED | High Floor/757 | 2BSH |
| 2 BED | Sea View/Front/781 | 22SB |
| 3 BED | - | 3BPB |
| 3 BED | High Floor/757 | 3BPB |
| 3 BED | Sea View/Front/781 | 3BPB |


#### PMA room category overloads

| Room Size | Requested Apartment Feature | Sihot room category |
| :---: | --- | :---: |
| 1 BED | - | 1JNR |
| 2 BED | - | 2BSU |
| 3 BED | - | 3BPS |
| 4 BED | - | 4BPS |


#### Room specific overloads

The two new `T_AP` columns `AP_SIHOT_CAT` and `AP_SIHOT_HOTEL` can be used for the individual mapping of each apartment
onto a specific Sihot.PMS Hotel Id and Room Price Category (room size and paid supplements).

Specially the Hotel Id mapping will be needed for the 16 BHC sweets that are planned to be migrated to new Club Paradiso
pseudo resort.



### Language / Nationality

The mapping of the language and nationalities is done by storing the Sihot language IDs in the Acumen `T_LG` table
(`LG_SIHOT_LANG VARCHAR2(2 BYTE)`).

| Sihot Id | Acumen Code |
| --- | --- |
| HR | CRO |
| EN | ENG |
| FR | FRE |
| DE | GER |
| IT | ITA |
| PL | POL |
| PT | POR |
| ES | SPA |
| SI | SVN |


### Booking Types Market Segmentation

The Acumen Reservation Booking Types (ResOcc types) are mapped onto the Sihot Market Segments with the help of 6 new
`T_RO` columns.

| column name | column content |
| --- | --- |
| RO_SIHOT_MKT_SEG | SIHOT market segment mapping (lower case not working in SIHOT) |
| RO_SIHOT_RES_GROUP | SIHOT market CHANNEL mapping |
| RO_SIHOT_SP_GROUP | SIHOT market NN mapping |
| RO_SIHOT_AGENCY_OBJID | SIHOT company object ID for agency bookings |
| RO_SIHOT_AGENCY_MC | SIHOT company matchcode for agency bookings |
| RO_SIHOT_RATE | SIHOT Rate for this Market segment and filter flag for every synchronized booking type |


#### Remapped market segment codes

The value in `RO_SIHOT_MKT_SEG` is also optional and only needed if the Acumen Reservation Booking Type code (`RO_CODE`)
is different to the Sihot.PMS market segment code. The following table is showing the manual mappings for the Acumen
lower-case booking types:

| Sihot Market segment ID | Acumen Reservation Booking Type |
| --- | --- |
| FG | fG |
| FO | fO |
| H1 | hg |
| H2 | hG |
| H3 | hR |
| H5 | hr |
| H6 | hW |
| H7 | hw |
| I1 | ig |
| I2 | iG |
| I3 | ii |
| I4 | iI |
| IW | iW |
| RG | rW |
| RN | Ri |
| RP | Ro |
| TS | TC |
| TC | tk |
| T1 | tc |


#### Mapping of Acumen Reservation Group to Sihot Channel

The following table shows the mapping between the Sihot CHANNEL field IDs (stored in the `RO_SIHOT_RES_GROUP` column)
and the Acumen reservation groups (with the `RO_RES_GROUP` column):

| Sihot Channel Id | Acumen Reservation Group |
| --- | --- |
| FB | Promo + Marketing Rental |
| GU | Guest |
| OT | Others |
| OW | Keys Member + Owner |
| RE | RCI External |
| RI | RCI Internal |
| RR | Rental External |
| RS | Rental SG |

This mapping got restructured on 9-Aug-2018 - the changes are logged in the Acumen/Oracle table T_LOG (double check
with query: `select * from t_log where log_table = 'RESOCC_TYPES' and log_column = 'RO_SIHOT_RES_GROUP'
order by log_code desc`).


#### Mapping of Acumen SP Group to Sihot NN

Underneath the mapping of the Sihot NN field (`RO_SIHOT_SP_GROUP`) onto the Acumen Silverpoint Groups (`RO_SP_GROUP`):

| Acumen SP Group | Sihot NN Id |
| --- | --- |
| Rental SP | RS |
| SP Booking | SB |
| SP CP Booking | SC |
| SP PB Booking | SP |


#### Orderer Agency Configuration for each Market Segment

The `RO_AGENCY_` columns are needed for to store the Sihot.PMS guest object ids of an optional orderer/agency that will
then be used for these types of bookings.

Individual agencies got currently only mapped to the two Thomas Cook booking types: the `TK` (Thomas Cook Scandinavian)
bookings got associated to the Sihot guest Object ID `27` and the matchcode `TCRENT` whereas the `tk` (Thomas Cook UK)
booking type is associated to the object id `20` and the matchcode `TCAG`.


#### Market Segment Synchronization and Rate

The value within the `RO_SIHOT_RATE` column is not only defining a default rate (Sihot.PMS rate code) for each
Reservation Booking Type - it is also used as a flag: if there is a non-empty value then all bookings with this
Reservation Booking Type are then automatically included into the synchronization process from Acumen to Sihot.PMS.

The value of the column `RO_SIHOT_RATE` is currently initialized with the following where clause which includes all
bookings of our Timeshare Owners, Club Paradiso Members, RCI visitors, Marketing visitors, Thomas Cook visitors and
Owner External Rentals:

```
 where RO_CLASS in ('B', 'R')
   and (   substr(RO_RES_GROUP, 1, 5) = 'Owner'
        or substr(RO_RES_GROUP, 1, 13) = 'Club Paradiso'
        or substr(RO_RES_GROUP, 1, 3) = 'RCI'
        or substr(RO_RES_GROUP, 1, 5) = 'Promo'
        or RO_CODE in ('TK', 'tk')
        or RO_CODE = 'ER'   -- requested by Esther 03-11-2016
       );
```

The Thomas Cook bookings are still synchronized in the first project phase for to provide a smooth migration for our
Rental Department - although they meanwhile can be imported directly with the SihotResImport command tool into the
Sihot.PMS.


### Acumen Client Owner Type Classification

For to minimize the amount of client data to migrate to Sihot.PMS we had to classify the Acumen clients by their type of
ownership(s). For each product a owner type can be specified/configured within the new column `RS_SIHOT_GUEST_TYPE`.

The current mapping is setting a owner flag string for to group all timeshare/resort owners together with less
important owner types like e.g. tablet, lifestyle, experience or explorer. For special treatment we only need to specify
distinguishable client types for Investors (new fractionals/share holders) and Keys Members.


### SIHOT package mappings

The Sihot.PMS Package code can be specified as the value of the key-value attribute `SIHOT_PACK` within the `LU_CHAR`
column of each meal plan/board. All Acumen meal plans are stored within the lookup classes `BOARDS` (for all bookings)
and `MKT_BOARDS` (only for marketing bookings).

### Thomas Cook Allotment mappings

For to create tour operator bookings via the WEB interface you need to specify the internal number of the allotment
contract. This internal allotment contract number is nowhere visible in the GUI of Sihot.PMS and has to be determined
by Michael after the creation of the allotment in Sihot. UPDATE: the new version is showing the allotment number.

Each hotel and tour operator has a individual internal allotment contract number. So for our two tour operators Thomas
Cook Northern/Scandinavia and U.K. for the two initial hotels (1 and 4) we need to configure four numbers, which are
now specified within the new config file SihotMktSegExceptions.cfg. 


### Configuration files

The default values of each command line argument can be set within one of the configurations files. If the values are
not specified in the app configuration file then the option default/fallback values will be searched within the base
config file: first in the app name section then in the default main section. More information on the several supported
configuration files and values you find in the module/package `ae_console_app`.

The following configuration values are not available as command line argument options (can only be specified within a
configuration file):
            
| Section Name | Key/Option Name | Description |
| --- | --- | --- |
| Settings | addressValidatorBaseUrl | Base URL for address validation web service |
| Settings | addressValidatorSearchUrl | Search URL for address validation web service |
| Settings | addressValidatorFetchUrl | Fetch URL for address validation web service |
| Settings | addressValidatorApiKey | address validation web service API key |
| Settings | apCats | Room category overloads for single hotel rooms |
| Settings | assRootUsr | Root user account name for AssCache database |
| Settings | assRootPwd | Root user account name for AssCache database |
| Settings | emailValidatorBaseUrl | Base URL for email validation web service |
| Settings | emailValidatorApiKey | email validation web service API key |
| Settings | hotelIds | Mapping of Sihot/Acumen hotel ids |
| Settings | phoneValidatorBaseUrl | Base URL for phone number validation web service |
| Settings | phoneValidatorApiKey | phone number validation web service API key |
| Settings | resortCats | Room category defaults and apartment feature overloads for all hotels/resorts |
| Settings | roAgencies | Agency Sihot/Acumen object Ids and market segment groupings |
| Settings | roomChangeMaxDaysDiff | Number of days a check-in/-out/room-move can differ from the expected arrival/departure date |
| Settings | SfIdResetResendFragments | Text fragments of ignorable errors where BssServer will try to resend the reservation data without the currently cached Salesforce Reservation Opportunity Id |
| Settings | shAdultPersTypes | List of Sihot adult person type categories, e.g. ['1A', '5A'] |
| Settings | shChildPersTypes | List of Sihot children person type categories, e.g. ['2A', '2B', '2C', '6A', '6B', '6C'] |
| Settings | WarningFragments | List of text fragments of complete error messages which will be re-classified as warnings and send separately to the notification receiver (specified in configuration key/option `warningsMailToAddr` or `smtpTo`).
| SihotAllotments | <marketSegmentCode>[_<hotel_id>] | Allotment/contract number for each market segment (and hotel id) |
| SihotPaymentInstructions | <marketSegmentCode> | Sihot Payment Instruction code for each market segment | 
| SihotRateSegments | <marketSegmentCode> | Sihot Rate Segment code for each market segment |
| SihotResTypes | <marketSegmentCode> | Sihot Reservation Type overload code for each market segment |


## System Synchronizations

Because lots of different data (like clients, reservations, reservation inventory, ownerships, sales inventory) need to
be available redundantly in several of our systems (Acumen, Salesforce and Sihot) we have to ensure that any
changes of this data in one of the system will be propagated to other systems.

Each type of data (record set or field) must have a master which is the system where the data is most accurate. 

| Type of data | Future Master System -> Synchronized onto | Current Master System(s) -> Synchronized onto |
| --- | --- | --- |
| Clients | Salesforce->Sihot | Acumen->Sihot, Salesforce->None, Sihot->None |
| Rental reservations | Sihot->Salesforce | Sihot->None |
| Owner reservations | Salesforce->Sihot, Sihot->Salesforce | Acumen->Sihot |
| Room Occupation | Sihot->Salesforce | Sihot->Acumen |
| Reservation Inventory | Sihot->Salesforce | Acumen->None |
| Product ownerships | Salesforce->Sihot | Acumen->None, Salesforce->None |
| Sales inventory | Salesforce->Sihot | Acumen->None, Salesforce->None |

Whereas the synchronization from/to Acumen and Salesforce can be done in various ways because we even can access the
internal data structures (Oracle tables and Salesforce objects) directly, our Sihot system is (like most commercial
systems) only providing an access via several APIs, which are much more restricted than a direct data access.

Sihot is providing the following pull interfaces:

* create/update client/guest (Sihot Kernel Interface)
* create/update/delete reservation (Sihot Web Interface)

Additionally Sihot is providing the following live/push interfaces (via the Sihot SXML interface):

* Reservation Changes
* Guest Changes
* Occupation Changes

The [SysDataMan application](#sysdataman-application) can be used for to manually synchronize and/or compare client
and reservation data between our three systems (Acumen, Salesforce and Sihot).


### Synchronization between Acumen and Sihot
  
Every client that got created first on the Acumen system and then get migrated as guest record onto the Sihot system
will by associated by the Sihot guest object id. This id will be stored for each pax of our Acumen couple client
record in the two new columns `CD_SIHOT_OBJID` and `CD_SIHOT_OBJID2`. Client data is currently only synchronized
from Acumen to Sihot together with the reservation synchronization.

The two Acumen log tables [Requested Unit Log](#requested-unit-log) and [Synchronization Log](#synchronization-log)
are used for to detect any changes done in Acumen on the client/reservation data. The SihotResSync application is used
to periodically pass any reservation changes from Acumen to Sihot.

Reservations for owners and marketing clients get created within the Acumen system and get then synchronized to Sihot.
The link/association is done via the Sihot reservation record object which is stored within Acumen/Oracle in the
Requested Unit record (in the `T_RU` column `RU_SIHOT_OBJID`). On any change of the reservation within Acumen the
reservation request will be synchronized again onto Sihot (together with the client data if changed too).

The AcuServer application is passing any room changes (check-ins, check-outs and room-moves) done within Sihot back
to the Acumen system (for to keep the Acumen Allocation system up-to-date). Any other changes done on reservations
or clients within Sihot are not synchronized back to Acumen.

#### Requested Unit Log

The following 8 new columns got added to the Acumen Requested Unit Log table (`T_RUL`) for to store also any other
booking changes of a synchronized reservation that are happening in a associated table like e.g. room change in the
related Apartment Reservation (`T_ARO`) or board/meal plan change in the Marketing Prospect (`T_PRC`):

| Column Name | Column Content |
| --- | --- |
| RUL_SIHOT_CAT | Unit/Price category in Sihot.PMS - overloaded if associated ARO exists |
| RUL_SIHOT_HOTEL | Hotel Id in Sihot.PMS - overloaded if associated ARO exists |
| RUL_SIHOT_ROOM | Booked apartment (`AP_CODE` value as Sihot room number - with leading zero for 3-digit PBC room numbers) if associated ARO record exits else NULL |
| RUL_SIHOT_OBJID | `RU_SIHOT_OBJID` value (for to detect if deleted RU got passed into Sihot.PMS) |
| RUL_SIHOT_PACK | Booked package/arrangement - overloaded if associated ARO/PRC exists |
| RUL_SIHOT_RATE | Market segment - used for filtering (also if RU record is deleted) |
| RUL_SIHOT_LAST_CAT | Previous Unit/Price category - needed for cancellation |
| RUL_SIHOT_LAST_HOTEL | Previous Hotel Id - needed for cancellation and hotel moves |

These columns got added later on mainly because of performance enhancements by condensing/focusing all these other
changes within the latest not synchronized requested unit log entry/record and also for to keep references of deleted
`T_RU` records for to be propagated onto Sihot.PMS.


#### Synchronization Log

Any synchronizations are fully logged within the `T_SRSL` table of the Acumen system, providing the
following columns:

| Column Name | Column Content |
| --- | --- |
| SRSL_TABLE | Acumen Table ID (RU/ARO/CD) |
| SRSL_PRIMARY | Acumen Table Primary Key (`RU_CODE`/Requested Unit, `ARO_CODE`/Apartment Reservation or `CD_CODE`/Client Details) |
| SRSL_ACTION | Initiated Action/OC=operation-code Onto Sihot.PMS (for CD also action of Person2) |
| SRSL_STATUS | Final Status/Response of Sihot.PMS (synchronized if substr(,1,6)='SYNCED', else 'ERR\[RC-code\]') |
| SRSL_DATE | Date/Time of the insert into this log table |
| SRSL_LOGREF | Audit Trail Log Id (for debugging only) - Primary Key of either RUL/Requested Unit Log, AROL/Apartment Reservation Log or LOG/Client Details Log |
| SRSL_MESSAGE | Final or Error Message/Response of Sihot.PMS (taken from the MSG response xml element) |


### Synchronization between Salesforce and Sihot

The [BssServer application](#bssserver-application) will pass any changes of
reservation data and of room occupations (check-ins, check-outs and room-moves) done within Sihot to Salesforce (and
optionally also to the AssCache database).

Client and reservation data can be passed from Salesforce to Sihot by using the 
[SihotServer Web Services](#sihotserver-web-services).
