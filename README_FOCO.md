# BrainBulb - Control de Foco Amazon Basics con Ondas Cerebrales

Este proyecto permite controlar un foco inteligente Amazon Basics mediante ondas cerebrales capturadas con un dispositivo NeuroSky MindWave.

## Características Principales

- **Control mental del foco**: Encender, apagar y ajustar brillo
- **Patrones cerebrales**:
  - Alta concentración → Encender foco
  - Meditación profunda → Apagar foco
  - Triple parpadeo → Ajustar brillo
- **Interfaz gráfica**:
  - Visualización en tiempo real de señales cerebrales
  - Panel de control manual del foco
  - Monitorización de comandos detectados
- **Sistema de calibración** adaptable a cada usuario

## Requisitos

### Hardware
- Dispositivo NeuroSky MindWave Mobile o compatibles
- ESP8266 (NodeMCU o similar)
- Foco inteligente Amazon Basics compatible con Tuya/Smart Life
- Computadora con conexión a la misma red WiFi

### Software
- Python 3.6+: numpy, matplotlib, tkinter, requests
- Arduino IDE con soporte para ESP8266
- Bibliotecas Arduino: ESP8266WiFi, ArduinoJson, TuyaSmartDevice

## Configuración del Foco Amazon Basics

1. **Instalar foco y configurarlo con la aplicación Smart Life**:
   - Descargar la app Smart Life de la tienda de aplicaciones
   - Seguir instrucciones para agregar el foco a la red WiFi
   - Verificar que el foco funciona correctamente desde la app

2. **Obtener credenciales para la API**:
   - Instalar [Tuya Developer Console](https://iot.tuya.com/)
   - Registrar una cuenta y crear un nuevo proyecto
   - Añadir el dispositivo y anotar:
     - Device ID
     - Device Key/Secret
     - Device IP local (opcional, pero recomendado)

3. **Configurar las credenciales en el ESP8266**:
   - Abrir `BrainHomeController.ino`
   - Modificar las siguientes líneas con tus datos:
     ```cpp
     const char* deviceId = "TU_DEVICE_ID";     // ID del dispositivo 
     const char* deviceKey = "TU_DEVICE_KEY";   // Clave del dispositivo
     const char* deviceIp = "TU_DEVICE_IP";     // IP local del dispositivo
     ```

## Instalación

1. **Preparar el firmware ESP8266**:
   - Abrir `BrainHomeController.ino` en Arduino IDE
   - Instalar la biblioteca TuyaSmartDevice (buscarla en Herramientas > Administrar Bibliotecas)
   - Configurar red WiFi con tu SSID y contraseña
   - Cargar el firmware en el ESP8266

2. **Instalar dependencias Python**:
   ```
   pip install numpy matplotlib requests tk
   ```

3. **Conexión del MindWave**:
   - Emparejar el dispositivo MindWave con tu computadora
   - Instalar ThinkGear Connector (necesario para recibir datos)

4. **Ejecutar la aplicación**:
   ```
   python BrainHomeController.py
   ```

## Uso

1. **Iniciar la aplicación** y verificar conexiones:
   - ThinkGear debería conectarse automáticamente
   - La aplicación intentará conectarse al ESP8266
   
2. **Calibrar el sistema**:
   - Haz clic en "Calibrar Señales"
   - Sigue las instrucciones para establecer umbrales personalizados

3. **Control mental**:
   - Concentrarte intensamente para encender el foco
   - Meditar profundamente para apagar el foco
   - Parpadear tres veces rápidamente para ajustar el brillo

4. **Ajustes opcionales**:
   - Cambiar umbrales de detección en la pestaña Configuración
   - Definir nivel de brillo con el deslizador

## Solución de Problemas

### El ESP8266 no se conecta al foco
- Verifica que las credenciales del dispositivo Tuya sean correctas
- Asegúrate de que el foco esté encendido y conectado a la red WiFi
- Comprueba que el ESP8266 está en la misma red WiFi que el foco

### La aplicación no detecta comandos cerebrales
- Ajusta la posición del sensor MindWave en tu frente
- Verifica que el clip de la oreja está haciendo buen contacto
- Aumenta o disminuye los umbrales de detección

### La aplicación no se conecta al ESP8266
- Verifica la dirección IP del ESP8266 (se muestra en el Serial Monitor)
- Confirma que el ESP8266 y tu computadora están en la misma red WiFi

## Limitaciones del Sistema

Este sistema está optimizado específicamente para focos inteligentes Amazon Basics que utilizan la plataforma Tuya/Smart Life. Puede no funcionar correctamente con otras marcas o modelos de focos inteligentes sin modificaciones adicionales en el código.
