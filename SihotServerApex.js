// prepare web service request body with parameters in JSON format
Opportunity res_opp = Trigger.new[0];   // or: = [select Arrival_Date__c, Departure... from Opp...];
JSONGenerator gen = JSON.createGenerator(true);
gen.writeStartObject();
gen.writeStringField('ARR_DATE', res_opp.Arrival_Date__c);
//...     <-- more web service parameters
gen.writeEndObject();
HttpRequest request = new HttpRequest();
request.setEndpoint(ws_url);
request.setMethod('PUT');
request.setBody(gen.getAsString())
// send request to web service server
Http http = new Http();
HttpResponse response = http.send(request);
status_code = response.getStatusCode();
if (status_code == 200) {      // if no error code then parse the JSON response
    // deserialize the JSON string into collections of primitive data types
    Map<String, Object> results = (Map<String, Object>) JSON.deserializeUntyped(response.getBody());
    res_opp.Resort__c = results.get('Sihot_Hotel_Id');         // update hotel/resort id
    //...    <-- more SF data updates, like e.g. res-id/sync-timestamp/audit/...
    // lists need to be type casted: List<Object> ids = (List<Object>) results.get('ids');
}
else {      // status_code == 400: error handling using JSON fields Error and Message
}