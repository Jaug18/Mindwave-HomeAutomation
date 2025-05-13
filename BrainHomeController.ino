#include <ESP8266WiFi.h>
#include <WiFiClient.h>
#include <ESP8266WebServer.h>
#include <ArduinoJson.h>
#include <EEPROM.h>
#include <TuyaSmartDevice.h>  // Biblioteca para comunicarse con dispositivos Tuya

// ======== CONFIGURACIÓN BÁSICA ========
// Configuración WiFi - MODIFICAR CON TUS DATOS
const char* ssid = "TuRedWiFi";      // Nombre de la red WiFi
const char* password = "TuContraseña"; // Contraseña de la red WiFi

// Configuración del foco Amazon Basics (Smart Life/Tuya) - MODIFICAR CON TUS DATOS
const char* deviceId = "TU_DEVICE_ID";     // ID del dispositivo (desde Tuya Developer Console)
const char* deviceKey = "TU_DEVICE_KEY";   // Clave del dispositivo (desde Tuya Developer Console)
const char* deviceIp = "TU_DEVICE_IP";     // IP local del dispositivo (opcional, pero recomendado)

// Servidor web en puerto 80
ESP8266WebServer server(80);

// ======== PINES Y CONSTANTES ========
#define PIN_LED_STATUS D0     // GPIO16 - LED para indicar estado
#define RECONNECT_INTERVAL 30000  // Intervalo para reintentar conexión en ms
#define EMERGENCY_TIMEOUT 60000   // Tiempo sin comandos para entrar en modo emergencia

// ======== VARIABLES GLOBALES ========
// Instancia del dispositivo Tuya
TuyaSmartDevice smartBulb(deviceId, deviceKey, deviceIp);

// Estado actual del foco
bool bulbState = false;        // Estado encendido/apagado
int bulbBrightness = 100;      // Nivel de brillo (1-100)
unsigned long lastCommandTime = 0;  // Tiempo del último comando recibido
bool emergencyMode = false;    // Modo de emergencia (si no hay comunicación)
unsigned long lastReconnectAttempt = 0; // Último intento de reconexión
unsigned long lastHeartbeat = 0;   // Último ping para verificar conexión
int reconnectCount = 0;       // Contador de intentos de reconexión

// Estado del sistema
DynamicJsonDocument deviceState(256);

// ======== CONFIGURACIÓN INICIAL ========
void setup() {
  // Iniciar puerto serie para depuración
  Serial.begin(115200);
  Serial.println("\n========= BrainHome Foco Controller =========");
  Serial.println("Iniciando sistema para control de foco inteligente...");
  
  // Configurar pin LED para indicaciones visuales
  pinMode(PIN_LED_STATUS, OUTPUT);
  digitalWrite(PIN_LED_STATUS, LOW);
  
  // Iniciar EEPROM y cargar último estado guardado
  EEPROM.begin(16);  // Solo necesitamos unos pocos bytes
  loadStateFromEEPROM();
  Serial.println("Estado anterior cargado desde EEPROM");
  
  // Configuración de WiFi
  setupWiFi();
  
  // Inicializar conexión con el foco
  initSmartBulb();
  
  // Aplicar estado inicial al foco
  applyCurrentState();
  
  // Indicar inicio exitoso mediante parpadeos del LED
  blinkStatusLED(3);
  
  // Configurar rutas del servidor web
  setupWebServer();
  
  // Iniciar servidor HTTP
  server.begin();
  Serial.println("Servidor HTTP iniciado en puerto 80");
  Serial.print("Accede a la interfaz web en http://");
  Serial.print(WiFi.localIP());
  Serial.println("/");
  
  // Actualizar y enviar estado inicial
  updateDeviceState();
  sendStatusUpdate();
  
  Serial.println("Inicialización completada. Esperando comandos...");
}

