import time
import json
import threading
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import requests
import socket
import queue
import os

# --- Internacionalización básica (es/en) ---
LANG = "es"
STRINGS = {
    "es": {
        "thinkgear_disconnected": "ThinkGear: Desconectado",
        "thinkgear_connected": "ThinkGear: Conectado",
        "esp_disconnected": "ESP8266: Desconectado",
        "esp_connected": "ESP8266: Conectado",
        "bulb_on": "ENCENDIDO",
        "bulb_off": "APAGADO",
        "attention": "Atención (Encender)",
        "meditation": "Meditación (Apagar)",
        "blink": "Parpadeos (Ajustar Brillo)",
        "signal_quality": "Calidad de señal",
        "calibration_started": "Calibración iniciada. Sigue las instrucciones...",
        "calibration_done": "Calibración completada.",
        "apply": "Aplicar",
        "reconnect": "Reconectar",
        "calibrate": "Calibrar Señales",
        "guide": "Guía de Uso",
        "guide_text": "• CONCENTRACIÓN ALTA: Enciende el foco\n• MEDITACIÓN PROFUNDA: Apaga el foco\n• TRIPLE PARPADEO: Ajusta el brillo al nivel configurado\n\nAjusta los umbrales según tu nivel de concentración y relajación personal.",
        "error": "Error",
        "info": "Información",
        "calibration_saved": "Calibración guardada.",
        "calibration_loaded": "Calibración cargada.",
        "invalid_ip": "IP no válida.",
        "invalid_port": "Puerto no válido.",
        "logs": "Logs",
        "select_lang": "Idioma",
        "spanish": "Español",
        "english": "Inglés",
        "signal_poor": "Señal: Mala",
        "signal_good": "Señal: Buena",
        "signal_excellent": "Señal: Excelente"
    },
    "en": {
        "thinkgear_disconnected": "ThinkGear: Disconnected",
        "thinkgear_connected": "ThinkGear: Connected",
        "esp_disconnected": "ESP8266: Disconnected",
        "esp_connected": "ESP8266: Connected",
        "bulb_on": "ON",
        "bulb_off": "OFF",
        "attention": "Attention (On)",
        "meditation": "Meditation (Off)",
        "blink": "Blinks (Set Brightness)",
        "signal_quality": "Signal quality",
        "calibration_started": "Calibration started. Follow the instructions...",
        "calibration_done": "Calibration completed.",
        "apply": "Apply",
        "reconnect": "Reconnect",
        "calibrate": "Calibrate Signals",
        "guide": "User Guide",
        "guide_text": "• HIGH CONCENTRATION: Turns on the bulb\n• DEEP MEDITATION: Turns off the bulb\n• TRIPLE BLINK: Sets brightness to configured level\n\nAdjust thresholds according to your personal concentration and relaxation levels.",
        "error": "Error",
        "info": "Info",
        "calibration_saved": "Calibration saved.",
        "calibration_loaded": "Calibration loaded.",
        "invalid_ip": "Invalid IP.",
        "invalid_port": "Invalid port.",
        "logs": "Logs",
        "select_lang": "Language",
        "spanish": "Spanish",
        "english": "English",
        "signal_poor": "Signal: Poor",
        "signal_good": "Signal: Good",
        "signal_excellent": "Signal: Excellent"
    }
}
def _(key):
    return STRINGS[LANG].get(key, key)

# --- Utilidades para persistencia de calibración ---
CALIBRATION_FILE = "calibration.json"
def save_calibration(thresholds):
    try:
        with open(CALIBRATION_FILE, "w") as f:
            json.dump(thresholds, f)
        return True
    except Exception:
        return False

