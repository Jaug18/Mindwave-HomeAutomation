#include <ESP8266WiFi.h>
#include <WiFiClient.h>
#include <ESP8266WebServer.h>
#include <ArduinoJson.h>
#include <EEPROM.h>
#include <Servo.h>
#include <IRremote.h>

// Configuración WiFi
const char* ssid = "TuRedWiFi";
const char* password = "TuContraseña";

// Servidor web en puerto 80
ESP8266WebServer server(80);

// Definición de pines para dispositivos (adaptados para ESP8266/ESP32)
#define PIN_LIGHT_MAIN D1     // GPIO5
#define PIN_LIGHT_SEC D2      // GPIO4
#define PIN_BLIND D3          // GPIO0 - Para servo
#define PIN_FAN D5            // GPIO14
#define PIN_TV_RELAY D6       // GPIO12
#define PIN_LED_STATUS D0     // GPIO16
#define PIN_IR_LED D7         // GPIO13

// Para servomotores (persiana)
Servo blindServo;

// Para control infrarrojo (TV, aire acondicionado)
IRsend irSender(PIN_IR_LED);

// Estructura para estado de dispositivos
struct DeviceState {
  bool lightMain;
  bool lightSec;
  int blindPosition;  // 0-100%
  bool fan;
  bool tv;
};

// Estado actual y configuración
DeviceState currentState;
unsigned long lastCommandTime = 0;
bool emergencyMode = false;
int eepromAddress = 0;

// Estado del sistema
DynamicJsonDocument deviceState(512);

void setup() {
  // Iniciar puerto serie para comunicación con PC
  Serial.begin(115200);
  Serial.println("\nBrainHome ESP Controller");
  
  // Iniciar EEPROM
  EEPROM.begin(512);
  
  // Configurar pines
  pinMode(PIN_LIGHT_MAIN, OUTPUT);
  pinMode(PIN_LIGHT_SEC, OUTPUT);
  pinMode(PIN_FAN, OUTPUT);
  pinMode(PIN_TV_RELAY, OUTPUT);
  pinMode(PIN_LED_STATUS, OUTPUT);
  
  // Configurar servo
  blindServo.attach(PIN_BLIND);
  
  // Inicializar estado desde EEPROM
  loadStateFromEEPROM();
  
  // Conectar a WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    digitalWrite(PIN_LED_STATUS, !digitalRead(PIN_LED_STATUS)); // Parpadeo durante conexión
  }
  Serial.println("");
  Serial.print("Connected to WiFi, IP address: ");
  Serial.println(WiFi.localIP());
  
  // Iniciar IR
  irSender.begin();
  
  // Aplicar estado inicial
  applyCurrentState();
  
  // Indicar inicio exitoso
  blinkStatusLED(3);
  
  // Configurar rutas del servidor web
  setupWebServer();
  
  // Iniciar servidor
  server.begin();
  Serial.println("HTTP server started");
  
  // Inicializar estado para la interfaz web
  updateDeviceState();
  
  // Enviar estado inicial por Serial
  sendStatusUpdate();
}

void loop() {
  // Manejar clientes web
  server.handleClient();
  
  // Verificar tiempo desde último comando (para modo de emergencia)
  unsigned long currentTime = millis();
  if (currentTime - lastCommandTime > 60000 && !emergencyMode) {  // 1 minuto
    // Entrar en modo de emergencia si no hay comunicación
    emergencyMode = true;
    // En modo emergencia podríamos apagar dispositivos críticos
  }
  
  // Verificar estados y realizar acciones periódicas
  checkDevices();
  
  delay(50);  // Pequeña pausa para estabilidad
}

void processCommand(String command) {
  // Actualizar tiempo de último comando
  lastCommandTime = millis();
  if (emergencyMode) {
    emergencyMode = false;
    sendStatusMessage("Exiting emergency mode. Normal operation resumed.");
  }
  
  // Analizar JSON
  DynamicJsonDocument doc(512);
  DeserializationError error = deserializeJson(doc, command);
  
  // Verificar si el JSON es válido
  if (error) {
    sendErrorMessage("Invalid JSON command");
    return;
  }
  
  // Extraer comando principal
  String cmd = doc["cmd"].as<String>();
  
  // Procesar comando
  if (cmd == "set") {
    // Comando para controlar un dispositivo
    String device = doc["params"]["device"].as<String>();
    String state = doc["params"]["state"].as<String>();
    
    setDeviceState(device, state);
    saveStateToEEPROM();
    updateDeviceState();
    sendStatusUpdate();
    
  } else if (cmd == "get") {
    // Comando para obtener estado
    sendStatusUpdate();
    
  } else if (cmd == "all_off") {
    // Apagar todos los dispositivos
    turnAllOff();
    saveStateToEEPROM();
    updateDeviceState();
    sendStatusUpdate();
    
  } else if (cmd == "status") {
    // Enviar estado actual
    sendStatusUpdate();
    
  } else if (cmd == "reset") {
    // Reiniciar ESP
    resetESP();
    
  } else {
    // Comando desconocido
    sendErrorMessage("Unknown command: " + cmd);
  }
}