// ======== BUCLE PRINCIPAL ========
void loop() {
  // Manejar clientes web
  server.handleClient();
  
  // Comprobar conexión con el foco
  smartBulb.loop();
  
  // Verificar conexión WiFi y reconectar si es necesario
  checkWiFiConnection();
  
  // Enviar ping/heartbeat periódico para verificar conexión
  sendHeartbeat();
  
  // Verificar tiempo desde último comando para gestión de emergencia
  checkEmergencyMode();
  
  // Pequeña pausa para estabilidad
  delay(50);
}

// ======== FUNCIONES DE CONFIGURACIÓN ========

// Configura y conecta a la red WiFi
void setupWiFi() {
  Serial.print("Conectando a WiFi: ");
  Serial.print(ssid);
  
  // Configuración adicional de WiFi para mejor estabilidad
  WiFi.persistent(true);
  WiFi.mode(WIFI_STA);
  
  // Iniciar conexión WiFi
  WiFi.begin(ssid, password);
  
  // Esperar conexión con indicador visual
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    digitalWrite(PIN_LED_STATUS, !digitalRead(PIN_LED_STATUS)); // Parpadear durante conexión
    attempts++;
  }
  
  // Verificar si se conectó
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("");
    Serial.print("Conectado a WiFi, IP: ");
    Serial.println(WiFi.localIP());
    digitalWrite(PIN_LED_STATUS, HIGH); // LED encendido indica conexión exitosa
  } else {
    Serial.println("");
    Serial.println("Error al conectar a WiFi. Reiniciando...");
    blinkStatusLED(5); // Indicar error
    ESP.restart(); // Reiniciar ESP8266 para intentar nuevamente
  }
}

// Inicializa la conexión con el foco inteligente
void initSmartBulb() {
  Serial.println("Iniciando conexión con el foco inteligente...");
  
  // Iniciar conexión con el dispositivo Tuya
  smartBulb.begin();
  
  // Verificar si se puede comunicar con el dispositivo
  if (!smartBulb.isConnected()) {
    Serial.println("Advertencia: No se pudo conectar con el foco. Verificar credenciales.");
    blinkStatusLED(2); // Indicación visual de advertencia
  } else {
    Serial.println("Conexión con foco establecida correctamente");
  }
}

// ======== FUNCIONES DE MONITOREO ========

// Verifica y mantiene la conexión WiFi
void checkWiFiConnection() {
  unsigned long currentMillis = millis();
  
  // Intentar reconectar si se perdió la conexión
  if (WiFi.status() != WL_CONNECTED) {
    digitalWrite(PIN_LED_STATUS, LOW); // Apagar LED
    
    // Limitar los intentos de reconexión para no saturar
    if (currentMillis - lastReconnectAttempt > RECONNECT_INTERVAL) {
      lastReconnectAttempt = currentMillis;
      reconnectCount++;
      
      Serial.print("Conexión WiFi perdida. Intento de reconexión #");
      Serial.println(reconnectCount);
      
      // Reiniciar WiFi si hay muchos intentos fallidos
      if (reconnectCount > 5) {
        Serial.println("Múltiples fallos de conexión. Reiniciando ESP8266...");
        ESP.restart();
      }
      
      // Intentar reconectar
      WiFi.reconnect();
    }
  } else {
    // Si estamos conectados, resetear contador de reconexiones
    reconnectCount = 0;
  }
}

// Envía un heartbeat periódico para verificar conexión
void sendHeartbeat() {
  // Enviar ping cada 30 segundos para verificar conexión
  if (millis() - lastHeartbeat > 30000) {
    lastHeartbeat = millis();
    
    // Verificar si el foco responde
    if (smartBulb.isConnected()) {
      Serial.println("Heartbeat: Conexión con foco OK");
    } else {
      Serial.println("Heartbeat: Foco no responde");
    }
    
    // También indicamos que seguimos vivos
    digitalWrite(PIN_LED_STATUS, !digitalRead(PIN_LED_STATUS));
    digitalWrite(PIN_LED_STATUS, !digitalRead(PIN_LED_STATUS));
  }
}

