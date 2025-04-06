# Guía Completa del Sistema BrainHome

## Índice

1. [Introducción](#introducción)
2. [Componentes Necesarios](#componentes-necesarios)
3. [Preparación del Entorno](#preparación-del-entorno)
4. [Instalación del Software](#instalación-del-software)
5. [Configuración del Hardware](#configuración-del-hardware)
6. [Configuración del Software](#configuración-del-software)
7. [Conectando el Sistema](#conectando-el-sistema)
8. [Uso del Sistema](#uso-del-sistema)
9. [Personalización](#personalización)
10. [Solución de Problemas](#solución-de-problemas)
11. [Referencias](#referencias)

## Introducción

BrainHome es un sistema domótico controlado por ondas cerebrales que permite manipular dispositivos del hogar mediante señales captadas por un dispositivo Neurosky MindWave. El sistema está compuesto por tres componentes principales:

1. **Aplicación Python (BrainHomeController.py)**: Interpreta las señales cerebrales y envía comandos.
2. **Arduino Principal (BrainHomeHub.ino)**: Controla físicamente los dispositivos del hogar.
3. **Extensión WiFi (BrainHomeWifi.ino)**: Proporciona una interfaz web para el control remoto.

## Componentes Necesarios

### Hardware

- **Neurosky MindWave Mobile**: Dispositivo EEG para captar señales cerebrales
- **Arduino Uno/Mega**: Para el hub principal de control
- **ESP8266 (NodeMCU)**: Para la extensión WiFi
- **Relés (5V)**: Mínimo 4 canales para controlar dispositivos
- **Servomotor**: Para controlar persianas
- **LED IR y receptor**: Para control de TV/AC
- **Cables Dupont**: Para conexiones
- **Protoboard**: Para montaje de prueba
- **Adaptador 5V**: Para alimentación
- **Dispositivos de prueba**: Luces, ventilador, etc.

### Software

- **Python 3.6+**: Para ejecutar la aplicación principal
- **Arduino IDE**: Para programar Arduino y ESP8266
- **Editor de texto**: VSCode, Sublime, etc.
- **Terminal/CMD**: Para ejecutar comandos

## Preparación del Entorno

### Instalación de Python

1. Descarga Python desde [python.org](https://www.python.org/downloads/)
2. Ejecuta el instalador y marca la casilla "Add Python to PATH"
3. Verifica la instalación abriendo una terminal y ejecutando:
   ```
   python --version
   ```
   o
   ```
   python3 --version
   ```

### Instalación de Arduino IDE

1. Descarga Arduino IDE desde [arduino.cc](https://www.arduino.cc/en/software)
2. Instala siguiendo las instrucciones para tu sistema operativo
3. Abre Arduino IDE y configura el directorio de sketches

### Configuración del Entorno para ESP8266

1. Abre Arduino IDE
2. Ve a Archivo > Preferencias
3. En "URLs Adicionales de Gestor de Tarjetas", añade:
   ```
   http://arduino.esp8266.com/stable/package_esp8266com_index.json
   ```
4. Acepta y cierra Preferencias
5. Ve a Herramientas > Placa > Gestor de tarjetas
6. Busca "ESP8266" e instala el paquete

## Instalación del Software

### Clonar el Repositorio

1. Abre una terminal
2. Navega al directorio donde quieres guardar el proyecto
3. Ejecuta:
   ```
   git clone https://github.com/usuario/python-mindwave.git
   cd python-mindwave
   ```

### Instalación de Dependencias Python

1. Crea un entorno virtual (recomendado):
   ```
   python -m venv venv
   ```

2. Activa el entorno virtual:
   - Windows:
     ```
     venv\Scripts\activate
     ```
   - macOS/Linux:
     ```
     source venv/bin/activate
     ```

3. Instala las dependencias:
   ```
   pip install numpy matplotlib tkinter pyserial pybluez
   ```

   Nota: En algunos sistemas, puede ser necesario instalar tkinter por separado.
   - Ubuntu/Debian:
     ```
     sudo apt-get install python3-tk
     ```
   - macOS:
     ```
     brew install python-tk
     ```

### Instalación de Librerías Arduino

1. Abre Arduino IDE
2. Ve a Herramientas > Administrar Bibliotecas
3. Busca e instala las siguientes librerías:
   - ArduinoJson (versión 6.x)
   - IRremote
   - Servo

## Configuración del Hardware

### Conexión del Arduino Principal

1. **Conexiones de pines Arduino**:
   - Pin 2: Luz Principal (relé 1)
   - Pin 3: Luz Secundaria (relé 2)
   - Pin 4: Control Persiana Subir
   - Pin 5: Control Persiana Bajar
   - Pin 6: Ventilador (relé 3)
   - Pin 7: TV (relé 4)
   - Pin 13: LED de estado

2. **Montaje de relés**:
   - Conecta VCC del módulo relé a 5V del Arduino
   - Conecta GND del módulo relé a GND del Arduino
   - Conecta IN1 al pin 2, IN2 al pin 3, etc.

3. **Montaje del servomotor**:
   - Conecta el cable rojo a 5V
   - Conecta el cable negro/marrón a GND
   - Conecta el cable de señal (amarillo/naranja) al pin 4

4. **Emisor IR**:
   - Conecta el ánodo a través de una resistencia de 220Ω al pin 9
   - Conecta el cátodo a GND

### Conexión del ESP8266

1. **Conexiones ESP8266**:
   - D2 (GPIO4): RX (conectar al TX del Arduino)
   - D3 (GPIO0): TX (conectar al RX del Arduino)
   - Necesitarás un divisor de voltaje para la conexión TX->RX ya que el ESP trabaja a 3.3V

2. **Divisor de voltaje simple**:
   - Usa dos resistencias (e.j. 1kΩ y 2kΩ) para bajar el voltaje de 5V a 3.3V
   - Arduino TX -> resistencia 1kΩ -> ESP8266 RX -> resistencia 2kΩ -> GND

### Configuración del Dispositivo MindWave

1. Carga las baterías del dispositivo MindWave
2. Empareja el dispositivo con tu computadora:
   - Activa el Bluetooth de tu computadora
   - Enciende el MindWave manteniendo presionado el botón de encendido
   - El LED debe parpadear en azul
   - Busca dispositivos Bluetooth en tu computadora
   - Empareja con "MindWave Mobile" (la contraseña suele ser 0000)

3. Encuentra el puerto serial asignado:
   - Windows: Busca en Administrador de dispositivos > Puertos COM
   - macOS: Ejecuta `ls /dev/tty.*` en Terminal
   - Linux: Ejecuta `ls /dev/rfcomm*` o `ls /dev/ttyUSB*` en Terminal

## Configuración del Software

### Configuración del Código Arduino Principal

1. Abre Arduino IDE
2. Abre el archivo `BrainHomeHub.ino`
3. Modifica las siguientes líneas si necesitas cambiar los pines:
   ```cpp
   #define PIN_LIGHT_MAIN 2
   #define PIN_LIGHT_SEC 3
   #define PIN_BLIND_UP 4
   #define PIN_BLIND_DOWN 5
   #define PIN_FAN 6
   #define PIN_TV_RELAY 7
   ```

4. Si usas un control remoto IR diferente, modifica los códigos IR al final del archivo:
   ```cpp
   #define TV_POWER 0xFFA25D
   #define TV_VOLUME_UP 0xFF629D
   // ... etc.
   ```

5. Selecciona la placa correcta:
   - Herramientas > Placa > Arduino Uno/Mega

6. Selecciona el puerto correcto:
   - Herramientas > Puerto > [Puerto de tu Arduino]

7. Sube el código:
   - Sketch > Subir

### Configuración del ESP8266

1. Abre Arduino IDE
2. Abre el archivo `BrainHomeWifi.ino`
3. Modifica la configuración WiFi:
   ```cpp
   const char* ssid = "TuRedWiFi";
   const char* password = "TuContraseña";
   ```

4. Si has cambiado los pines de comunicación serial, actualiza:
   ```cpp
   SoftwareSerial arduinoSerial(D2, D3); // RX, TX
   ```

5. Selecciona la placa correcta:
   - Herramientas > Placa > ESP8266 > NodeMCU 1.0

6. Selecciona el puerto correcto:
   - Herramientas > Puerto > [Puerto de tu ESP8266]

7. Sube el código:
   - Sketch > Subir

### Configuración de la Aplicación Python

1. Abre el archivo `BrainHomeController.py` en un editor de texto
2. Localiza la función `connect_mindwave()` y modifica el puerto:
   ```python
   self.mindwave = Headset('/dev/tu_puerto_mindwave')
   ```
   Reemplaza '/dev/tu_puerto_mindwave' con el puerto correcto para tu dispositivo.

3. Si has modificado la dirección IP del ESP8266, actualiza las referencias en el código.

## Conectando el Sistema

### Paso 1: Verificación del Hardware

1. Asegúrate de que Arduino esté conectado y programado
2. Verifica que ESP8266 esté conectado y programado
3. Comprueba que MindWave esté emparejado y encendido

### Paso 2: Iniciar la Aplicación Python

1. Abre una terminal en el directorio del proyecto
2. Activa el entorno virtual si lo utilizas
3. Ejecuta la aplicación:
   ```
   python BrainHomeController.py
   ```

4. Verifica que la interfaz gráfica se inicie correctamente

### Paso 3: Verificar la Conexión Web

1. Con el ESP8266 conectado y programado, anota la dirección IP que aparece en el monitor serie
2. Abre un navegador web y navega a esa dirección IP
3. Deberías ver la interfaz web del sistema BrainHome

## Uso del Sistema

### Interfaz de Python

La interfaz de la aplicación Python tiene tres pestañas principales:

1. **Control**: 
   - Muestra el estado de los dispositivos
   - Permite control manual a través de botones
   - Muestra los comandos mentales detectados

2. **Configuración**:
   - Ajusta los umbrales de detección para señales cerebrales
   - Configura los puertos de conexión
   - Define perfiles y mapeos de comandos

3. **Señales**:
   - Visualiza en tiempo real las señales cerebrales
   - Muestra gráficos de atención, meditación y parpadeos

### Colocación del Dispositivo MindWave

1. Coloca el dispositivo MindWave en tu cabeza
   - La banda debe estar en la frente
   - El sensor debe tocar la piel en la frente
   - El clip debe estar en el lóbulo de la oreja

2. Verifica la calidad de la señal:
   - Luz verde: Buena señal
   - Luz roja: Mala señal (reajusta el dispositivo)

### Calibración del Sistema

1. Antes de usar, realiza una calibración:
   - Haz clic en el botón "Calibrar Señales"
   - Sigue las instrucciones en pantalla
   - Relájate primero, luego ejecuta las acciones solicitadas

2. La calibración ajusta los umbrales para tus señales particulares

### Control Mental

Para controlar dispositivos con la mente:

1. **Encender luz principal**:
   - Concéntrate intensamente por 2-3 segundos
   - Deberías ver un pico en el gráfico de "Atención"

2. **Apagar todo**:
   - Parpadea rápidamente 3 veces
   - El sistema detectará esta secuencia como comando de apagado

3. **Otros comandos**:
   - Varían según la configuración establecida
   - Puedes personalizarlos en la pestaña de Configuración

### Interfaz Web

La interfaz web permite:

1. Control de todos los dispositivos de forma remota
2. Visualización del estado actual
3. Ejecución de comandos globales como "Apagar Todo"

## Personalización

### Añadir Nuevos Dispositivos

Para añadir un nuevo dispositivo:

1. **En Arduino**:
   - Define un nuevo pin en `BrainHomeHub.ino`:
     ```cpp
     #define PIN_NEW_DEVICE 8
     ```
   - Añade el dispositivo a la estructura DeviceState:
     ```cpp
     struct DeviceState {
       // ... dispositivos existentes
       bool newDevice;
     };
     ```
   - Actualiza las funciones setDeviceState, sendStatusUpdate, etc.

2. **En ESP8266**:
   - Añade el nuevo dispositivo a la interfaz web en setupWebServer()

3. **En Python**:
   - Añade el dispositivo a la lista de dispositivos en _setup_control_panel()

### Personalizar Patrones Cerebrales

Para modificar los patrones de detección:

1. Edita la función `_detect_patterns()` en la clase BrainSignalProcessor
2. Modifica los umbrales y algoritmos según tus necesidades
3. Añade nuevos patrones al diccionario gesture_patterns

## Solución de Problemas

### Problemas de Conexión MindWave

- **Problema**: No se detecta el dispositivo MindWave
  - **Solución**: Verifica que esté emparejado y el puerto sea correcto
  - Ejecuta `ls /dev/tty.*` (macOS) o `mode` (Windows) para ver puertos disponibles

- **Problema**: Señal pobre o intermitente
  - **Solución**: Recoloca el dispositivo, asegura buen contacto de la pinza en la oreja
  - Cambia las baterías si están bajas

### Problemas de Arduino

- **Problema**: Error al subir código
  - **Solución**: Verifica que la placa y puerto seleccionados sean correctos
  - Presiona el botón de reset en Arduino justo antes de subir

- **Problema**: Dispositivos no responden
  - **Solución**: Verifica conexiones físicas y que los pines correspondan con el código
  - Utiliza la función de diagnóstico LED para depurar

### Problemas de ESP8266

- **Problema**: No se conecta a WiFi
  - **Solución**: Verifica credenciales WiFi en el código
  - Asegúrate que la red sea 2.4 GHz (no compatible con 5 GHz)

- **Problema**: Interfaz web inaccesible
  - **Solución**: Verifica la IP mostrada en el monitor serial
  - Comprueba que el router permita conexiones entre dispositivos

### Problemas de Software Python

- **Problema**: Error al iniciar aplicación
  - **Solución**: Verifica que todas las dependencias estén instaladas
  - Activa el entorno virtual si lo estás utilizando

- **Problema**: No se detectan comandos mentales
  - **Solución**: Ejecuta la calibración nuevamente
  - Ajusta los umbrales en la pestaña de configuración

## Referencias

- [Documentación de Neurosky MindWave](https://neurosky.com/biosensors/eeg-sensor/)
- [Documentación de Arduino](https://www.arduino.cc/reference/en/)
- [Documentación de ESP8266](https://arduino-esp8266.readthedocs.io/)
- [Matplotlib para visualizaciones](https://matplotlib.org/)
- [ArduinoJson](https://arduinojson.org/)
- [Tkinter para interfaces gráficas](https://docs.python.org/3/library/tkinter.html)
