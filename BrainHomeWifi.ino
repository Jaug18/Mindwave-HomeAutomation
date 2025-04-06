#include <ESP8266WiFi.h>
#include <WiFiClient.h>
#include <ESP8266WebServer.h>
#include <ArduinoJson.h>
#include <SoftwareSerial.h>

// Configuración WiFi
const char* ssid = "TuRedWiFi";
const char* password = "TuContraseña";

// Servidor web en puerto 80
ESP8266WebServer server(80);

// Puerto serie software para comunicación con Arduino principal
SoftwareSerial arduinoSerial(D2, D3); // RX, TX

// Buffer para comunicación serie
String inputBuffer = "";
bool commandComplete = false;

// Estado del sistema
DynamicJsonDocument deviceState(512);

void setup() {
  // Iniciar puerto serie para depuración
  Serial.begin(115200);
  Serial.println("\nBrainHome WiFi Extension");
  
  // Iniciar puerto serie software para comunicación con Arduino
  arduinoSerial.begin(115200);
  
  // Conectar a WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.print("Connected to WiFi, IP address: ");
  Serial.println(WiFi.localIP());
  
  // Configurar rutas del servidor web
  setupWebServer();
  
  // Iniciar servidor
  server.begin();
  Serial.println("HTTP server started");
  
  // Inicializar estado
  deviceState["devices"]["light_main"] = "off";
  deviceState["devices"]["light_sec"] = "off";
  deviceState["devices"]["blind"] = 50;
  deviceState["devices"]["fan"] = "off";
  deviceState["devices"]["tv"] = "off";
  
  // Solicitar estado actual
  requestStatus();
}

void loop() {
  // Manejar clientes web
  server.handleClient();
  
  // Leer respuestas desde Arduino
  while (arduinoSerial.available() > 0) {
    char inChar = (char)arduinoSerial.read();
    inputBuffer += inChar;
    
    // Verificar finalización de respuesta
    if (inChar == '\n') {
      commandComplete = true;
      break;
    }
  }
  
  // Procesar respuesta completa
  if (commandComplete) {
    processArduinoResponse(inputBuffer);
    inputBuffer = "";
    commandComplete = false;
  }
  
  delay(10);
}

