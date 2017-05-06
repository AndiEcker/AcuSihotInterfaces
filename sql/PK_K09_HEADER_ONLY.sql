CREATE OR REPLACE PACKAGE SALES.K
AS
  /*PRAGMA restrict_references(WNDS);*/

  /* Various System Constants */

  OwnerInventory    constant INV_TYPES.IT_CODE%TYPE := 'OWND'; /* Owner inventory */
  OwnerPBHC         constant INV_TYPES.IT_CODE%TYPE := 'OWPB'; /* PBC inventory owned by PBHC*/
  MaintInventory    constant INV_TYPES.IT_CODE%TYPE := 'MAIN'; /* Maintenance inventory */
  RPNVAL            constant INV_TYPES.IT_CODE%TYPE := 'SPNV'; /* Silverpoint Null Value Inventory */

  PrivateResaleDeal constant DEALS.DL_TYPE%TYPE     := 'PRIVATE';
  ChangeOfOwnerDeal constant DEALS.DL_TYPE%TYPE     := 'OWNER_CHANGE';
  PBHCConversionDeal constant DEALS.DL_TYPE%TYPE    := 'PBHC_CONVERT';
  PointsConversionDeal constant DEALS.DL_TYPE%TYPE    := 'POINTS_CONVERT';
  ConfiscateDeal    constant DEALS.DL_TYPE%TYPE     := 'CNFS';
  NewInventoryDeal  constant DEALS.DL_TYPE%TYPE     := 'NEW_INV';
  NonAccExchange    constant DEALS.DL_TYPE%TYPE     := 'NONACC_EXCH';

  WeekStartDayUnknown constant APT_WEEKS.WK_START_OFFSET_DAYS%TYPE := -9; /* Unknown Changeover Day */
  
  SihotRoomChangeMaxDaysDiff constant T_RU.RU_DAYS%type := 4; 

  /* StatusCode Constants */
  Unconfirmed   constant STAT_CODES.ST_CODE%TYPE := 100; /* Checked in */
  Unconf2       constant STAT_CODES.ST_CODE%TYPE := 120;
  Unconf3       constant STAT_CODES.ST_CODE%TYPE := 130;
  Unconf4       constant STAT_CODES.ST_CODE%TYPE := 140;
  UnconfR       constant STAT_CODES.ST_CODE%TYPE := 170; /* Ready for printing PA */
  UnconfP       constant STAT_CODES.ST_CODE%TYPE := 180; /* PA has been printed */
  PleaseConfirm constant STAT_CODES.ST_CODE%TYPE := 190; /* Done and ready for Confirmation */

  Burn          constant STAT_CODES.ST_CODE%TYPE := 200; /* Burn Statuses */
  BurnDeck      constant STAT_CODES.ST_CODE%TYPE := 220;
  BurnButt      constant STAT_CODES.ST_CODE%TYPE := 250;
  NoSale        constant STAT_CODES.ST_CODE%TYPE := 260;
  CanceledExch  constant STAT_CODES.ST_CODE%TYPE := 270; /* A previously OnHold IN week has been canceled */

  OnHold        constant STAT_CODES.ST_CODE%TYPE := 300; /* On Hold status */
  WeeksOnHold    constant STAT_CODES.ST_CODE%TYPE := 310; /* Weeks on Hold */
  PostedForSign constant STAT_CODES.ST_CODE%TYPE := 330; /* Posted Sor Signing */
  TransOfResale constant STAT_CODES.ST_CODE%TYPE := 370; /* Tranfer Of Resales */
  WaitingForTOF constant STAT_CODES.ST_CODE%TYPE := 380; /* Waiting for Tranfer Of Funds */

  Confirmed     constant STAT_CODES.ST_CODE%TYPE := 400; /* Deal Confirmed */

  PreCancel     constant STAT_CODES.ST_CODE%TYPE := 500; /* Pre-Cancelation of Deal */
  TOF           constant STAT_CODES.ST_CODE%TYPE := 540; /* Tranfer Of Funds Cancelation */
  Canceled      constant STAT_CODES.ST_CODE%TYPE := 550; /* Deal Canceled */

  ExchProblem   constant STAT_CODES.ST_CODE%TYPE := 610; /* Problem with Exchange */

  FinCompleted constant STAT_CODES.ST_CODE%TYPE := 770; -- Deal Completed subject to Finance
  PartComplete  constant STAT_CODES.ST_CODE%TYPE := 780; /* Deal Partly Complete */
  Confiscated   constant STAT_CODES.ST_CODE%TYPE := 785; /* Week Confiscated */
  Reinstated    constant STAT_CODES.ST_CODE%TYPE := 786; /* Week Reinstated */
  Completed     constant STAT_CODES.ST_CODE%TYPE := 790; /* Deal or Week Completed */

  NonAcceptance constant STAT_CODES.ST_CODE%TYPE := 791; /* Non Acceptance of sale by seller */
  OccyProblem   constant STAT_CODES.ST_CODE%TYPE := 792; /* Occupancy Problem */
  WaitingDocs   constant STAT_CODES.ST_CODE%TYPE := 793; /* Waiting on documentation */

  RetToResales  constant STAT_CODES.ST_CODE%TYPE := 795; /* Return To Resales */
  ConfInResales constant STAT_CODES.ST_CODE%TYPE := 796; /* Confirmed in Resales */
  SendAccounts  constant STAT_CODES.ST_CODE%TYPE := 798; /* Send to Accounts */
  SentAccounts  constant STAT_CODES.ST_CODE%TYPE := 799; /* Sent to Accounts */
  NewlyReturned constant STAT_CODES.ST_CODE%TYPE := 810; /* Newly Returned */

  Listed        constant STAT_CODES.ST_CODE%TYPE := 850; /* Listing Statuses */
  Delisted      constant STAT_CODES.ST_CODE%TYPE := 860;
  Expired       constant STAT_CODES.ST_CODE%TYPE := 870;
  Renewal       constant STAT_CODES.ST_CODE%TYPE := 880;
  RenewalSent   constant STAT_CODES.ST_CODE%TYPE := 881;
  AutoRenew     constant STAT_CODES.ST_CODE%TYPE := 882;

  Available     constant STAT_CODES.ST_CODE%TYPE := 890; /* Week Availabkle for Resale */

  Unavailable   constant STAT_CODES.ST_CODE%TYPE := 970; /* currently only for Traded-In Explorer Membership */


  /* Client/Reservation StatusCode Constants */
  CDNewClient     constant STAT_CODES.ST_CODE%TYPE := 100; /* New Client */
  CDMktRejected   constant STAT_CODES.ST_CODE%TYPE := 120; /* Rejected by Marketing as unsuitable */
  CDResRequested  constant STAT_CODES.ST_CODE%TYPE := 150; /* Reservation requested */
  CDResOnHold     constant STAT_CODES.ST_CODE%TYPE := 170; /* Reservation on hold */
  CDResConfirmed  constant STAT_CODES.ST_CODE%TYPE := 200; /* Reservation confirmed */
  CDResCancelled  constant STAT_CODES.ST_CODE%TYPE := 250; /* Reservation cancelled */
  CDCheckedIn     constant STAT_CODES.ST_CODE%TYPE := 300; /* Client checked in */
  CDCheckedOutNT  constant STAT_CODES.ST_CODE%TYPE := 350; /* Client checked out - not toured */
  CDToured        constant STAT_CODES.ST_CODE%TYPE := 400; /* Client has toured but not purchased */
  CDPurchased     constant STAT_CODES.ST_CODE%TYPE := 500; /* Client has a Deal (Sales history) */
  CDCancelled     constant STAT_CODES.ST_CODE%TYPE := 550; /* Client has Cancelled all Deals*/
  CDCurrentOwner  constant STAT_CODES.ST_CODE%TYPE := 600; /* Client is a current Owner */
  CDPreviousOwner constant STAT_CODES.ST_CODE%TYPE := 650; /* Client has sold all ownerships */
  CDBlackCurrent  constant STAT_CODES.ST_CODE%TYPE := 666; /* Client is Blacklisted (Current Owner)*/
  CDBlackPrevious constant STAT_CODES.ST_CODE%TYPE := 667; /* Client is Blacklisted (Previous Owner) */

  /* Client Type Constants */
  ClientInvestor  constant CLIENT_DETAILS.CD_TYPE%TYPE := 'INVESTOR';  /* Ordinary Investor */
  ClientPreferred constant CLIENT_DETAILS.CD_TYPE%TYPE := 'PREFERRED'; /* Preferential Investor (receives Oversell) */

   /* Reservation/Occupancy Constants*/
  ROCancelled     constant LOBBY.APT_RES_OCC.ARO_STATUS%TYPE:=120;
  ROBlocked       constant LOBBY.APT_RES_OCC.ARO_STATUS%TYPE:=123;
  RORequest       constant LOBBY.APT_RES_OCC.ARO_STATUS%TYPE:=150;
  ROOnHold        constant LOBBY.APT_RES_OCC.ARO_STATUS%TYPE:=170;
  ROResAccepted   constant LOBBY.APT_RES_OCC.ARO_STATUS%TYPE:=190; -- ae:11-02-06 added
  ROConfirmed     constant LOBBY.APT_RES_OCC.ARO_STATUS%TYPE:=200;
  RONoShow        constant LOBBY.APT_RES_OCC.ARO_STATUS%TYPE:=210;
  ROOnSiteNotOcc  constant LOBBY.APT_RES_OCC.ARO_STATUS%TYPE:=220;
  ROCheckedIn     constant LOBBY.APT_RES_OCC.ARO_STATUS%TYPE:=300;
  ROTransferOut   constant LOBBY.APT_RES_OCC.ARO_STATUS%TYPE:=320;
  ROTransferIn    constant LOBBY.APT_RES_OCC.ARO_STATUS%TYPE:=330;
  ROCheckedOut    constant LOBBY.APT_RES_OCC.ARO_STATUS%TYPE:=390;

  /* ae:11-02-06 added Marketing Leads (T_ML) StatusCode Constants */
  MLNewLead       constant MKT_LEADS.ML_STATUS%TYPE := 100; /* New Lead */
  MLPreBooking    constant MKT_LEADS.ML_STATUS%TYPE := 110; /* High risk lead presented - awaiting further advice from generator before proceeding */
  MLFeePaid       constant MKT_LEADS.ML_STATUS%TYPE := 112; /* Prebooking lead with fees paid */
  MLPromoFollowUp constant MKT_LEADS.ML_STATUS%TYPE := 115; /* Response from advertisement received but subject to survey */
  MLOnHold        constant MKT_LEADS.ML_STATUS%TYPE := 120; /* Lead on hold for whatrever reason */
  MLRejected      constant MKT_LEADS.ML_STATUS%TYPE := 130; /* Lead rejected by manager */
  MLBlowout       constant MKT_LEADS.ML_STATUS%TYPE := 135; /* MktLead Blowout */
  MLCancelled     constant MKT_LEADS.ML_STATUS%TYPE := 140; /* Client cancelled */
  MLMoreWork      constant MKT_LEADS.ML_STATUS%TYPE := 150; /* More work needed before approval */
  MLSentElsewhere constant MKT_LEADS.ML_STATUS%TYPE := 155; /* Lead approved for another resort (BIN) */
  MLForApproval   constant MKT_LEADS.ML_STATUS%TYPE := 160; /* Lead presented for approval */
  MLResRequested  constant MKT_LEADS.ML_STATUS%TYPE := 180; /* Lead approved and reservation requested */
  MLResProblem    constant MKT_LEADS.ML_STATUS%TYPE := 185; /* Problem with creating reservation; returned to Marketing by Res. Dept. */
  MLResAccepted   constant MKT_LEADS.ML_STATUS%TYPE := 190; /* Reservation accepted without allocating an apartment */
  MLResConfirmed  constant MKT_LEADS.ML_STATUS%TYPE := 200; /* Reservation accepted with an apartment allocated */
  MLAcknowledged  constant MKT_LEADS.ML_STATUS%TYPE := 220; /* Client acknowledged with flight details */

  /* special variable for audit trail (EVENTLOG) */
  ExecutingMainProc VARCHAR2(50);
  ExecutingAction   VARCHAR2(50);
  ExecutingSubProc  VARCHAR2(50);
  ProcedureStack    varchar2(2000);

  /* location variable contains: MALTA, TENERIFE, ... */
  cLocation         T_LU.LU_CHAR%type;

  UseClientCurrency boolean := FALSE; /* Should we use CD_CUREF for deals? */
  HouseRate         T_LU.LU_NUMBER%type := 110/100; /* House rate multible (avoid using decimal with mathm. notation: 110/100=1.10)*/
  SellingRate       T_LU.LU_NUMBER%type := 115/100; /* Selling rate multible 115/100 = 1.15 */

  MainCurrency      T_CU.CU_CODE%type := 'GBP'; /* Central System Currency */
  AccountsCurrency  T_CU.CU_CODE%type := 'EUR'; /* Accounting System Currency */
  DefaultCCcurrency T_CU.CU_CODE%type := 'EUR'; /* Default Credit Card Currency */

END K;
/


