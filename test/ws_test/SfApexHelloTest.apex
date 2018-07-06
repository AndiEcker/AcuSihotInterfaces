// simple test of apex callout
JSONGenerator gen = JSON.createGenerator(true);
gen.writeStartObject();
gen.writeStringField('NAME', 'world');
gen.writeEndObject();
System.debug('json generator=' + gen);

HttpRequest request = new HttpRequest();
request.setEndpoint('https://lint.signallia.com/lint');
request.setMethod('GET');
// adding body results in Method Not Allowed error (status_code=405): request.setBody(gen.getAsString());
System.debug('json=' + gen.getAsString());
System.debug('request=' + request);

// send request to web service server
Http http = new Http();
HttpResponse response = http.send(request);
System.debug('response=' + response);

Integer status_code = response.getStatusCode();
System.debug('Hello service returned with status code ' + status_code);
