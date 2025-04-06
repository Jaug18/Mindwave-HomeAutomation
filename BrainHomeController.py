import serial
import time
import json
import threading
import numpy as np
import tkinter as tk
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from mindwave import Headset  # Usando el módulo existente

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

class ArduinoController:
    """Gestiona la comunicación bidireccional con Arduino"""
    
    def __init__(self, port, baud_rate=115200):
        self.port = port
        self.baud_rate = baud_rate
        self.connection = None
        self.connected = False
        self.command_queue = []
        self.response_buffer = ""
        self.device_status = {}
        self.lock = threading.Lock()
        self.connect()
        
    def connect(self):
        """Establece conexión con Arduino"""
        try:
            self.connection = serial.Serial(self.port, self.baud_rate, timeout=1)
            time.sleep(2)  # Esperar a que Arduino reinicie
            self.connected = True
            # Iniciar thread de lectura de respuestas
            threading.Thread(target=self._read_responses, daemon=True).start()
            print(f"Conectado a Arduino en {self.port}")
            return True
        except Exception as e:
            print(f"Error al conectar con Arduino: {e}")
            self.connected = False
            return False
    
    def send_command(self, command, params=None):
        """Envía un comando a Arduino con formato JSON"""
        if not self.connected:
            return False
            
        cmd_obj = {
            "cmd": command,
            "timestamp": time.time(),
            "id": int(time.time() * 1000) % 10000
        }
        
        if params:
            cmd_obj["params"] = params
            
        cmd_json = json.dumps(cmd_obj) + "\n"
        
        with self.lock:
            try:
                self.connection.write(cmd_json.encode())
                return True
            except Exception as e:
                print(f"Error enviando comando: {e}")
                self.connected = False
                return False
    
    def _read_responses(self):
        """Thread que lee y procesa respuestas de Arduino"""
        while self.connected:
            try:
                if self.connection.in_waiting:
                    new_data = self.connection.read(self.connection.in_waiting).decode()
                    self.response_buffer += new_data
                    
                    # Procesar líneas completas
                    while '\n' in self.response_buffer:
                        line, self.response_buffer = self.response_buffer.split('\n', 1)
                        try:
                            response = json.loads(line)
                            self._process_response(response)
                        except json.JSONDecodeError:
                            print(f"Respuesta inválida: {line}")
                
                time.sleep(0.1)
            except Exception as e:
                print(f"Error leyendo respuestas: {e}")
                self.connected = False
                break
    
    def _process_response(self, response):
        """Procesa respuestas JSON de Arduino"""
        if "status" in response:
            # Actualizar estado de dispositivos
            if "devices" in response:
                self.device_status = response["devices"]
                print(f"Estado actualizado: {self.device_status}")
        elif "error" in response:
            print(f"Error desde Arduino: {response['error']}")
        
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
        
        # Intentar detectar puerto Arduino automáticamente
        arduino_port = self._detect_arduino_port()
        self.arduino = ArduinoController(arduino_port)
        
        # Intentar conectar con MindWave
        self.mindwave = None
        self.connect_mindwave()
        
        # Configurar interfaz
        self._setup_ui()
        
        # Iniciar thread de control
        self.running = True
        threading.Thread(target=self._control_loop, daemon=True).start()
    
    def _detect_arduino_port(self):
        """Detecta automáticamente el puerto de Arduino"""
        # Simplificado para este ejemplo
        import serial.tools.list_ports
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            if "Arduino" in p.description or "CH340" in p.description:
                return p.device
        
        # Puerto por defecto según sistema operativo
        import platform
        system = platform.system()
        if system == "Windows":
            return "COM3"
        elif system == "Darwin":  # macOS
            return "/dev/cu.usbmodem14101"
        else:  # Linux
            return "/dev/ttyACM0"
    
    def connect_mindwave(self):
        """Intenta conectar con el dispositivo MindWave"""
        try:
            self.mindwave = Headset('/dev/rfcomm0')  # Ajustar según tu sistema
            
            # Registrar handlers
            self.mindwave.attention_handlers.append(
                lambda value: self.processor.update('attention', value))
            self.mindwave.meditation_handlers.append(
                lambda value: self.processor.update('meditation', value))
            self.mindwave.blink_handlers.append(
                lambda value: self.processor.update('blink', value))
                
            print("Conectado a MindWave Mobile 2")
            return True
        except Exception as e:
            print(f"Error conectando con MindWave: {e}")
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
        
        self.lbl_mindwave_status = ttk.Label(frame_status, text="MindWave: Desconectado")
        self.lbl_mindwave_status.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        self.lbl_arduino_status = ttk.Label(frame_status, text="Arduino: Desconectado")
        self.lbl_arduino_status.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
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
                               command=lambda d=device["id"]: self.arduino.send_command("set", {"device": d, "state": "on"}))
            btn_on.grid(row=i, column=2, padx=5, pady=5)
            
            btn_off = ttk.Button(frame_devices, text="Apagar", 
                                command=lambda d=device["id"]: self.arduino.send_command("set", {"device": d, "state": "off"}))
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
                                command=lambda: self.arduino.send_command("status"))
        btn_refresh.pack(side="left", padx=5)
        
        btn_all_off = ttk.Button(frame_actions, text="Apagar Todo", 
                                command=lambda: self.arduino.send_command("all_off"))
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
        
        ttk.Label(frame_connection, text="Puerto Arduino:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.arduino_port = ttk.Entry(frame_connection)
        self.arduino_port.insert(0, self.arduino.port)
        self.arduino_port.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(frame_connection, text="Puerto MindWave:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.mindwave_port = ttk.Entry(frame_connection)
        self.mindwave_port.insert(0, "/dev/rfcomm0")  # Ajustar según configuración inicial
        self.mindwave_port.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        btn_reconnect = ttk.Button(frame_connection, text="Reconectar", command=self._reconnect_devices)
        btn_reconnect.grid(row=2, column=1, padx=5, pady=5, sticky="e")
        
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
        """Reconecta a los dispositivos con los nuevos puertos configurados"""
        # Reconectar Arduino
        new_arduino_port = self.arduino_port.get()
        if new_arduino_port != self.arduino.port:
            self.arduino = ArduinoController(new_arduino_port)
        
        # Reconectar MindWave
        # Implementación simplificada
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
                if self.mindwave and self.mindwave.connected:
                    self.lbl_mindwave_status.config(text="MindWave: Conectado")
                else:
                    self.lbl_mindwave_status.config(text="MindWave: Desconectado")
                
                if self.arduino.connected:
                    self.lbl_arduino_status.config(text="Arduino: Conectado")
                else:
                    self.lbl_arduino_status.config(text="Arduino: Desconectado")
                
                # Actualizar estado de dispositivos
                device_status = self.arduino.get_device_status()
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
                    
                    # Enviar comando a Arduino
                    if command == "luz_on":
                        self.arduino.send_command("set", {"device": "light_main", "state": "on"})
                    elif command == "luz_off":
                        self.arduino.send_command("set", {"device": "light_main", "state": "off"})
                    elif command == "todo_off":
                        self.arduino.send_command("all_off")
                
                time.sleep(0.1)
            except Exception as e:
                print(f"Error en el bucle de control: {e}")
                time.sleep(1)  # Pausa para evitar bucle de errores

# Punto de entrada principal
if __name__ == "__main__":
    root = tk.Tk()
    app = BrainHomeApp(root)
    root.mainloop()