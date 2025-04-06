#include <ArduinoJson.h>
#include <EEPROM.h>

// Definición de pines para dispositivos
#define PIN_LIGHT_MAIN 2
#define PIN_LIGHT_SEC 3
#define PIN_BLIND_UP 4
#define PIN_BLIND_DOWN 5
#define PIN_FAN 6
#define PIN_TV_RELAY 7
#define PIN_LED_STATUS 13

// Para servomotores (persiana)
#include <Servo.h>
Servo blindServo;

// Para control infrarrojo (TV, aire acondicionado)
#include <IRremote.h>
IRsend irSender;

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

// Buffer para recepción de comandos
String inputBuffer = "";
bool commandComplete = false;

void setup() {
  // Iniciar comunicación serial
  Serial.begin(115200);
  
  // Configurar pines
  pinMode(PIN_LIGHT_MAIN, OUTPUT);
  pinMode(PIN_LIGHT_SEC, OUTPUT);
  pinMode(PIN_FAN, OUTPUT);
  pinMode(PIN_TV_RELAY, OUTPUT);
  pinMode(PIN_LED_STATUS, OUTPUT);
  
  // Configurar servo
  blindServo.attach(PIN_BLIND_UP);
  
  // Inicializar estado desde EEPROM
  loadStateFromEEPROM();
  
  // Aplicar estado inicial
  applyCurrentState();
  
  // Indicar inicio exitoso
  blinkStatusLED(3);
  
  // Enviar estado inicial
  sendStatusUpdate();
}

void loop() {
  // Leer comandos seriales
  while (Serial.available() > 0) {
    char inChar = (char)Serial.read();
    inputBuffer += inChar;
    
    // Verificar finalización de comando (nueva línea)
    if (inChar == '\n') {
      commandComplete = true;
      break;
    }
  }
  
  // Procesar comando completo
  if (commandComplete) {
    processCommand(inputBuffer);
    inputBuffer = "";
    commandComplete = false;
  }
  
  // Verificar tiempo desde último comando (para modo de emergencia)
  unsigned long currentTime = millis();
  if (currentTime - lastCommandTime > 60000 && !emergencyMode) {  // 1 minuto
    // Entrar en modo de emergencia si no hay comunicación
    emergencyMode = true;
    sendErrorMessage("No communication for 60 seconds. Entering emergency mode.");
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
    sendStatusUpdate();
    
  } else if (cmd == "get") {
    // Comando para obtener estado
    sendStatusUpdate();
    
  } else if (cmd == "all_off") {
    // Apagar todos los dispositivos
    turnAllOff();
    saveStateToEEPROM();
    sendStatusUpdate();
    
  } else if (cmd == "status") {
    // Enviar estado actual
    sendStatusUpdate();
    
  } else if (cmd == "reset") {
    // Reiniciar Arduino
    resetArduino();
    
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
  // Envía comando IR (simplificado)
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

void resetArduino() {
  sendStatusMessage("Resetting Arduino...");
  delay(100);
  asm volatile ("jmp 0");  // Saltar al vector de reset
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

// Códigos IR para controlar TV (ejemplo)
#define TV_POWER 0xFFA25D
#define TV_VOLUME_UP 0xFF629D
#define TV_VOLUME_DOWN 0xFFE21D
#define TV_CHANNEL_UP 0xFF22DD
#define TV_CHANNEL_DOWN 0xFF02FD