def load_calibration():
    if os.path.exists(CALIBRATION_FILE):
        try:
            with open(CALIBRATION_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return None
    return None

class ThinkGearClient:
    """Cliente para conectarse al ThinkGear Connector mediante socket TCP"""
    
    def __init__(self, host='127.0.0.1', port=13854):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.running = False
        self.signal_quality = 200  # 0 = excelente, 200 = muy mala
        
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
                    self.connected = False
                    break
                
                # Añadir al buffer y procesar líneas completas
                buffer += data
                lines = buffer.split('\r')
                
                for i in range(len(lines) - 1):
                    try:
                        self._process_json_data(lines[i])
                    except json.JSONDecodeError:
                        pass
                
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
            self.signal_quality = value
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
        self.attention_threshold = 60
        self.meditation_threshold = 70
        self.blink_threshold = 80
        self.calibration_time = calibration_time
        self.calibrated = False
        self.gesture_patterns = {
            'foco_on': {'attention': 'spike', 'duration': 2},
            'foco_off': {'meditation': 'spike', 'duration': 2},
            'ajustar_brillo': {'blink': 'triple', 'duration': 3},
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
    
    def calibrate(self, callback=None):
        """Inicia proceso de calibración personalizada"""
        self.calibrated = False
        self.attention_buffer = []
        self.meditation_buffer = []
        self.blink_buffer = []
        self._calibration_callback = callback
        threading.Thread(target=self._calibration_thread, daemon=True).start()

    def _calibration_thread(self):
        # Calibración interactiva: 15s relajación, 15s concentración
        print("Iniciando calibración. Relájate durante los primeros 15 segundos...")
        time.sleep(15)
        att_relax = self.attention_buffer[-20:] if len(self.attention_buffer) >= 20 else self.attention_buffer[:]
        med_relax = self.meditation_buffer[-20:] if len(self.meditation_buffer) >= 20 else self.meditation_buffer[:]
        print("Ahora concéntrate intensamente durante 15 segundos...")
        self.attention_buffer = []
        self.meditation_buffer = []
        time.sleep(15)
        att_focus = self.attention_buffer[-20:] if len(self.attention_buffer) >= 20 else self.attention_buffer[:]
        med_focus = self.meditation_buffer[-20:] if len(self.meditation_buffer) >= 20 else self.meditation_buffer[:]
        # Calcular umbrales
        if att_relax and att_focus:
            self.attention_threshold = int((np.mean(att_relax) + np.mean(att_focus)) / 2)
        if med_relax and med_focus:
            self.meditation_threshold = int((np.mean(med_relax) + np.mean(med_focus)) / 2)
        self.calibrated = True
        # Guardar calibración
        save_calibration({
            "attention": self.attention_threshold,
            "meditation": self.meditation_threshold,
            "blink": self.blink_threshold
        })
        if self._calibration_callback:
            self._calibration_callback()
        print("Calibración completada.")
    
    def _detect_patterns(self):
        """Detecta patrones específicos en las señales cerebrales"""
        # Detección de picos de atención para encender
        if len(self.attention_buffer) >= 5:
            recent_attention = self.attention_buffer[-5:]
            if max(recent_attention) > self.attention_threshold and \
               recent_attention[-1] > self.attention_threshold and \
               recent_attention[0] < self.attention_threshold * 0.7:
                self.detected_gestures.append(('foco_on', time.time()))
        
        # Detección de picos de meditación para apagar
        if len(self.meditation_buffer) >= 5:
            recent_meditation = self.meditation_buffer[-5:]
            if max(recent_meditation) > self.meditation_threshold and \
               recent_meditation[-1] > self.meditation_threshold and \
               recent_meditation[0] < self.meditation_threshold * 0.7:
                self.detected_gestures.append(('foco_off', time.time()))
                
        # Detección de triple parpadeo para ajustar brillo
        if len(self.blink_buffer) >= 10:
            recent_blinks = self.blink_buffer[-10:]
            blink_count = sum(1 for b in recent_blinks if b > self.blink_threshold)
            if blink_count >= 3:
                self.detected_gestures.append(('ajustar_brillo', time.time()))
        
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

class SmartBulbController:
    """Gestiona la comunicación con el foco inteligente a través del ESP8266"""
    
    def __init__(self, ip_address, port=80):
        self.ip_address = ip_address
        self.port = port
        self.base_url = f"http://{ip_address}:{port}"
        self.connected = False
        self.bulb_status = {
            "state": "off",
            "brightness": 100
        }
        self.lock = threading.Lock()
        self.connect()
        
    def connect(self):
        """Establece conexión con el ESP8266"""
        try:
            response = requests.get(f"{self.base_url}/status", timeout=2)
            if response.status_code == 200:
                self.connected = True
                self._process_response(response.json())
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
            threading.Thread(target=self._auto_reconnect, daemon=True).start()
            return False
    
    def send_command(self, command, params=None):
        """Envía un comando al ESP8266"""
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
    
    def turn_on(self):
        """Enciende el foco"""
        return self.send_command("set", {"state": "on"})
    
    def turn_off(self):
        """Apaga el foco"""
        return self.send_command("set", {"state": "off"})
    
    def set_brightness(self, brightness):
        """Ajusta el brillo del foco (0-100)"""
        brightness = max(1, min(100, brightness))
        return self.send_command("set", {"state": "on", "brightness": brightness})
    
    def _status_polling(self):
        """Thread que realiza polling del estado del foco"""
        while self.connected:
            try:
                response = requests.get(f"{self.base_url}/status", timeout=2)
                if response.status_code == 200:
                    try:
                        self._process_response(response.json())
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
        if "state" in response:
            self.bulb_status["state"] = response["state"]
        if "brightness" in response:
            self.bulb_status["brightness"] = response["brightness"]
        
    def get_status(self):
        """Devuelve el estado actual del foco"""
        return self.bulb_status

    def _auto_reconnect(self):
        """Reconexión automática si se pierde la conexión"""
        while not self.connected:
            try:
                time.sleep(5)
                response = requests.get(f"{self.base_url}/status", timeout=2)
                if response.status_code == 200:
                    self.connected = True
                    self._process_response(response.json())
                    threading.Thread(target=self._status_polling, daemon=True).start()
                    print(f"Reconectado a ESP8266 en {self.ip_address}")
                    break
            except Exception:
                continue

class BrainBulbApp:
    """Aplicación de control del foco inteligente con ondas cerebrales"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("BrainBulb Controller")
        self.root.geometry("700x550")
        
        # Componentes principales
        self.processor = BrainSignalProcessor()
        self.queue = queue.Queue()
        self.log_queue = queue.Queue()
        self.signal_quality = 200
        
        # Detectar IP ESP8266 o usar default
        esp_ip = self._detect_esp8266_ip()
        self.bulb_controller = SmartBulbController(esp_ip)
        
        # Intentar conectar con ThinkGear
        self.thinkgear = None
        self.connect_thinkgear()
        
        # Cargar calibración
        self._load_calibration()
        
        # Configurar interfaz
        self._setup_ui()
        
        # Iniciar threads
        self.running = True
        threading.Thread(target=self._control_loop, daemon=True).start()
        self.root.after(500, self._process_queue)
        self.root.after(1000, self._update_signal_quality)
    
    def _detect_esp8266_ip(self):
        """Detecta IP del ESP8266 o devuelve la IP por defecto"""
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
    
    def _load_calibration(self):
        """Carga calibración desde archivo si existe"""
        cal = load_calibration()
        if cal:
            self.processor.attention_threshold = cal.get("attention", self.processor.attention_threshold)
            self.processor.meditation_threshold = cal.get("meditation", self.processor.meditation_threshold)
            self.processor.blink_threshold = cal.get("blink", self.processor.blink_threshold)
            print(_("calibration_loaded"))
    
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
        
        # Contenido de las pestañas
        self._setup_control_panel(control_frame)
        self._setup_config_panel(config_frame)
        self._setup_graph_panel(graph_frame)
        
        # Añadir selector de idioma
        lang_frame = ttk.Frame(self.root)
        lang_frame.pack(fill="x", padx=10, pady=2)
        ttk.Label(lang_frame, text=_("select_lang")).pack(side="left")
        lang_combo = ttk.Combobox(lang_frame, values=[_("spanish"), _("english")], state="readonly")
        lang_combo.current(0 if LANG == "es" else 1)
        lang_combo.pack(side="left")
        def change_lang(event):
            global LANG
            LANG = "es" if lang_combo.current() == 0 else "en"
            messagebox.showinfo(_("info"), "Reinicia la aplicación para aplicar el idioma.")
        lang_combo.bind("<<ComboboxSelected>>", change_lang)
    
    def _setup_control_panel(self, parent):
        """Configura el panel de control principal"""
        # Estado de conexión
        frame_status = ttk.LabelFrame(parent, text="Estado")
        frame_status.pack(fill="x", padx=10, pady=5)
        
        self.lbl_mindwave_status = ttk.Label(frame_status, text="ThinkGear: Desconectado")
        self.lbl_mindwave_status.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        self.lbl_esp8266_status = ttk.Label(frame_status, text="ESP8266: Desconectado")
        self.lbl_esp8266_status.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # Indicador de calidad de señal
        self.signal_quality_var = tk.StringVar(value=_("signal_quality") + ": ???")
        self.lbl_signal_quality = ttk.Label(frame_status, textvariable=self.signal_quality_var)
        self.lbl_signal_quality.grid(row=0, column=2, padx=5, pady=5, sticky="w")
        
        # Panel del foco
        frame_bulb = ttk.LabelFrame(parent, text="Foco Inteligente Amazon Basics")
        frame_bulb.pack(fill="both", expand=True, padx=10, pady=5)
        
        ttk.Label(frame_bulb, text="Estado:").grid(row=0, column=0, padx=5, pady=15, sticky="w")
        self.bulb_status_var = tk.StringVar(value="Desconocido")
        self.bulb_status_label = ttk.Label(frame_bulb, textvariable=self.bulb_status_var, font=("Arial", 12, "bold"))
        self.bulb_status_label.grid(row=0, column=1, padx=5, pady=15, sticky="w")
        
        ttk.Label(frame_bulb, text="Brillo:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.brightness_var = tk.StringVar(value="100%")
        ttk.Label(frame_bulb, textvariable=self.brightness_var).grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        self.brightness_scale = tk.Scale(frame_bulb, from_=1, to=100, orient="horizontal", length=300)
        self.brightness_scale.set(100)
        self.brightness_scale.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky="ew")
        
        # Panel de botones
        frame_buttons = ttk.Frame(frame_bulb)
        frame_buttons.grid(row=3, column=0, columnspan=3, padx=5, pady=15)
        
        btn_on = ttk.Button(frame_buttons, text="Encender", 
                           command=lambda: self.bulb_controller.turn_on())
        btn_on.grid(row=0, column=0, padx=10)
        
        btn_off = ttk.Button(frame_buttons, text="Apagar", 
                            command=lambda: self.bulb_controller.turn_off())
        btn_off.grid(row=0, column=1, padx=10)
        
        btn_set_brightness = ttk.Button(frame_buttons, text="Ajustar Brillo", 
                                     command=lambda: self.bulb_controller.set_brightness(self.brightness_scale.get()))
        btn_set_brightness.grid(row=0, column=2, padx=10)
        
        # Panel de comandos mentales recientes
        frame_commands = ttk.LabelFrame(parent, text="Comandos Mentales Detectados")
        frame_commands.pack(fill="x", padx=10, pady=5)
        
        self.commands_text = tk.Text(frame_commands, height=5, state="disabled")
        self.commands_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Botón de calibración
        frame_actions = ttk.Frame(parent)
        frame_actions.pack(fill="x", padx=10, pady=10)
        
        btn_calibrate = ttk.Button(frame_actions, text="Calibrar Señales", 
                                  command=self._start_calibration)
        btn_calibrate.pack(side="left", padx=5)
        
        # Añadir logs
        frame_logs = ttk.LabelFrame(parent, text=_("logs"))
        frame_logs.pack(fill="both", expand=True, padx=10, pady=5)
        self.logs_text = tk.Text(frame_logs, height=5, state="disabled")
        self.logs_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Selección de brillo para gesto "ajustar_brillo"
        frame_blink = ttk.LabelFrame(parent, text=_("blink"))
        frame_blink.pack(fill="x", padx=10, pady=5)
        ttk.Label(frame_blink, text="Brillo para gesto:").pack(side="left", padx=5)
        self.blink_brightness = tk.Scale(frame_blink, from_=1, to=100, orient="horizontal", length=200)
        self.blink_brightness.set(50)
        self.blink_brightness.pack(side="left", padx=5)
    
    def _setup_config_panel(self, parent):
        """Configura el panel de configuración"""
        # Configuración de umbrales
        frame_thresholds = ttk.LabelFrame(parent, text="Umbrales de Detección")
        frame_thresholds.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(frame_thresholds, text="Atención (Encender):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.attention_threshold = tk.Scale(frame_thresholds, from_=0, to=100, orient="horizontal")
        self.attention_threshold.set(self.processor.attention_threshold)
        self.attention_threshold.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(frame_thresholds, text="Meditación (Apagar):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.meditation_threshold = tk.Scale(frame_thresholds, from_=0, to=100, orient="horizontal")
        self.meditation_threshold.set(self.processor.meditation_threshold)
        self.meditation_threshold.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(frame_thresholds, text="Parpadeo (Ajustar Brillo):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
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
        self.esp8266_ip.insert(0, self.bulb_controller.ip_address)
        self.esp8266_ip.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(frame_connection, text="Puerto ESP8266:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.esp8266_port = ttk.Entry(frame_connection)
        self.esp8266_port.insert(0, str(self.bulb_controller.port))
        self.esp8266_port.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(frame_connection, text="Host ThinkGear:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.thinkgear_host = ttk.Entry(frame_connection)
        self.thinkgear_host.insert(0, "127.0.0.1")
        self.thinkgear_host.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(frame_connection, text="Puerto ThinkGear:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.thinkgear_port = ttk.Entry(frame_connection)
        self.thinkgear_port.insert(0, "13854")
        self.thinkgear_port.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        
        btn_reconnect = ttk.Button(frame_connection, text="Reconectar", command=self._reconnect_devices)
        btn_reconnect.grid(row=4, column=1, padx=5, pady=5, sticky="e")
        
        # Guía de uso
        frame_guide = ttk.LabelFrame(parent, text="Guía de Uso")
        frame_guide.pack(fill="both", expand=True, padx=10, pady=5)
        
        guide_text = "• CONCENTRACIÓN ALTA: Enciende el foco\n"
        guide_text += "• MEDITACIÓN PROFUNDA: Apaga el foco\n"
        guide_text += "• TRIPLE PARPADEO: Ajusta el brillo al nivel configurado\n\n"
        guide_text += "Ajusta los umbrales según tu nivel de concentración y relajación personal."
        
        guide_label = ttk.Label(frame_guide, text=guide_text, wraplength=400, justify="left")
        guide_label.pack(padx=10, pady=10, fill="both", expand=True)
        
        # Botón para guardar calibración manualmente
        btn_save_cal = ttk.Button(parent, text=_("calibrate") + " & Guardar", command=self._save_calibration)
        btn_save_cal.pack(padx=10, pady=5, anchor="e")
    
    def _setup_graph_panel(self, parent):
        """Configura el panel de visualización de señales"""
        # Crear figura de matplotlib
        self.fig = Figure(figsize=(10, 6), dpi=100)
        
        # Tres subplots para atención, meditación y parpadeos
        self.ax_attention = self.fig.add_subplot(311)
        self.ax_meditation = self.fig.add_subplot(312)
        self.ax_blink = self.fig.add_subplot(313)
        
        self.ax_attention.set_title("Atención (Encender)")
        self.ax_meditation.set_title("Meditación (Apagar)")
        self.ax_blink.set_title("Parpadeos (Ajustar Brillo)")
        
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
        print(f"Umbrales aplicados: Atención={self.processor.attention_threshold}, "
              f"Meditación={self.processor.meditation_threshold}, Parpadeo={self.processor.blink_threshold}")
        self._save_calibration()
    
    def _reconnect_devices(self):
        """Reconecta a los dispositivos con los nuevos parámetros configurados"""
        # Reconectar ESP8266
        new_esp8266_ip = self.esp8266_ip.get()
        try:
            socket.inet_aton(new_esp8266_ip)
        except Exception:
            messagebox.showerror(_("error"), _("invalid_ip"))
            return
        try:
            new_esp8266_port = int(self.esp8266_port.get())
        except Exception:
            messagebox.showerror(_("error"), _("invalid_port"))
            return
        
        if new_esp8266_ip != self.bulb_controller.ip_address or new_esp8266_port != self.bulb_controller.port:
            self.bulb_controller = SmartBulbController(new_esp8266_ip, new_esp8266_port)
        
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
        def on_done():
            messagebox.showinfo(_("info"), _("calibration_done"))
        self.processor.calibrate(callback=on_done)
        messagebox.showinfo(_("info"), _("calibration_started"))
    
    def _save_calibration(self):
        """Guarda calibración actual"""
        thresholds = {
            "attention": self.processor.attention_threshold,
            "meditation": self.processor.meditation_threshold,
            "blink": self.processor.blink_threshold
        }
        if save_calibration(thresholds):
            messagebox.showinfo(_("info"), _("calibration_saved"))
        else:
            messagebox.showerror(_("error"), "No se pudo guardar calibración.")
    
    def _update_signal_quality(self):
        """Actualiza el indicador de calidad de señal"""
        if self.thinkgear:
            q = getattr(self.thinkgear, "signal_quality", 200)
            self.signal_quality = q
            if q == 0:
                txt = _("signal_excellent")
                color = "green"
            elif q < 100:
                txt = _("signal_good")
                color = "orange"
            else:
                txt = _("signal_poor")
                color = "red"
            self.signal_quality_var.set(f"{_('signal_quality')}: {txt}")
            self.lbl_signal_quality.config(foreground=color)
        self.root.after(1000, self._update_signal_quality)
    
    def _process_queue(self):
        """Procesa mensajes de la cola para la GUI"""
        try:
            while True:
                msg = self.queue.get_nowait()
                if msg["type"] == "log":
                    self.logs_text.config(state="normal")
                    self.logs_text.insert("end", msg["text"] + "\n")
                    self.logs_text.see("end")
                    self.logs_text.config(state="disabled")
        except queue.Empty:
            pass
        self.root.after(500, self._process_queue)
    
    def _log(self, text):
        self.queue.put({"type": "log", "text": text})
    
    def _control_loop(self):
        """Bucle principal de control que ejecuta comandos detectados"""
        last_signal_quality = 200
        while self.running:
            try:
                # Actualizar estado de conexión en UI
                if self.thinkgear and self.thinkgear.connected:
                    self.lbl_mindwave_status.config(text="ThinkGear: Conectado")
                else:
                    self.lbl_mindwave_status.config(text="ThinkGear: Desconectado")
                
                if self.bulb_controller.connected:
                    self.lbl_esp8266_status.config(text="ESP8266: Conectado")
                else:
                    self.lbl_esp8266_status.config(text="ESP8266: Desconectado")
                
                # Actualizar estado del foco
                bulb_status = self.bulb_controller.get_status()
                self.bulb_status_var.set("ENCENDIDO" if bulb_status["state"] == "on" else "APAGADO")
                self.brightness_var.set(f"{bulb_status['brightness']}%")
                
                # Cambio de color según el estado
                if bulb_status["state"] == "on":
                    self.bulb_status_label.config(foreground="green")
                else:
                    self.bulb_status_label.config(foreground="red")
                
                # Actualizar calidad de señal
                if self.thinkgear:
                    q = getattr(self.thinkgear, "signal_quality", 200)
                    if q != last_signal_quality:
                        last_signal_quality = q
                        self._log(f"{_('signal_quality')}: {q}")
                
                # Procesar comandos mentales
                command = self.processor.get_command()
                if command:
                    # Actualizar UI
                    self.commands_text.config(state="normal")
                    self.commands_text.insert("end", f"{time.strftime('%H:%M:%S')}: {command}\n")
                    self.commands_text.see("end")
                    self.commands_text.config(state="disabled")
                    
                    # Log
                    self._log(f"{time.strftime('%H:%M:%S')}: {command}")
                    
                    # Enviar comando al foco
                    if command == "foco_on":
                        self.bulb_controller.turn_on()
                    elif command == "foco_off":
                        self.bulb_controller.turn_off()
                    elif command == "ajustar_brillo":
                        self.bulb_controller.set_brightness(self.blink_brightness.get())
                
                time.sleep(0.1)
            except Exception as e:
                self._log(f"{_('error')}: {e}")
                time.sleep(1)

# Punto de entrada principal
if __name__ == "__main__":
    root = tk.Tk()
    app = BrainBulbApp(root)
    root.mainloop()