void setDeviceState(String device, String state) {
  bool stateOn = (state == "on");
  int stateValue = -1;
  
  // Si hay un valor numérico (e.g., para persiana)
  if (state.toInt() > 0 || state == "0") {
    stateValue = state.toInt();
  }
  
  // Controlar el dispositivo correspondiente
  if (device == "light_main") {
    digitalWrite(PIN_LIGHT_MAIN, stateOn ? HIGH : LOW);
    currentState.lightMain = stateOn;
    sendStatusMessage("Main light " + state);
    
  } else if (device == "light_sec") {
    digitalWrite(PIN_LIGHT_SEC, stateOn ? HIGH : LOW);
    currentState.lightSec = stateOn;
    sendStatusMessage("Secondary light " + state);
    
  } else if (device == "blind") {
    if (stateValue >= 0 && stateValue <= 100) {
      moveBlind(stateValue);
      currentState.blindPosition = stateValue;
      sendStatusMessage("Blind position set to " + state + "%");
    } else if (state == "up") {
      moveBlind(100);
      currentState.blindPosition = 100;
      sendStatusMessage("Blind moving up");
    } else if (state == "down") {
      moveBlind(0);
      currentState.blindPosition = 0;
      sendStatusMessage("Blind moving down");
    }
    
  } else if (device == "fan") {
    digitalWrite(PIN_FAN, stateOn ? HIGH : LOW);
    currentState.fan = stateOn;
    sendStatusMessage("Fan " + state);
    
  } else if (device == "tv") {
    // Control de TV por IR y relé
    if (stateOn) {
      sendIRCommand(TV_POWER);
      digitalWrite(PIN_TV_RELAY, HIGH);
    } else {
      sendIRCommand(TV_POWER);
      digitalWrite(PIN_TV_RELAY, LOW);
    }
    currentState.tv = stateOn;
    sendStatusMessage("TV " + state);
    
  } else {
    sendErrorMessage("Unknown device: " + device);
  }
}

void moveBlind(int position) {
  // Convierte porcentaje (0-100) a valor para servo (0-180)
  int servoValue = map(position, 0, 100, 0, 180);
  blindServo.write(servoValue);
  
  // Esperar a que el servo llegue a posición
  delay(500);
}

void sendIRCommand(unsigned long command) {
  // Envía comando IR
  irSender.sendNEC(command, 32);
}

void turnAllOff() {
  // Apagar todas las luces
  digitalWrite(PIN_LIGHT_MAIN, LOW);
  digitalWrite(PIN_LIGHT_SEC, LOW);
  digitalWrite(PIN_FAN, LOW);
  digitalWrite(PIN_TV_RELAY, LOW);
  
  // No movemos la persiana en apagado total
  
  // Actualizar estado
  currentState.lightMain = false;
  currentState.lightSec = false;
  currentState.fan = false;
  currentState.tv = false;
  
  sendStatusMessage("All devices turned off");
}

void checkDevices() {
  // Verificar estado físico de los dispositivos
  // Este es un ejemplo simple; en un sistema real verificaríamos
  // sensores de corriente, etc.
  
  // Indicador de actividad
  if (digitalRead(PIN_LIGHT_MAIN) == HIGH || 
      digitalRead(PIN_LIGHT_SEC) == HIGH ||
      digitalRead(PIN_FAN) == HIGH ||
      digitalRead(PIN_TV_RELAY) == HIGH) {
    digitalWrite(PIN_LED_STATUS, HIGH);
  } else {
    digitalWrite(PIN_LED_STATUS, LOW);
  }
}

void saveStateToEEPROM() {
  // Guardar estado en EEPROM
  // Simplificado: en una implementación real usaríamos
  // más validación y checksum
  EEPROM.put(eepromAddress, currentState);
  EEPROM.commit(); // Necesario en ESP para guardar cambios
}

void loadStateFromEEPROM() {
  // Cargar estado desde EEPROM
  EEPROM.get(eepromAddress, currentState);
  
  // Validar valores (prevenir errores de EEPROM no inicializada)
  if (currentState.blindPosition > 100) {
    // Valores por defecto si la EEPROM no está inicializada
    currentState.lightMain = false;
    currentState.lightSec = false;
    currentState.blindPosition = 50;
    currentState.fan = false;
    currentState.tv = false;
  }
}

void applyCurrentState() {
  // Aplicar el estado actual a los dispositivos físicos
  digitalWrite(PIN_LIGHT_MAIN, currentState.lightMain ? HIGH : LOW);
  digitalWrite(PIN_LIGHT_SEC, currentState.lightSec ? HIGH : LOW);
  digitalWrite(PIN_FAN, currentState.fan ? HIGH : LOW);
  digitalWrite(PIN_TV_RELAY, currentState.tv ? HIGH : LOW);
  
  moveBlind(currentState.blindPosition);
}

void blinkStatusLED(int times) {
  // Parpadear LED de estado
  for (int i = 0; i < times; i++) {
    digitalWrite(PIN_LED_STATUS, HIGH);
    delay(100);
    digitalWrite(PIN_LED_STATUS, LOW);
    delay(100);
  }
}

