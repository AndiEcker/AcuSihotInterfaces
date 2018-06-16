# TODO: Implement bridge server listening to Salesforce for to create reservations and guests within the Sihot system

# In Salesforce we either creating an Button that calls an Apex Class that makes an API call to this server
# .. or we will use a Workflow, triggered by a record update to send an Outbound Message to this server

# Outbound Example with twisted: https://salesforce.stackexchange.com/questions/94279/parsing-outbound-message-in-python
# .. and https://developer.salesforce.com/docs/atlas.en-us.api.meta/api/sforce_api_quickstart_intro.htm

"""
Steps to distribute/roll-out to Salesforce production:
- Authorize Endpoint Addresses: see https://trailhead.salesforce.com/modules/apex_integration_services/units/apex_integration_callouts#apex_integration_callouts_authorizing
- In the Developer Console, select Debug | Open Execute Anonymous Window and put the APEX code:
    Http http = new Http();
    HttpRequest request = new HttpRequest();
    request.setEndpoint('https://tf-sh-sihot3v.acumen.es/res/upsert');
    request.setMethod('PUT');
    HttpResponse response = http.send(request);
    // If the request is successful, parse the JSON response.
    if (response.getStatusCode() == 200) {
        // Deserialize the JSON string into collections of primitive data types.
        Map<String, Object> results = (Map<String, Object>) JSON.deserializeUntyped(response.getBody());
        // Cast the values in the 'animals' key as a list
        List<Object> ids = (List<Object>) results.get('ids');
        System.debug('Received the following ids:');
        for (Object id_str: ids) {
            System.debug(id_str);
        }
    }
-

"""

# following example taken from https://github.com/apex/up-examples/tree/master/oss/python-bottle
from bottle import route, run, template


@route('/')
def hello():
    return "hello"


@route('/res/upsert/<name>')
def hello(name):
    return template('Hola <b>{{name}}</b> - guapetón!', name=name)


run(port=9090)