void setupWebServer() {
  // Página principal - Interface de control
  server.on("/", HTTP_GET, []() {
    String html = "<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'>";
    html += "<title>BrainHome Control</title>";
    html += "<style>";
    html += "body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f0f0f0; }";
    html += ".container { max-width: 800px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }";
    html += "h1 { color: #3498db; text-align: center; }";
    html += ".device { margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 8px; }";
    html += ".device-title { font-weight: bold; margin-bottom: 10px; }";
    html += ".button { display: inline-block; padding: 8px 16px; background-color: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer; margin-right: 10px; text-decoration: none; }";
    html += ".button.off { background-color: #e74c3c; }";
    html += ".status { display: inline-block; padding: 5px 10px; border-radius: 15px; font-size: 14px; color: white; margin-left: 10px; }";
    html += ".status.on { background-color: #2ecc71; }";
    html += ".status.off { background-color: #e74c3c; }";
    html += ".slider { width: 80%; margin: 10px 0; }";
    html += "</style>";
    html += "</head><body>";
    html += "<div class='container'>";
    html += "<h1>BrainHome Control System</h1>";
    
    // Dispositivo: Luz Principal
    html += "<div class='device'>";
    html += "<div class='device-title'>Luz Principal</div>";
    html += "<a href='/control?device=light_main&state=on' class='button'>Encender</a>";
    html += "<a href='/control?device=light_main&state=off' class='button off'>Apagar</a>";
    html += "<span class='status " + String(deviceState["devices"]["light_main"] == "on" ? "on" : "off") + "'>" + 
            String(deviceState["devices"]["light_main"] == "on" ? "Encendido" : "Apagado") + "</span>";
    html += "</div>";
    
    // Dispositivo: Luz Secundaria
    html += "<div class='device'>";
    html += "<div class='device-title'>Luz Secundaria</div>";
    html += "<a href='/control?device=light_sec&state=on' class='button'>Encender</a>";
    html += "<a href='/control?device=light_sec&state=off' class='button off'>Apagar</a>";
    html += "<span class='status " + String(deviceState["devices"]["light_sec"] == "on" ? "on" : "off") + "'>" + 
            String(deviceState["devices"]["light_sec"] == "on" ? "Encendido" : "Apagado") + "</span>";
    html += "</div>";
    
    // Dispositivo: Persiana
    html += "<div class='device'>";
    html += "<div class='device-title'>Persiana (" + String((int)deviceState["devices"]["blind"]) + "%)</div>";
    html += "<form action='/control' method='get'>";
    html += "<input type='hidden' name='device' value='blind'>";
    html += "<input type='range' name='state' min='0' max='100' value='" + String((int)deviceState["devices"]["blind"]) + "' class='slider' onchange='this.form.submit()'>";
    html += "</form>";
    html += "<a href='/control?device=blind&state=0' class='button off'>Cerrar</a>";
    html += "<a href='/control?device=blind&state=100' class='button'>Abrir</a>";
    html += "</div>";
    
    // Dispositivo: Ventilador
    html += "<div class='device'>";
    html += "<div class='device-title'>Ventilador</div>";
    html += "<a href='/control?device=fan&state=on' class='button'>Encender</a>";
    html += "<a href='/control?device=fan&state=off' class='button off'>Apagar</a>";
    html += "<span class='status " + String(deviceState["devices"]["fan"] == "on" ? "on" : "off") + "'>" + 
            String(deviceState["devices"]["fan"] == "on" ? "Encendido" : "Apagado") + "</span>";
    html += "</div>";
    
    // Dispositivo: TV
    html += "<div class='device'>";
    html += "<div class='device-title'>Televisión</div>";
    html += "<a href='/control?device=tv&state=on' class='button'>Encender</a>";
    html += "<a href='/control?device=tv&state=off' class='button off'>Apagar</a>";
    html += "<span class='status " + String(deviceState["devices"]["tv"] == "on" ? "on" : "off") + "'>" + 
            String(deviceState["devices"]["tv"] == "on" ? "Encendido" : "Apagado") + "</span>";
    html += "</div>";
    
    // Acciones globales
    html += "<div class='device'>";
    html += "<div class='device-title'>Acciones Globales</div>";
    html += "<a href='/control?command=all_off' class='button off'>Apagar Todo</a>";
    html += "<a href='/refresh' class='button'>Actualizar Estado</a>";
    html += "</div>";
    
    html += "</div>"; // Fin del container
    
    // Script para refrescar automáticamente
    html += "<script>";
    html += "setTimeout(function(){ location.reload(); }, 30000);"; // Recargar cada 30 segundos
    html += "</script>";
    
    html += "</body></html>";
    server.send(200, "text/html", html);
  });
  
  // Endpoint para controlar dispositivos
  server.on("/control", HTTP_GET, []() {
    String device = server.arg("device");
    String state = server.arg("state");
    String command = server.arg("command");
    
    DynamicJsonDocument doc(256);
    
    if (command != "") {
      // Comando global (e.g., all_off)
      doc["cmd"] = command;
    } else if (device != "" && state != "") {
      // Control de dispositivo específico
      doc["cmd"] = "set";
      JsonObject params = doc.createNestedObject("params");
      params["device"] = device;
      params["state"] = state;
    } else {
      server.send(400, "text/plain", "Parámetros inválidos");
      return;
    }
    
    // Enviar comando a Arduino
    String jsonCommand;
    serializeJson(doc, jsonCommand);
    arduinoSerial.println(jsonCommand);
    
    // Redireccionar a la página principal
    server.sendHeader("Location", "/", true);
    server.send(302, "text/plain", "");
  });
  
  // Endpoint para refrescar estado
  server.on("/refresh", HTTP_GET, []() {
    requestStatus();
    
    // Redireccionar a la página principal
    server.sendHeader("Location", "/", true);
    server.send(302, "text/plain", "");
  });
  
  // API REST para obtener estado en formato JSON
  server.on("/api/status", HTTP_GET, []() {
    String jsonString;
    serializeJson(deviceState, jsonString);
    server.send(200, "application/json", jsonString);
  });
  
  // Manejar 404
  server.onNotFound([]() {
    server.send(404, "text/plain", "Página no encontrada");
  });
}

void requestStatus() {
  // Solicitar estado actual a Arduino
  DynamicJsonDocument doc(64);
  doc["cmd"] = "status";
  
  String jsonCommand;
  serializeJson(doc, jsonCommand);
  arduinoSerial.println(jsonCommand);
  
  Serial.println("Status requested");
}

void processArduinoResponse(String response) {
  // Procesar respuesta JSON desde Arduino
  DynamicJsonDocument doc(512);
  DeserializationError error = deserializeJson(doc, response);
  
  if (error) {
    Serial.print("Error parsing JSON: ");
    Serial.println(error.c_str());
    return;
  }
  
  // Si la respuesta contiene estado de dispositivos, actualizar
  if (doc.containsKey("status") && doc.containsKey("devices")) {
    // Actualizar estado de dispositivos
    deviceState["devices"] = doc["devices"];
    
    Serial.println("Device state updated");
  } else if (doc.containsKey("message")) {
    // Mensaje de estado
    String message = doc["message"].as<String>();
    Serial.println("Status message: " + message);
  } else if (doc.containsKey("error")) {
    // Mensaje de error
    String errorMessage = doc["error"].as<String>();
    Serial.println("Error message: " + errorMessage);
  }
}