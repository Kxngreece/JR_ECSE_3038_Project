
#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include "env.h"

bool sensor = false;
int sensorValue;

OneWire oneWire(temp_sensor);
DallasTemperature sensors(&oneWire);

float temp(){
  sensors.requestTemperatures();
  float x = sensors.getTempCByIndex(0);
  return x;
}

bool presence(){
  int person_in_room;
  sensorValue = digitalRead(pir_sensor);

  if (sensorValue == HIGH) {
    delay(100);
    
    if (sensor == false) {
      sensor= true;

    }
  } 
  else {
      delay(200);
      
      if (sensor == true){
        sensor = false;
    }
  }

  return sensor;
}


void postSensor(float temp, bool presence){
  HTTPClient http;
  String requestBody;

  String new_endpoint;
  String path = "/sensor";
  new_endpoint = tempendpoint + path,

  http.begin(new_endpoint);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("Content-Length", "62");

  JsonDocument doc;

  doc["temperature"] = temp;
  doc["presence"] = presence;

  doc.shrinkToFit();

  serializeJson(doc, requestBody);

  int httpResponseCode = http.POST(requestBody);
  
  Serial.print("HERE IS THE RESPONSE: ");
  Serial.println(http.getString());
  Serial.println();

  http.end();
}

void getFanData(){
  HTTPClient http;

  String new_endpoint;
  String path = "/fan";
  new_endpoint = fanendpoint + path,

  http.begin(new_endpoint);

  int httpResponseCode = http.GET();

  if(httpResponseCode > 0) {
    Serial.print("HTTP Response code: ");
    Serial.println(httpResponseCode);

    String responseBody = http.getString();
    Serial.println(responseBody);

    JsonDocument doc;

    DeserializationError error = deserializeJson(doc, responseBody);

    if (error) {
      Serial.print("deserializeJson() failed: ");
      Serial.println(error.c_str());
      return;
    }

    const bool fan_ctrl = doc["fan"]; 

    digitalWrite(fan, fan_ctrl); 
    
    }
    else{
      Serial.print("Error Code: ");
      Serial.println(httpResponseCode);
    }
  
    http.end();

}

void getLightData(){

  HTTPClient http;

  String new_endpoint;
  String path = "/light";
  new_endpoint = lightendpoint + path,

  http.begin(new_endpoint);

  int httpResponseCode = http.GET();

  if(httpResponseCode > 0) {

    Serial.print("HTTP Response code: ");
    Serial.println(httpResponseCode);

    String responseBody = http.getString();
    Serial.println(responseBody);

    JsonDocument doc;

    DeserializationError error = deserializeJson(doc, responseBody);

    if (error) {
      Serial.print("deserializeJson() failed: ");
      Serial.println(error.c_str());
      return;
    }

    const bool light_ctrl = doc["light"]; 

    digitalWrite(light, light_ctrl);

    }
    else{
      Serial.print("Error Code: ");
      Serial.println(httpResponseCode);
    }
  
    http.end();

}


void setup() {
  Serial.begin(9600);
  
  // WiFi_SSID and WIFI_PASS should be stored in the env.h
  WiFi.begin(ssid, password);
  Serial.println("Connecting");

  while(WiFi.status() != WL_CONNECTED) 
  {
    delay(1000);
    Serial.print(".");
  }

  Serial.println("");
  Serial.print("Connected to WiFi network with IP Address: ");
  Serial.println(WiFi.localIP());

  
  pinMode(light, OUTPUT);
  pinMode(pir_sensor, INPUT);
  pinMode(fan,OUTPUT);
}

void loop() {

  //Check WiFi connection status
  if(WiFi.status()== WL_CONNECTED){
    delay(200);
    bool pir = presence();
    float temperature = temp();
    postSensor(temperature,pir);
    delay(5000);

    getFanData();
    getLightData();
    delay(5000);
  }
  else {
    Serial.println("WiFi Disconnected");
  }
}