// Verifica si entrar en modo emergencia por falta de comunicación
void checkEmergencyMode() {
  unsigned long currentTime = millis();
  if (currentTime - lastCommandTime > EMERGENCY_TIMEOUT && !emergencyMode) {
    emergencyMode = true;
    Serial.println("ALERTA: Entrando en modo emergencia por falta de comunicación");
    
    // En modo emergencia podríamos establecer un estado predeterminado seguro
    // Por ejemplo, luz al 50% para asegurar visibilidad
    if (bulbState) {
      smartBulb.setBrightness(50);
      Serial.println("Modo emergencia: Ajustando brillo al 50%");
    }
    
    // Indicación visual de modo emergencia
    blinkStatusLED(4);
  }
}

// ======== FUNCIONES DE PROCESAMIENTO DE COMANDOS ========

// Procesa un comando recibido en formato JSON
void processCommand(String command) {
  // Actualizar tiempo de último comando
  lastCommandTime = millis();
  
  // Salir de modo emergencia si estábamos en él
  if (emergencyMode) {
    emergencyMode = false;
    sendStatusMessage("Modo emergencia desactivado");
  }
  
  // Analizar JSON
  DynamicJsonDocument doc(256);
  DeserializationError error = deserializeJson(doc, command);
  
  // Verificar si el formato JSON es válido
  if (error) {
    sendErrorMessage("Comando JSON inválido: " + String(error.c_str()));
    return;
  }
  
  // Registrar comando recibido
  Serial.print("Comando recibido: ");
  serializeJson(doc, Serial);
  Serial.println();
  
  // Extraer comando principal
  String cmd = doc["cmd"].as<String>();
  
  // Procesar según el tipo de comando
  if (cmd == "set") {
    // Control del foco
    String state = doc["params"]["state"].as<String>();
    int brightness = doc["params"]["brightness"] | -1;
    
    // Aplicar cambios al foco
    setBulbState(state, brightness);
    
    // Guardar estado en memoria persistente
    saveStateToEEPROM();
    
    // Actualizar estado actual
    updateDeviceState();
    
    // Enviar confirmación
    sendStatusUpdate();
    
  } else if (cmd == "get" || cmd == "status") {
    // Enviar estado actual
    sendStatusUpdate();
    
  } else if (cmd == "restart") {
    // Comando para reiniciar el ESP8266
    sendStatusMessage("Reiniciando dispositivo...");
    delay(500);
    ESP.restart();
    
  } else {
    // Comando desconocido
    sendErrorMessage("Comando desconocido: " + cmd);
  }
}

// Establece el estado del foco (encendido/apagado y brillo)
void setBulbState(String state, int brightness) {
  bool stateOn = (state == "on");
  
  if (stateOn) {
    if (brightness >= 0 && brightness <= 100) {
      // Encender con brillo específico
      Serial.print("Encendiendo foco con brillo: ");
      Serial.println(brightness);
      smartBulb.setBrightness(brightness);
      bulbBrightness = brightness;
    } else {
      // Encender con último brillo utilizado
      Serial.print("Encendiendo foco con último brillo: ");
      Serial.println(bulbBrightness);
      smartBulb.turnOn();
    }
    bulbState = true;
    sendStatusMessage("Foco encendido");
  } else {
    // Apagar foco
    Serial.println("Apagando foco");
    smartBulb.turnOff();
    bulbState = false;
    sendStatusMessage("Foco apagado");
  }
  
  // Indicación visual de cambio
  digitalWrite(PIN_LED_STATUS, bulbState ? HIGH : LOW);
}

// ======== FUNCIONES DE GESTIÓN DE ESTADO ========

// Guarda el estado actual en EEPROM
void saveStateToEEPROM() {
  // Guardar estado de encendido/apagado y nivel de brillo
  EEPROM.write(0, bulbState ? 1 : 0);
  EEPROM.write(1, bulbBrightness);
  
  // Confirmación física de escritura
  EEPROM.commit();
  
  Serial.println("Estado guardado en EEPROM");
}

