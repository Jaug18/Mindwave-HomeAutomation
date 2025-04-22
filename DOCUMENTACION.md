# Documentación BrainHomeController

## Índice
1. [Introducción](#introducción)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Componentes Principales](#componentes-principales)
4. [Requisitos del Sistema](#requisitos-del-sistema)
5. [Configuración Inicial](#configuración-inicial)
6. [Funcionamiento Detallado](#funcionamiento-detallado)
7. [Detección de Patrones Cerebrales](#detección-de-patrones-cerebrales)
8. [Comandos y Acciones](#comandos-y-acciones)
9. [Interfaz de Usuario](#interfaz-de-usuario)
10. [Calibración](#calibración)
11. [Comunicación con Dispositivos](#comunicación-con-dispositivos)
12. [Solución de Problemas](#solución-de-problemas)
13. [Personalización Avanzada](#personalización-avanzada)

## Introducción

BrainHomeController es un sistema de control domótico innovador que permite a los usuarios controlar dispositivos electrónicos del hogar mediante señales cerebrales. Utilizando un dispositivo de electroencefalografía (EEG) compatible con el protocolo ThinkGear, el sistema interpreta patrones de ondas cerebrales y los traduce en comandos para activar o desactivar dispositivos conectados a un controlador ESP8266.

Este sistema representa una interfaz cerebro-máquina (BMI) práctica para el hogar inteligente, permitiendo el control de luces, persianas, ventiladores y otros dispositivos sin necesidad de controles físicos o comandos de voz.

## Arquitectura del Sistema

El sistema BrainHomeController consta de tres componentes principales:

1. **Dispositivo ThinkGear/NeuroSky**: Captura las señales cerebrales mediante electrodos en contacto con la frente y el lóbulo de la oreja.

2. **Aplicación Python (BrainHomeController)**: Procesa las señales cerebrales, detecta patrones específicos, y envía comandos al controlador de dispositivos. También proporciona una interfaz gráfica para monitorización y configuración.

3. **Controlador ESP8266**: Recibe comandos del software y controla los dispositivos físicos mediante relés u otros actuadores.

La arquitectura sigue un patrón cliente-servidor donde:
- El ThinkGear Connector actúa como servidor de datos de ondas cerebrales
- La aplicación Python actúa como cliente de datos cerebrales y servidor de comandos
- El ESP8266 actúa como cliente de comandos y controlador de dispositivos

## Componentes Principales

### Clase ThinkGearClient

Gestiona la conexión con el ThinkGear Connector mediante socket TCP. Se encarga de:
- Conectar con el servidor ThinkGear (generalmente en localhost:13854)
- Recibir y procesar datos JSON de las ondas cerebrales
- Distribuir los datos procesados mediante handlers

### Clase BrainSignalProcessor

Analiza las señales cerebrales para detectar patrones que correspondan a comandos. Características:
- Mantiene buffers para diferentes tipos de señales (atención, meditación, parpadeo)
- Implementa algoritmos de detección de patrones específicos
- Calibración de umbrales para adaptarse a diferentes usuarios
- Genera comandos basados en patrones detectados

### Clase ESP8266Controller

Gestiona la comunicación con el microcontrolador ESP8266. Funciones:
- Establece conexión HTTP con el ESP8266
- Envía comandos para controlar dispositivos
- Recibe y procesa actualizaciones de estado
- Polling del estado de dispositivos para mantener la interfaz actualizada

### Clase BrainHomeApp

Proporciona la interfaz gráfica y coordina todo el sistema. Incluye:
- Configuración y gestión de la conexión con dispositivos
- Visualización gráfica de señales cerebrales en tiempo real
- Controles manuales para dispositivos
- Ajustes de configuración y calibración
- Registro de comandos detectados

## Requisitos del Sistema

### Hardware Necesario

- **Dispositivo de EEG**: Compatible con protocolo ThinkGear (como NeuroSky MindWave Mobile)
- **Ordenador**: Con sistema operativo Windows, macOS o Linux
- **ESP8266**: NodeMCU o cualquier placa basada en ESP8266
- **Dispositivos controlables**: Relés, luces, persianas, etc.
- **Conexión a red local**: Para comunicación entre componentes

### Software Necesario

- **Python 3.7+**: Con los siguientes paquetes:
  - numpy
  - matplotlib
  - tkinter
  - requests
  - socket
- **ThinkGear Connector**: Software que recibe datos del dispositivo EEG
- **Firmware ESP8266**: Con servidor web y API REST

## Configuración Inicial

### 1. Configuración del ESP8266

El ESP8266 debe estar programado con un firmware que:
- Cree un servidor web
- Implemente endpoints API para:
  - `/status`: Devuelve el estado actual de los dispositivos
  - `/command`: Recibe comandos para controlar dispositivos
- Se conecte a la red WiFi local
- Controle los pines conectados a relés u otros actuadores

### 2. Instalación del ThinkGear Connector

1. Descargar e instalar el ThinkGear Connector desde la web oficial de NeuroSky
2. Configurar el dispositivo EEG con el software según instrucciones del fabricante
3. Verificar que el ThinkGear Connector esté corriendo y escuchando en el puerto 13854

### 3. Configuración de la Aplicación Python

Al iniciar la aplicación por primera vez:
1. Configurar la dirección IP del ESP8266 en la pestaña "Configuración"
2. Configurar los parámetros de conexión del ThinkGear (normalmente localhost:13854)
3. Realizar una calibración inicial de señales para ajustar los umbrales

## Funcionamiento Detallado

### Flujo de Datos

1. **Captura de Señales**:
   - El dispositivo EEG captura señales cerebrales
   - Envía los datos procesados al ThinkGear Connector vía Bluetooth
   - ThinkGear Connector expone estos datos a través de un socket TCP

2. **Procesamiento de Señales**:
   - `ThinkGearClient` recibe datos JSON del socket
   - Extrae valores de atención, meditación y parpadeo
   - Envía estos valores a los handlers registrados
   - `BrainSignalProcessor` almacena los valores en buffers
   - Analiza continuamente los buffers para detectar patrones

3. **Generación de Comandos**:
   - Cuando se detecta un patrón, se genera un comando
   - El comando se coloca en una cola con timestamp
   - El bucle principal extrae comandos recientes de la cola

4. **Ejecución de Comandos**:
   - Para cada comando extraído, se mapea a una acción específica
   - Se envía una solicitud HTTP al ESP8266
   - El ESP8266 ejecuta la acción (encender/apagar dispositivo)
   - Se recibe confirmación y se actualiza la interfaz

## Detección de Patrones Cerebrales

### Tipos de Señales Monitorizadas

1. **Atención (0-100)**: Indica el nivel de concentración mental
2. **Meditación (0-100)**: Indica el nivel de relajación mental
3. **Parpadeo (0-255)**: Fuerza del parpadeo detectado

### Patrones Reconocidos

1. **Pico de Atención**: Incremento rápido y significativo del nivel de atención
   - Uso: Encender luz principal
   - Detección: Valor > umbral_atención durante al menos 2 segundos

2. **Pico de Meditación**: Nivel sostenido alto de meditación
   - Uso: Apagar luz principal
   - Detección: Valor > umbral_meditación durante al menos 2 segundos

3. **Triple Parpadeo**: Tres parpadeos consecutivos en corto tiempo
   - Uso: Apagar todos los dispositivos
   - Detección: 3+ valores > umbral_parpadeo en ventana de 10 muestras

## Comandos y Acciones

El sistema tiene predefinidos los siguientes comandos:

| Comando     | Patrón Cerebral          | Acción                              |
|-------------|--------------------------|------------------------------------|
| luz_on      | Pico de atención         | Enciende la luz principal           |
| luz_off     | Pico de meditación       | Apaga la luz principal              |
| todo_off    | Triple parpadeo          | Apaga todos los dispositivos        |

Estos comandos son enviados al ESP8266 como solicitudes HTTP POST a `/command` con un payload JSON que especifica el dispositivo y el estado deseado.

## Interfaz de Usuario

La interfaz gráfica está organizada en tres pestañas principales:

### 1. Pestaña de Control

- **Panel de Estado**: Muestra el estado de conexión con ThinkGear y ESP8266
- **Panel de Dispositivos**: Lista de dispositivos controlables con:
  - Nombre del dispositivo
  - Estado actual (Encendido/Apagado)
  - Botones de control manual
- **Comandos Detectados**: Historial de comandos mentales detectados
- **Botones de Control**: Calibración, actualización de estado, apagado general

### 2. Pestaña de Configuración

- **Umbrales de Detección**: Controles deslizantes para ajustar:
  - Umbral de atención (0-100)
  - Umbral de meditación (0-100)
  - Umbral de parpadeo (0-100)
- **Configuración de Conexión**: Campos para configurar:
  - IP y puerto del ESP8266
  - Host y puerto del ThinkGear
- **Perfiles y Mapeos**: (Implementación futura) Para personalizar comandos

### 3. Pestaña de Señales

- **Gráficos en Tiempo Real**: Tres gráficos que muestran:
  - Nivel de atención a lo largo del tiempo
  - Nivel de meditación a lo largo del tiempo
  - Fuerza de parpadeo a lo largo del tiempo
- Actualización cada segundo con datos de los buffers

## Calibración

El proceso de calibración ajusta los umbrales de detección a las características específicas del usuario:

1. **Etapa de Reposo** (15 segundos): 
   - El usuario permanece relajado
   - El sistema registra niveles base de señales

2. **Etapa de Concentración** (15 segundos):
   - El usuario se concentra intensamente
   - El sistema registra niveles máximos de atención

3. **Análisis Automático**:
   - Se calculan umbrales óptimos basados en:
     - Media y desviación estándar de señales
     - Diferencia entre estados de reposo y concentración
   - Se aplican factores de seguridad para evitar falsos positivos

## Comunicación con Dispositivos

### Comunicación con ThinkGear

La comunicación con ThinkGear se realiza mediante socket TCP:

1. Conexión al host:puerto configurado (por defecto 127.0.0.1:13854)
2. Envío de comando para activar salida en formato JSON
3. Lectura continua del socket para recibir datos en tiempo real
4. Decodificación de paquetes JSON con valores de señales cerebrales
5. Distribución de datos mediante handlers registrados

### Comunicación con ESP8266

La comunicación con ESP8266 se realiza mediante API REST sobre HTTP:

1. **Endpoint `/status` (GET)**:
   - Solicita el estado actual de todos los dispositivos
   - Recibe respuesta JSON con estados (on/off)
   - Actualiza la interfaz con el estado recibido

2. **Endpoint `/command` (POST)**:
   - Envía comando JSON con:
     - Tipo de comando (`cmd`)
     - Parámetros específicos (`params`)
     - Identificador y timestamp
   - Recibe confirmación o error
   - Actualiza estado en base a la respuesta

## Solución de Problemas

### Problemas de Conexión con ThinkGear

- **Síntoma**: Error "No se pudo conectar a ThinkGear"
  - **Solución**: Verificar que ThinkGear Connector esté ejecutándose
  - **Solución**: Comprobar que el dispositivo EEG esté emparejado y encendido
  - **Solución**: Verificar host y puerto en configuración

- **Síntoma**: Se conecta pero no recibe datos
  - **Solución**: Ajustar posición del sensor frontal
  - **Solución**: Verificar carga de batería del dispositivo EEG
  - **Solución**: Reiniciar ThinkGear Connector

### Problemas de Conexión con ESP8266

- **Síntoma**: Error "Error conectando con ESP8266"
  - **Solución**: Verificar que ESP8266 esté conectado a la red
  - **Solución**: Comprobar IP y puerto configurados
  - **Solución**: Verificar firewall no bloquee comunicación

- **Síntoma**: Comandos enviados no tienen efecto
  - **Solución**: Verificar cableado entre ESP8266 y dispositivos
  - **Solución**: Revisar logs del ESP8266
  - **Solución**: Comprobar formato de comandos

### Problemas de Detección de Patrones

- **Síntoma**: No se detectan comandos mentales
  - **Solución**: Realizar nueva calibración
  - **Solución**: Ajustar umbrales manualmente
  - **Solución**: Practicar técnicas de concentración/relajación

- **Síntoma**: Falsos positivos frecuentes
  - **Solución**: Aumentar umbrales de detección
  - **Solución**: Modificar algoritmos de detección
  - **Solución**: Usar entorno con menos distracciones

## Personalización Avanzada

### Añadir Nuevos Dispositivos

Para añadir nuevos dispositivos al sistema:

1. Configurar un nuevo pin en el ESP8266 y conexión física
2. Actualizar el firmware del ESP8266 para soportar el nuevo dispositivo
3. Añadir entrada en la lista `devices` en `_setup_control_panel`
4. Actualizar el mapeo de comandos en `_control_loop`

### Implementar Nuevos Patrones Cerebrales

Para añadir nuevos patrones detectables:

1. Estudiar características del patrón deseado 
2. Implementar algoritmo de detección en `_detect_patterns` de `BrainSignalProcessor`
3. Añadir nuevo patrón a `gesture_patterns` en el constructor
4. Actualizar el mapeo de comandos en `_control_loop`

### Integración con Otros Sistemas

El sistema puede expandirse para integrar con:

- **Plataformas domóticas**: HomeAssistant, OpenHAB
- **Asistentes de voz**: Combinación con comandos de voz
- **IA predictiva**: Para aprender patrones de usuario
- **Sistemas de notificación**: Para alertas y feedback

## Conclusión

BrainHomeController representa un avance en la interacción cerebro-máquina aplicada a la domótica. El sistema demuestra cómo las tecnologías de interfaz cerebral pueden integrarse en aplicaciones prácticas y cotidianas, ofreciendo nuevas posibilidades de control para personas con movilidad reducida o para quienes buscan una experiencia futurista en su hogar inteligente.

La arquitectura modular y flexible del sistema permite adaptaciones a diversas necesidades y escenarios, mientras que su interfaz gráfica facilita la configuración y monitorización sin conocimientos técnicos profundos.