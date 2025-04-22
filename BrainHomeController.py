import time
import json
import threading
import numpy as np
import tkinter as tk
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import requests  # Para comunicación HTTP con ESP8266
import socket   # Para conectar con ThinkGear
import struct   # Para decodificar datos binarios

class ThinkGearClient:
    """Cliente para conectarse al ThinkGear Connector mediante socket TCP"""
    
    # Códigos de los datos según el protocolo ThinkGear
    POOR_SIGNAL = 0x02
    ATTENTION = 0x04
    MEDITATION = 0x05
    BLINK_STRENGTH = 0x16
    RAW_WAVE = 0x80
    ASIC_EEG_POWER = 0x83
    
    def __init__(self, host='127.0.0.1', port=13854):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.running = False
        
        # Callbacks
        self.attention_handlers = []
        self.meditation_handlers = []
        self.blink_handlers = []
        self.poor_signal_handlers = []
        
        # Thread para la lectura de datos
        self.thread = None
    
    def connect(self):
        """Conecta con el ThinkGear Connector"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            
            # Enviar comando para activar la salida de datos JSON
            init_json_cmd = '{"enableRawOutput": false, "format": "Json"}'
            self.socket.sendall(init_json_cmd.encode('utf-8'))
            
            self.connected = True
            self.running = True
            
            # Iniciar thread de lectura
            self.thread = threading.Thread(target=self._read_data_loop)
            self.thread.daemon = True
            self.thread.start()
            
            print(f"Conectado a ThinkGear en {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"Error conectando con ThinkGear: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Desconecta del ThinkGear Connector"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        self.connected = False
    
    def _read_data_loop(self):
        """Bucle de lectura de datos desde el socket"""
        buffer = ""
        
        while self.running and self.connected:
            try:
                # Leer datos del socket
                data = self.socket.recv(1024).decode('utf-8')
                if not data:
                    # Conexión cerrada
                    self.connected = False
                    break
                
                # Añadir al buffer y procesar líneas completas
                buffer += data
                lines = buffer.split('\r')
                
                # Procesar todas las líneas completas
                for i in range(len(lines) - 1):
                    try:
                        # Procesar línea JSON
                        self._process_json_data(lines[i])
                    except json.JSONDecodeError:
                        pass  # Ignorar líneas no JSON
                
                # Guardar la última línea incompleta
                buffer = lines[-1]
                
            except Exception as e:
                print(f"Error leyendo datos de ThinkGear: {e}")
                self.connected = False
                break
    
    def _process_json_data(self, line):
        """Procesa una línea de datos en formato JSON"""
        if not line.strip():
            return
            
        data = json.loads(line)
        
        # Procesar cada tipo de dato
        if 'poorSignalLevel' in data:
            value = data['poorSignalLevel']
            for handler in self.poor_signal_handlers:
                handler(value)
                
        if 'eSense' in data:
            if 'attention' in data['eSense']:
                value = data['eSense']['attention']
                for handler in self.attention_handlers:
                    handler(value)
                    
            if 'meditation' in data['eSense']:
                value = data['eSense']['meditation']
                for handler in self.meditation_handlers:
                    handler(value)
        
        if 'blinkStrength' in data:
            value = data['blinkStrength']
            for handler in self.blink_handlers:
                handler(value)

class BrainSignalProcessor:
    """Procesa y analiza señales cerebrales para detectar patrones e intenciones"""
    
    def __init__(self, calibration_time=30):
        self.attention_buffer = []
        self.meditation_buffer = []
        self.blink_buffer = []
        self.buffer_size = 100
        self.attention_threshold = 60  # Valor inicial, se ajustará con calibración
        self.meditation_threshold = 70
        self.blink_threshold = 80
        self.calibration_time = calibration_time
        self.calibrated = False
        self.gesture_patterns = {
            'luz_on': {'attention': 'spike', 'duration': 2},
            'luz_off': {'meditation': 'spike', 'duration': 2},
            'todo_off': {'blink': 'triple', 'duration': 3},
            # Se pueden añadir más patrones
        }
        self.detected_gestures = []
    
    def update(self, signal_type, value):
        """Actualiza los buffers con nuevos valores"""
        if signal_type == 'attention':
            self.attention_buffer.append(value)
            if len(self.attention_buffer) > self.buffer_size:
                self.attention_buffer.pop(0)
        elif signal_type == 'meditation':
            self.meditation_buffer.append(value)
            if len(self.meditation_buffer) > self.buffer_size:
                self.meditation_buffer.pop(0)
        elif signal_type == 'blink':
            self.blink_buffer.append(value)
            if len(self.blink_buffer) > self.buffer_size:
                self.blink_buffer.pop(0)
        
        self._detect_patterns()
    
    def calibrate(self):
        """Inicia proceso de calibración personalizada"""
        self.calibrated = False
        self.attention_buffer = []
        self.meditation_buffer = []
        self.blink_buffer = []
        print("Iniciando calibración. Relájate durante los primeros 15 segundos...")
        # La calibración continuaría en un thread separado
        
    def _detect_patterns(self):
        """Detecta patrones específicos en las señales cerebrales"""
        # Detección de picos de atención
        if len(self.attention_buffer) >= 5:
            recent_attention = self.attention_buffer[-5:]
            if max(recent_attention) > self.attention_threshold and \
               recent_attention[-1] > self.attention_threshold and \
               recent_attention[0] < self.attention_threshold * 0.7:
                self.detected_gestures.append(('luz_on', time.time()))
                
        # Detección de triple parpadeo
        if len(self.blink_buffer) >= 10:
            recent_blinks = self.blink_buffer[-10:]
            # Algoritmo simplificado para detectar 3 parpadeos consecutivos
            blink_count = sum(1 for b in recent_blinks if b > self.blink_threshold)
            if blink_count >= 3:
                self.detected_gestures.append(('todo_off', time.time()))
        
        # Limitar el historial de gestos detectados
        if len(self.detected_gestures) > 20:
            self.detected_gestures = self.detected_gestures[-20:]
    
    def get_command(self):
        """Devuelve el comando más reciente si existe y lo elimina de la lista"""
        if self.detected_gestures:
            gesture, timestamp = self.detected_gestures.pop(0)
            if time.time() - timestamp < 3:  # Solo comandos recientes
                return gesture
        return None

class ESP8266Controller:
    """Gestiona la comunicación bidireccional con ESP8266"""
    
    def __init__(self, ip_address, port=80):
        self.ip_address = ip_address
        self.port = port
        self.base_url = f"http://{ip_address}:{port}"
        self.connected = False
        self.device_status = {}
        self.lock = threading.Lock()
        self.connect()
        
    def connect(self):
        """Establece conexión con ESP8266"""
        try:
            # Intenta una solicitud simple para verificar conexión
            response = requests.get(f"{self.base_url}/status", timeout=2)
            if response.status_code == 200:
                self.connected = True
                # Iniciar thread de polling para estado
                threading.Thread(target=self._status_polling, daemon=True).start()
                print(f"Conectado a ESP8266 en {self.ip_address}")
                return True
            else:
                print(f"Error conectando con ESP8266: Status code {response.status_code}")
                self.connected = False
                return False
        except Exception as e:
            print(f"Error al conectar con ESP8266: {e}")
            self.connected = False
            return False
    
    def send_command(self, command, params=None):
        """Envía un comando a ESP8266 vía HTTP"""
        if not self.connected:
            return False
            
        cmd_obj = {
            "cmd": command,
            "timestamp": time.time(),
            "id": int(time.time() * 1000) % 10000
        }
        
        if params:
            cmd_obj["params"] = params
            
        with self.lock:
            try:
                response = requests.post(
                    f"{self.base_url}/command",
                    json=cmd_obj,
                    timeout=2
                )
                
                if response.status_code == 200:
                    try:
                        resp_data = response.json()
                        self._process_response(resp_data)
                        return True
                    except ValueError:
                        print("Respuesta no válida del ESP8266")
                        return False
                else:
                    print(f"Error enviando comando: Status code {response.status_code}")
                    return False
            except Exception as e:
                print(f"Error enviando comando: {e}")
                self.connected = False
                return False
    
    def _status_polling(self):
        """Thread que realiza polling del estado del ESP8266"""
        while self.connected:
            try:
                response = requests.get(f"{self.base_url}/status", timeout=2)
                if response.status_code == 200:
                    try:
                        status_data = response.json()
                        self._process_response(status_data)
                    except ValueError:
                        print("Datos de estado no válidos")
                else:
                    print(f"Error obteniendo estado: Status code {response.status_code}")
                    self.connected = False
            except Exception as e:
                print(f"Error en polling de estado: {e}")
                self.connected = False
                break
            
            time.sleep(5)  # Polling cada 5 segundos
    
    def _process_response(self, response):
        """Procesa respuestas JSON del ESP8266"""
        if "status" in response:
            # Actualizar estado de dispositivos
            if "devices" in response:
                self.device_status = response["devices"]
                print(f"Estado actualizado: {self.device_status}")
        elif "error" in response:
            print(f"Error desde ESP8266: {response['error']}")
        
    def get_device_status(self):
        """Devuelve el estado actual de los dispositivos"""
        return self.device_status

class BrainHomeApp:
    """Aplicación principal con interfaz gráfica"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("BrainHome Controller")
        self.root.geometry("800x600")
        
        # Componentes principales
        self.processor = BrainSignalProcessor()
        
        # Intentar detectar IP ESP8266 automáticamente o usar default
        esp_ip = self._detect_esp8266_ip()
        self.esp8266 = ESP8266Controller(esp_ip)
        
        # Intentar conectar con ThinkGear
        self.thinkgear = None
        self.connect_thinkgear()
        
        # Configurar interfaz
        self._setup_ui()
        
        # Iniciar thread de control
        self.running = True
        threading.Thread(target=self._control_loop, daemon=True).start()
    
    def _detect_esp8266_ip(self):
        """Detecta automáticamente la IP del ESP8266 o devuelve la IP por defecto"""
        # Simplificado - en una implementación real podría buscar en la red
        return "192.168.1.100"  # IP por defecto del ESP8266
    
    def connect_thinkgear(self):
        """Intenta conectar con el servicio ThinkGear"""
        try:
            self.thinkgear = ThinkGearClient()
            success = self.thinkgear.connect()
            
            if success:
                # Registrar handlers
                self.thinkgear.attention_handlers.append(
                    lambda value: self.processor.update('attention', value))
                self.thinkgear.meditation_handlers.append(
                    lambda value: self.processor.update('meditation', value))
                self.thinkgear.blink_handlers.append(
                    lambda value: self.processor.update('blink', value))
                    
                print("Conectado a ThinkGear")
                return True
            else:
                print("No se pudo conectar a ThinkGear")
                return False
        except Exception as e:
            print(f"Error conectando con ThinkGear: {e}")
            return False
    
    def _setup_ui(self):
        """Configura la interfaz gráfica"""
        # Frame principal con pestañas
        notebook = ttk.Notebook(self.root)
        
        # Pestaña de control
        control_frame = ttk.Frame(notebook)
        notebook.add(control_frame, text="Control")
        
        # Pestaña de configuración
        config_frame = ttk.Frame(notebook)
        notebook.add(config_frame, text="Configuración")
        
        # Pestaña de gráficos
        graph_frame = ttk.Frame(notebook)
        notebook.add(graph_frame, text="Señales")
        
        notebook.pack(expand=1, fill="both")
        
        # Contenido del panel de control
        self._setup_control_panel(control_frame)
        
        # Contenido del panel de configuración
        self._setup_config_panel(config_frame)
        
        # Contenido del panel de gráficos
        self._setup_graph_panel(graph_frame)
    
    def _setup_control_panel(self, parent):
        """Configura el panel de control principal"""
        # Estado de conexión
        frame_status = ttk.LabelFrame(parent, text="Estado")
        frame_status.pack(fill="x", padx=10, pady=5)
        
        self.lbl_mindwave_status = ttk.Label(frame_status, text="ThinkGear: Desconectado")
        self.lbl_mindwave_status.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        self.lbl_esp8266_status = ttk.Label(frame_status, text="ESP8266: Desconectado")
        self.lbl_esp8266_status.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # Panel de dispositivos
        frame_devices = ttk.LabelFrame(parent, text="Dispositivos")
        frame_devices.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Dispositivos de ejemplo con botones de control manual
        devices = [
            {"name": "Luz principal", "id": "light_main"},
            {"name": "Luz secundaria", "id": "light_sec"},
            {"name": "Persiana", "id": "blind"},
            {"name": "Ventilador", "id": "fan"},
            {"name": "TV", "id": "tv"}
        ]
        
        self.device_widgets = {}
        
        for i, device in enumerate(devices):
            ttk.Label(frame_devices, text=device["name"]).grid(row=i, column=0, padx=5, pady=5, sticky="w")
            
            status_var = tk.StringVar(value="Desconocido")
            status_label = ttk.Label(frame_devices, textvariable=status_var)
            status_label.grid(row=i, column=1, padx=5, pady=5)
            
            btn_on = ttk.Button(frame_devices, text="Encender", 
                               command=lambda d=device["id"]: self.esp8266.send_command("set", {"device": d, "state": "on"}))
            btn_on.grid(row=i, column=2, padx=5, pady=5)
            
            btn_off = ttk.Button(frame_devices, text="Apagar", 
                                command=lambda d=device["id"]: self.esp8266.send_command("set", {"device": d, "state": "off"}))
            btn_off.grid(row=i, column=3, padx=5, pady=5)
            
            self.device_widgets[device["id"]] = {
                "status": status_var,
                "btn_on": btn_on,
                "btn_off": btn_off
            }
        
        # Panel de comandos mentales recientes
        frame_commands = ttk.LabelFrame(parent, text="Comandos Mentales Detectados")
        frame_commands.pack(fill="x", padx=10, pady=5)
        
        self.commands_text = tk.Text(frame_commands, height=5, state="disabled")
        self.commands_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Botones de control principal
        frame_actions = ttk.Frame(parent)
        frame_actions.pack(fill="x", padx=10, pady=10)
        
        btn_calibrate = ttk.Button(frame_actions, text="Calibrar Señales", 
                                   command=self._start_calibration)
        btn_calibrate.pack(side="left", padx=5)
        
        btn_refresh = ttk.Button(frame_actions, text="Actualizar Estado", 
                                command=lambda: self.esp8266.send_command("status"))
        btn_refresh.pack(side="left", padx=5)
        
        btn_all_off = ttk.Button(frame_actions, text="Apagar Todo", 
                                command=lambda: self.esp8266.send_command("all_off"))
        btn_all_off.pack(side="right", padx=5)
    
    def _setup_config_panel(self, parent):
        """Configura el panel de ajustes"""
        # Configuración de umbrales
        frame_thresholds = ttk.LabelFrame(parent, text="Umbrales de Detección")
        frame_thresholds.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(frame_thresholds, text="Atención:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.attention_threshold = tk.Scale(frame_thresholds, from_=0, to=100, orient="horizontal")
        self.attention_threshold.set(self.processor.attention_threshold)
        self.attention_threshold.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(frame_thresholds, text="Meditación:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.meditation_threshold = tk.Scale(frame_thresholds, from_=0, to=100, orient="horizontal")
        self.meditation_threshold.set(self.processor.meditation_threshold)
        self.meditation_threshold.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(frame_thresholds, text="Parpadeo:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.blink_threshold = tk.Scale(frame_thresholds, from_=0, to=100, orient="horizontal")
        self.blink_threshold.set(self.processor.blink_threshold)
        self.blink_threshold.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        
        btn_apply = ttk.Button(frame_thresholds, text="Aplicar", command=self._apply_thresholds)
        btn_apply.grid(row=3, column=1, padx=5, pady=5, sticky="e")
        
        # Configuración de conexión
        frame_connection = ttk.LabelFrame(parent, text="Configuración de Conexión")
        frame_connection.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(frame_connection, text="IP ESP8266:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.esp8266_ip = ttk.Entry(frame_connection)
        self.esp8266_ip.insert(0, self.esp8266.ip_address)
        self.esp8266_ip.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(frame_connection, text="Puerto ESP8266:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.esp8266_port = ttk.Entry(frame_connection)
        self.esp8266_port.insert(0, str(self.esp8266.port))
        self.esp8266_port.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(frame_connection, text="Host ThinkGear:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.thinkgear_host = ttk.Entry(frame_connection)
        self.thinkgear_host.insert(0, "127.0.0.1")  # Host por defecto del ThinkGear
        self.thinkgear_host.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(frame_connection, text="Puerto ThinkGear:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.thinkgear_port = ttk.Entry(frame_connection)
        self.thinkgear_port.insert(0, "13854")  # Puerto por defecto del ThinkGear
        self.thinkgear_port.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        
        btn_reconnect = ttk.Button(frame_connection, text="Reconectar", command=self._reconnect_devices)
        btn_reconnect.grid(row=4, column=1, padx=5, pady=5, sticky="e")
        
        # Perfiles y mapeos
        frame_profiles = ttk.LabelFrame(parent, text="Perfiles y Mapeos de Comandos")
        frame_profiles.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Aquí iría una lista de mapeos configurables de señales a comandos
        # Por brevedad, omitimos la implementación detallada
    
    def _setup_graph_panel(self, parent):
        """Configura el panel de visualización de señales"""
        # Crear figura de matplotlib
        self.fig = Figure(figsize=(10, 6), dpi=100)
        
        # Tres subplots para atención, meditación y parpadeos
        self.ax_attention = self.fig.add_subplot(311)
        self.ax_meditation = self.fig.add_subplot(312)
        self.ax_blink = self.fig.add_subplot(313)
        
        self.ax_attention.set_title("Atención")
        self.ax_meditation.set_title("Meditación")
        self.ax_blink.set_title("Parpadeos")
        
        self.ax_attention.set_ylim(0, 100)
        self.ax_meditation.set_ylim(0, 100)
        self.ax_blink.set_ylim(0, 100)
        
        # Líneas iniciales
        self.line_attention, = self.ax_attention.plot([], [], 'r-')
        self.line_meditation, = self.ax_meditation.plot([], [], 'g-')
        self.line_blink, = self.ax_blink.plot([], [], 'b-')
        
        self.fig.tight_layout()
        
        # Crear canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        
        # Actualización periódica
        self.root.after(1000, self._update_graphs)
    
    def _update_graphs(self):
        """Actualiza los gráficos con nuevos datos"""
        # Actualizar datos de atención
        x = range(len(self.processor.attention_buffer))
        self.line_attention.set_data(x, self.processor.attention_buffer)
        if x:
            self.ax_attention.set_xlim(0, max(x))
        
        # Actualizar datos de meditación
        x = range(len(self.processor.meditation_buffer))
        self.line_meditation.set_data(x, self.processor.meditation_buffer)
        if x:
            self.ax_meditation.set_xlim(0, max(x))
        
        # Actualizar datos de parpadeo
        x = range(len(self.processor.blink_buffer))
        self.line_blink.set_data(x, self.processor.blink_buffer)
        if x:
            self.ax_blink.set_xlim(0, max(x))
        
        self.canvas.draw()
        
        # Programar próxima actualización
        self.root.after(1000, self._update_graphs)
    
    def _apply_thresholds(self):
        """Aplica los nuevos umbrales configurados"""
        self.processor.attention_threshold = self.attention_threshold.get()
        self.processor.meditation_threshold = self.meditation_threshold.get()
        self.processor.blink_threshold = self.blink_threshold.get()
        print(f"Nuevos umbrales aplicados: A={self.processor.attention_threshold}, "
              f"M={self.processor.meditation_threshold}, B={self.processor.blink_threshold}")
    
    def _reconnect_devices(self):
        """Reconecta a los dispositivos con los nuevos parámetros configurados"""
        # Reconectar ESP8266
        new_esp8266_ip = self.esp8266_ip.get()
        new_esp8266_port = int(self.esp8266_port.get())
        
        if new_esp8266_ip != self.esp8266.ip_address or new_esp8266_port != self.esp8266.port:
            self.esp8266 = ESP8266Controller(new_esp8266_ip, new_esp8266_port)
        
        # Reconectar ThinkGear
        if self.thinkgear:
            self.thinkgear.disconnect()
            
        self.thinkgear = ThinkGearClient(
            host=self.thinkgear_host.get(),
            port=int(self.thinkgear_port.get())
        )
        self.thinkgear.connect()
        
        # Registrar handlers
        if self.thinkgear.connected:
            self.thinkgear.attention_handlers.append(
                lambda value: self.processor.update('attention', value))
            self.thinkgear.meditation_handlers.append(
                lambda value: self.processor.update('meditation', value))
            self.thinkgear.blink_handlers.append(
                lambda value: self.processor.update('blink', value))
        
        print("Dispositivos reconectados")
    
    def _start_calibration(self):
        """Inicia el proceso de calibración"""
        # Implementación simplificada
        self.processor.calibrate()
        print("Calibración iniciada. Sigue las instrucciones...")
    
    def _control_loop(self):
        """Bucle principal de control que ejecuta comandos detectados"""
        while self.running:
            try:
                # Actualizar estado de conexión en UI
                if self.thinkgear and self.thinkgear.connected:
                    self.lbl_mindwave_status.config(text="ThinkGear: Conectado")
                else:
                    self.lbl_mindwave_status.config(text="ThinkGear: Desconectado")
                
                if self.esp8266.connected:
                    self.lbl_esp8266_status.config(text="ESP8266: Conectado")
                else:
                    self.lbl_esp8266_status.config(text="ESP8266: Desconectado")
                
                # Actualizar estado de dispositivos
                device_status = self.esp8266.get_device_status()
                for device_id, status in device_status.items():
                    if device_id in self.device_widgets:
                        self.device_widgets[device_id]["status"].set(
                            "Encendido" if status == "on" else "Apagado")
                
                # Procesar comandos mentales
                command = self.processor.get_command()
                if command:
                    # Actualizar UI
                    self.commands_text.config(state="normal")
                    self.commands_text.insert("end", f"{time.strftime('%H:%M:%S')}: {command}\n")
                    self.commands_text.see("end")
                    self.commands_text.config(state="disabled")
                    
                    # Enviar comando a ESP8266
                    if command == "luz_on":
                        self.esp8266.send_command("set", {"device": "light_main", "state": "on"})
                    elif command == "luz_off":
                        self.esp8266.send_command("set", {"device": "light_main", "state": "off"})
                    elif command == "todo_off":
                        self.esp8266.send_command("all_off")
                
                time.sleep(0.1)
            except Exception as e:
                print(f"Error en el bucle de control: {e}")
                time.sleep(1)  # Pausa para evitar bucle de errores

# Punto de entrada principal
if __name__ == "__main__":
    root = tk.Tk()
    app = BrainHomeApp(root)
    root.mainloop()