// Carga el estado desde EEPROM
void loadStateFromEEPROM() {
  // Leer valores de memoria
  bulbState = EEPROM.read(0) == 1;
  bulbBrightness = EEPROM.read(1);
  
  // Validar valores para evitar estados inválidos
  if (bulbBrightness > 100 || bulbBrightness < 1) {
    bulbBrightness = 100;  // Valor predeterminado
  }
  
  Serial.print("Estado cargado: ");
  Serial.print(bulbState ? "Encendido" : "Apagado");
  Serial.print(", Brillo: ");
  Serial.println(bulbBrightness);
}

// Aplica el estado cargado al foco
void applyCurrentState() {
  Serial.println("Aplicando estado inicial al foco...");
  
  // Aplicar según el estado almacenado
  if (bulbState) {
    smartBulb.setBrightness(bulbBrightness);
    Serial.print("Encendiendo con brillo: ");
    Serial.println(bulbBrightness);
  } else {
    smartBulb.turnOff();
    Serial.println("Manteniendo apagado");
  }
}

// Parpadea el LED de estado (útil para indicaciones visuales)
void blinkStatusLED(int times) {
  for (int i = 0; i < times; i++) {
    digitalWrite(PIN_LED_STATUS, HIGH);
    delay(100);
    digitalWrite(PIN_LED_STATUS, LOW);
    delay(100);
  }
}

// Actualiza el objeto JSON con el estado actual
void updateDeviceState() {
  deviceState["state"] = bulbState ? "on" : "off";
  deviceState["brightness"] = bulbBrightness;
  deviceState["wifi_strength"] = WiFi.RSSI(); // Nivel de señal WiFi
  deviceState["uptime"] = millis() / 1000;    // Tiempo desde inicio en segundos
}

// ======== FUNCIONES DE COMUNICACIÓN ========

// Envía el estado actual como respuesta JSON
void sendStatusUpdate() {
  DynamicJsonDocument doc(256);
  doc["status"] = "ok";
  doc["timestamp"] = millis();
  doc["state"] = bulbState ? "on" : "off";
  doc["brightness"] = bulbBrightness;
  doc["wifi_strength"] = WiFi.RSSI();
  doc["uptime"] = millis() / 1000;
  doc["emergency_mode"] = emergencyMode;
  
  String jsonResponse;
  serializeJson(doc, jsonResponse);
  
  // Enviar al cliente web
  server.send(200, "application/json", jsonResponse);
  
  // También mostrar en consola serial para depuración
  serializeJson(doc, Serial);
  Serial.println();
}

// Envía un mensaje de estado con nivel informativo
void sendStatusMessage(String message) {
  DynamicJsonDocument doc(256);
  doc["status"] = "ok";
  doc["message"] = message;
  doc["timestamp"] = millis();
  
  String jsonResponse;
  serializeJson(doc, jsonResponse);
  
  // Enviar como respuesta HTTP si hay una solicitud activa
  if (server.client()) {
    server.send(200, "application/json", jsonResponse);
  }
  
  // Siempre mostrar en consola serial
  serializeJson(doc, Serial);
  Serial.println();
}

// Envía un mensaje de error
void sendErrorMessage(String errorMessage) {
  DynamicJsonDocument doc(256);
  doc["status"] = "error";
  doc["error"] = errorMessage;
  doc["timestamp"] = millis();
  
  String jsonResponse;
  serializeJson(doc, jsonResponse);
  
  // Enviar como respuesta HTTP con código 400
  if (server.client()) {
    server.send(400, "application/json", jsonResponse);
  }
  
  // Mostrar en consola serial
  serializeJson(doc, Serial);
  Serial.println();
}

// ======== CONFIGURACIÓN DEL SERVIDOR WEB ========

// Configura todas las rutas del servidor web
void setupWebServer() {
  // Página principal (interfaz HTML)
  server.on("/", HTTP_GET, handleRoot);
  
  // Endpoint para control del foco vía web
  server.on("/control", HTTP_GET, handleControl);
  
  // API para obtener estado actual
  server.on("/status", HTTP_GET, []() {
    sendStatusUpdate();
  });
  
  // API para enviar comandos (vía POST)
  server.on("/command", HTTP_POST, []() {
    String postBody = server.arg("plain");
    processCommand(postBody);
  });
  
  // Endpoint para reiniciar el dispositivo
  server.on("/restart", HTTP_GET, []() {
    sendStatusMessage("Reiniciando dispositivo...");
    delay(500);
    ESP.restart();
  });
  
  // Manejo de 404 (página no encontrada)
  server.onNotFound([]() {
    server.send(404, "text/plain", "Página no encontrada");
  });
}

