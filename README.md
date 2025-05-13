# Mindwave Home Automation

Controla dispositivos inteligentes (como focos Tuya/Amazon Basics) usando señales cerebrales capturadas por un Mindwave Mobile y una interfaz gráfica avanzada.

---

## Tabla de Contenidos

- [Descripción General](#descripción-general)
- [Características](#características)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Uso](#uso)
- [Calibración](#calibración)
- [Internacionalización](#internacionalización)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Notas y Consejos](#notas-y-consejos)
- [Licencia](#licencia)

---

## Descripción General

Este proyecto permite controlar un foco inteligente compatible con Tuya/Amazon Basics mediante ondas cerebrales, usando un Mindwave Mobile y un ESP8266. Incluye una interfaz gráfica (GUI) para visualizar señales, calibrar umbrales, ver logs y ajustar la configuración.

---

## Características

- **Control mental**: Enciende, apaga y ajusta el brillo del foco usando concentración, meditación o parpadeos detectados.
- **Interfaz gráfica avanzada**: Visualización en tiempo real de señales, logs, comandos detectados y estado del sistema.
- **Calibración personalizada**: Ajusta los umbrales de detección según tus propias señales cerebrales.
- **Internacionalización**: Soporte para español e inglés.
- **Reconexión automática**: El sistema intenta reconectar con los dispositivos si se pierde la conexión.
- **Persistencia**: Guarda la calibración y configuración para futuros usos.
- **Soporte para reproducción offline**: Simula señales usando archivos grabados.

---

## Requisitos

### Hardware

- [NeuroSky Mindwave Mobile](http://neurosky.com/)
- ESP8266 (NodeMCU, Wemos D1 mini, etc.)
- Foco inteligente compatible con Tuya/Smart Life/Amazon Basics

### Software

- Python 3.7+
- Arduino IDE (para cargar el firmware al ESP8266)
- Sistema operativo: Windows, Linux o macOS

### Dependencias Python

Instala con:

```bash
pip install numpy matplotlib requests pyserial
```

---

## Instalación

### 1. Firmware ESP8266

1. Abre `BrainHomeController.ino` en el Arduino IDE.
2. Configura tus credenciales WiFi y datos del dispositivo Tuya.
3. Sube el sketch al ESP8266.
4. El ESP8266 debe estar en la misma red que tu PC.

### 2. Interfaz Python

1. Clona este repositorio.
2. Instala las dependencias Python.
3. Conecta el Mindwave Mobile y asegúrate de que el ThinkGear Connector esté ejecutándose (puerto 13854 por defecto).
4. Ejecuta la interfaz:

```bash
python BrainHomeController.py
```

---

## Configuración

- **IP y puerto del ESP8266**: Configura en la pestaña "Configuración" de la GUI.
- **Host y puerto de ThinkGear**: Usualmente `127.0.0.1:13854`.
- **Umbrales de detección**: Ajusta los sliders para atención, meditación y parpadeo.
- **Idioma**: Cambia entre español e inglés desde la GUI.

---

## Uso

1. **Conecta el Mindwave Mobile** y asegúrate de que el ThinkGear Connector esté activo.
2. **Ejecuta la aplicación Python**.
3. **Verifica la conexión** con el ESP8266 y el Mindwave desde la GUI.
4. **Calibra tus señales** usando el botón "Calibrar Señales".
5. **Controla el foco**:
   - **Concentración alta**: Enciende el foco.
   - **Meditación profunda**: Apaga el foco.
   - **Triple parpadeo**: Ajusta el brillo al nivel seleccionado.
6. **Observa las señales y logs** en tiempo real.

---

## Calibración

- Pulsa "Calibrar Señales".
- Sigue las instrucciones: primero relájate, luego concéntrate.
- Los umbrales se ajustarán automáticamente y se guardarán para futuros usos.
- Puedes guardar la calibración manualmente desde la pestaña de configuración.

---

## Internacionalización

- Cambia el idioma desde la GUI.
- Reinicia la aplicación para aplicar el cambio.

---

## Estructura del Proyecto

```
Mindwave-HomeAutomation/
├── BrainHomeController.ino      # Firmware para ESP8266
├── BrainHomeController.py       # Interfaz gráfica y lógica principal
├── mindwave.py                  # Driver para Mindwave Mobile
├── calibration.json             # Archivo de calibración (autogenerado)
├── README.md                    # Este archivo
└── ...                          # Otros archivos y recursos
```

---

## Notas y Consejos

- **ThinkGear Connector**: Debe estar ejecutándose antes de iniciar la GUI.
- **Logs**: Consulta la pestaña/logs para ver errores y eventos.
- **Reconexión**: El sistema intenta reconectar automáticamente si se pierde la conexión.
- **Modo offline**: Usa `OfflineHeadset` en `mindwave.py` para pruebas con archivos grabados.
- **Seguridad**: No compartas tus claves de Tuya/Amazon Basics.

---

## Licencia

MIT License. Consulta el archivo LICENSE para más detalles.

---