void resetESP() {
  sendStatusMessage("Resetting ESP...");
  delay(100);
  ESP.reset(); // Método específico de ESP para reiniciar
}

// Funciones para enviar respuestas formateadas en JSON
void sendStatusUpdate() {
  DynamicJsonDocument doc(512);
  doc["status"] = "ok";
  doc["timestamp"] = millis();
  
  JsonObject devices = doc.createNestedObject("devices");
  devices["light_main"] = currentState.lightMain ? "on" : "off";
  devices["light_sec"] = currentState.lightSec ? "on" : "off";
  devices["blind"] = currentState.blindPosition;
  devices["fan"] = currentState.fan ? "on" : "off";
  devices["tv"] = currentState.tv ? "on" : "off";
  
  serializeJson(doc, Serial);
  Serial.println();
}

void sendStatusMessage(String message) {
  DynamicJsonDocument doc(256);
  doc["status"] = "ok";
  doc["message"] = message;
  doc["timestamp"] = millis();
  
  serializeJson(doc, Serial);
  Serial.println();
}

void sendErrorMessage(String errorMessage) {
  DynamicJsonDocument doc(256);
  doc["error"] = errorMessage;
  doc["timestamp"] = millis();
  
  serializeJson(doc, Serial);
  Serial.println();
}

// Actualizar estado para la interfaz web
void updateDeviceState() {
  deviceState["devices"]["light_main"] = currentState.lightMain ? "on" : "off";
  deviceState["devices"]["light_sec"] = currentState.lightSec ? "on" : "off";
  deviceState["devices"]["blind"] = currentState.blindPosition;
  deviceState["devices"]["fan"] = currentState.fan ? "on" : "off";
  deviceState["devices"]["tv"] = currentState.tv ? "on" : "off";
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
    
    if (command != "") {
      // Comando global (e.g., all_off)
      if (command == "all_off") {
        turnAllOff();
        saveStateToEEPROM();
        updateDeviceState();
      }
    } else if (device != "" && state != "") {
      // Control de dispositivo específico
      setDeviceState(device, state);
      saveStateToEEPROM();
      updateDeviceState();
    } else {
      server.send(400, "text/plain", "Parámetros inválidos");
      return;
    }
    
    // Redireccionar a la página principal
    server.sendHeader("Location", "/", true);
    server.send(302, "text/plain", "");
  });
  
  // Endpoint para refrescar estado
  server.on("/refresh", HTTP_GET, []() {
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
  
  // Añadir nuevo endpoint para API de comandos
  server.on("/command", HTTP_POST, []() {
    String postBody = server.arg("plain");
    DynamicJsonDocument doc(512);
    DeserializationError error = deserializeJson(doc, postBody);
    
    if (error) {
      DynamicJsonDocument errorResponse(256);
      errorResponse["error"] = "Invalid JSON";
      String jsonResponse;
      serializeJson(errorResponse, jsonResponse);
      server.send(400, "application/json", jsonResponse);
      return;
    }
    
    // Actualizar tiempo de último comando
    lastCommandTime = millis();
    if (emergencyMode) {
      emergencyMode = false;
    }
    
    // Procesar comando
    String cmd = doc["cmd"].as<String>();
    
    DynamicJsonDocument response(512);
    response["status"] = "ok";
    response["timestamp"] = millis();
    
    if (cmd == "set") {
      // Comando para controlar un dispositivo
      String device = doc["params"]["device"].as<String>();
      String state = doc["params"]["state"].as<String>();
      
      setDeviceState(device, state);
      saveStateToEEPROM();
      updateDeviceState();
      
    } else if (cmd == "get" || cmd == "status") {
      // Comando para obtener estado
      JsonObject devices = response.createNestedObject("devices");
      devices["light_main"] = currentState.lightMain ? "on" : "off";
      devices["light_sec"] = currentState.lightSec ? "on" : "off";
      devices["blind"] = currentState.blindPosition;
      devices["fan"] = currentState.fan ? "on" : "off";
      devices["tv"] = currentState.tv ? "on" : "off";
      
    } else if (cmd == "all_off") {
      // Apagar todos los dispositivos
      turnAllOff();
      saveStateToEEPROM();
      updateDeviceState();
      
    } else if (cmd == "reset") {
      // Reiniciar ESP
      response["message"] = "Resetting ESP...";
      
    } else {
      // Comando desconocido
      response["status"] = "error";
      response["error"] = "Unknown command: " + cmd;
    }
    
    String jsonResponse;
    serializeJson(response, jsonResponse);
    server.send(200, "application/json", jsonResponse);
    
    // Si era un comando de reset, realizar reset después de enviar respuesta
    if (cmd == "reset") {
      delay(500);
      ESP.reset();
    }
  });
  
  // Manejar 404
  server.onNotFound([]() {
    server.send(404, "text/plain", "Página no encontrada");
  });
}

// Códigos IR para controlar TV (ejemplo)
#define TV_POWER 0xFFA25D
#define TV_VOLUME_UP 0xFF629D
#define TV_VOLUME_DOWN 0xFFE21D
#define TV_CHANNEL_UP 0xFF22DD
#define TV_CHANNEL_DOWN 0xFF02FD