// Manejador para la ruta principal (interfaz web)
void handleRoot() {
  String html = "<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'>";
  html += "<title>Control Foco Amazon Basics</title>";
  html += "<style>";
  html += "body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f0f0f0; }";
  html += ".container { max-width: 600px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }";
  html += "h1 { color: #3498db; text-align: center; }";
  html += ".device { margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 8px; }";
  html += ".device-title { font-weight: bold; margin-bottom: 10px; }";
  html += ".button { display: inline-block; padding: 10px 20px; background-color: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer; margin-right: 10px; text-decoration: none; }";
  html += ".button.off { background-color: #e74c3c; }";
  html += ".status { display: inline-block; padding: 5px 10px; border-radius: 15px; font-size: 14px; color: white; margin-left: 10px; }";
  html += ".status.on { background-color: #2ecc71; }";
  html += ".status.off { background-color: #e74c3c; }";
  html += ".slider { width: 100%; margin: 20px 0; }";
  html += ".info { margin-top: 20px; font-size: 12px; color: #666; }";
  html += "</style>";
  html += "</head><body>";
  html += "<div class='container'>";
  html += "<h1>Control Foco Amazon Basics</h1>";
  
  // Estado y controles del foco
  html += "<div class='device'>";
  html += "<div class='device-title'>Foco Inteligente</div>";
  html += "<span class='status " + String(bulbState ? "on" : "off") + "'>" + 
          String(bulbState ? "Encendido" : "Apagado") + "</span>";
  html += "<p>Brillo: " + String(bulbBrightness) + "%</p>";
  html += "<a href='/control?state=on' class='button'>Encender</a>";
  html += "<a href='/control?state=off' class='button off'>Apagar</a>";
  html += "<form action='/control' method='get'>";
  html += "<input type='range' name='brightness' min='1' max='100' value='" + String(bulbBrightness) + "' class='slider'>";
  html += "<input type='submit' value='Ajustar Brillo' class='button'>";
  html += "</form>";
  html += "</div>";
  
  // Información del sistema
  html += "<div class='info'>";
  html += "<p>Señal WiFi: " + String(WiFi.RSSI()) + " dBm</p>";
  html += "<p>IP: " + WiFi.localIP().toString() + "</p>";
  html += "<p>Tiempo encendido: " + String(millis() / 1000) + " segundos</p>";
  html += "<p>Versión: 1.0</p>";
  html += "</div>";
  
  html += "<p><a href='/restart' class='button' onclick='return confirm(\"¿Seguro que deseas reiniciar el dispositivo?\")'>Reiniciar dispositivo</a></p>";
  
  html += "</div>"; // fin container
  
  // Auto-refrescar cada 10 segundos
  html += "<script>setTimeout(function(){ location.reload(); }, 10000);</script>";
  
  html += "</body></html>";
  
  server.send(200, "text/html", html);
}

// Manejador para la ruta de control
void handleControl() {
  String state = server.arg("state");
  String brightnessStr = server.arg("brightness");
  int brightness = -1;
  
  // Si recibimos un valor de brillo, procesarlo
  if (brightnessStr != "") {
    brightness = brightnessStr.toInt();
    if (brightness > 0) {
      bulbBrightness = brightness;
      smartBulb.setBrightness(brightness);
      bulbState = true;
    }
  }
  
  // Si recibimos un comando de encendido/apagado, procesarlo
  if (state == "on") {
    setBulbState("on", -1);
  } else if (state == "off") {
    setBulbState("off", -1);
  }
  
  // Guardar cambios en memoria no volátil
  saveStateToEEPROM();
  updateDeviceState();
  
  // Redireccionar a la página principal
  server.sendHeader("Location", "/", true);
  server.send(302, "text/plain", "");
}
