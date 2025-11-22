#include <SPI.h>
#include <MFRC522.h>
#include <ESP32Servo.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Keypad.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <WebSocketsClient.h>

// ================== CONFIGURACIÓN WIFI ==================
const char* ssid = "FMLA ACOSTA_EXT";
const char* password = "Acost@333";
const char* API_HOST = "192.168.1.120";
const uint16_t API_PORT = 8000;
const String API_BASE = String("http://") + API_HOST + ":" + String(API_PORT);

// ================== PINES ESP32 ==================
// Pines SPI para NFC
#define SCK_PIN  18
#define MISO_PIN 19
#define MOSI_PIN 23

// Lector NFC
#define RST_PIN_1 17
#define SS_PIN_1 5

// Servomotores
#define SERVO_PRINCIPAL_PIN 13
#define SERVO_GARAJE_PIN 32

// LEDs
#define LED_VERDE 12
#define LED_ROJO 21

// Configuración LCD I2C
#define LCD_SDA 4
#define LCD_SCL 15
#define LCD_DIRECCION 0x27
#define LCD_COLUMNAS 16
#define LCD_FILAS 2

// ================== TECLADO ==================
const byte rowsCount = 3;
const byte columsCount = 3;
char keys[rowsCount][columsCount] = {
  { '1', '2', '3' },
  { '4', '5', '6' },
  { '7', '8', '9' }
};
byte rowPins[rowsCount] = { 14, 27, 26 };
byte columnPins[columsCount] = { 25, 33, 22 };
Keypad keypad = Keypad(makeKeymap(keys), rowPins, columnPins, rowsCount, columsCount);

// ================== VARIABLES GLOBALES ==================
WebSocketsClient webSocket;
LiquidCrystal_I2C lcd(LCD_DIRECCION, LCD_COLUMNAS, LCD_FILAS);
MFRC522 lector1(SS_PIN_1, RST_PIN_1);
Servo servoPrincipal;
Servo servoSecundario;

// Estados del sistema
String tokenActual = "";
String userName = "";
bool logeado = false;
bool sistemaActivo = true;
bool modoEmergencia = false;
bool esperandoTarjetaRegistro = false;
int usuarioRegistroId = 0;
String nombreTarjetaRegistro = "";

// Control de tiempo
unsigned long ultimaLectura = 0;
const unsigned long intervaloLectura = 500;
unsigned long lastConnectionCheck = 0;
const unsigned long connectionCheckInterval = 10000;

// Variables para login manual
bool loginManualActivo = false;
String inputPin = "";
int intentosLogin = 0;
const int maxIntentos = 3;

// ================== SETUP ==================
void setup() {
  Serial.begin(115200);
  Serial.println();
  Serial.println("🚀 INICIANDO SISTEMA NFC - CONTROL DE ACCESO INTELIGENTE");
  Serial.println("========================================================");

  // Inicializar I2C para LCD
  Wire.begin(LCD_SDA, LCD_SCL);
  
  // Inicializar LCD
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(" INICIANDO...");
  lcd.setCursor(0, 1);
  lcd.print("SISTEMA SEGURO");
  delay(1000);

  // Inicializar SPI para NFC
  SPI.begin(SCK_PIN, MISO_PIN, MOSI_PIN);
  delay(300);

  // Inicializar lector NFC
  Serial.println("1. INICIALIZANDO LECTOR NFC:");
  lcd.clear();
  lcd.print("INIC. LECTOR...");

  lector1.PCD_Init();
  delay(300);
  
  if (!verificarLector(lector1)) {
    lcd.clear();
    lcd.print("ERROR LECTOR!");
    lcd.setCursor(0, 1);
    lcd.print("REINICIAR...");
    delay(2000);
    ESP.restart();
  }

  // Configurar servomotores
  Serial.println("2. CONFIGURANDO SERVOMOTORES:");
  lcd.clear();
  lcd.print("CONFIG. SERVOS...");
  
  servoPrincipal.attach(SERVO_PRINCIPAL_PIN);
  servoSecundario.attach(SERVO_GARAJE_PIN);
  
  servoPrincipal.write(0);  // Cerrado
  servoSecundario.write(0); // Cerrado
  
  Serial.println("   ✅ Servo principal listo - PIN 13");
  Serial.println("   ✅ Servo garaje listo - PIN 32");

  // Configurar LEDs
  Serial.println("3. CONFIGURANDO LEDs:");
  pinMode(LED_ROJO, OUTPUT);
  pinMode(LED_VERDE, OUTPUT);
  digitalWrite(LED_ROJO, HIGH);  // Rojo encendido (sistema bloqueado)
  digitalWrite(LED_VERDE, LOW);
  Serial.println("   ✅ LEDs listos - Rojo ENCENDIDO");

  // Conectar WiFi
  conectarWiFi();

  // Configurar WebSocket
  configurarWebSocket();

  // Pantalla inicial
  mostrarPantallaInicial();
  
  Serial.println();
  Serial.println("🔒 SISTEMA DE ACCESO SEGURO LISTO");
  Serial.println("   Opciones de acceso:");
  Serial.println("   1. Tarjeta NFC válida");
  Serial.println("   2. PIN manual (teclado)");
  Serial.println("   3. Control remoto (App Web)");
  Serial.println();
}

// ================== LOOP PRINCIPAL ==================
void loop() {
  webSocket.loop();

  // Verificar conexión periódicamente
  if (millis() - lastConnectionCheck >= connectionCheckInterval) {
    lastConnectionCheck = millis();
    verificarConexiones();
  }

  // Procesar teclado si está activo el login manual
  if (loginManualActivo) {
    procesarTecladoLogin();
  } else if (logeado && sistemaActivo) {
    // Si está logeado y el sistema está activo, procesar selección de puerta
    procesarSeleccionPuerta();
  } else {
    // Si no está logeado, procesar NFC y opciones de acceso
    procesarAcceso();
  }

  // Procesar registro de tarjeta si está activo
  if (esperandoTarjetaRegistro) {
    procesarRegistroTarjeta();
  }
}

// ================== FUNCIONES WIFI ==================
void conectarWiFi() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Conectando WiFi");
  
  WiFi.begin(ssid, password);
  unsigned long startAttempt = millis();

  while (WiFi.status() != WL_CONNECTED && millis() - startAttempt < 15000) {
    delay(500);
    lcd.print(".");
    Serial.print(".");
  }

  if (WiFi.status() != WL_CONNECTED) {
    lcd.clear();
    lcd.print("WIFI NO CONECTADO");
    Serial.println("\n[ERROR] No se pudo conectar al WiFi");
    // Continuar sin WiFi en modo local
    sistemaActivo = false;
    return;
  }

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("WiFi OK");
  lcd.setCursor(0, 1);
  lcd.print(WiFi.localIP());
  Serial.println("\n[OK] WiFi conectado con IP: " + WiFi.localIP().toString());
  delay(2000);
}

void verificarConexiones() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WIFI] ⚠️ Reconectando WiFi...");
    conectarWiFi();
  }
  
  if (!webSocket.isConnected()) {
    Serial.println("[WS] ⚠️ Reconectando WebSocket...");
    webSocket.begin(API_HOST, API_PORT, "/ws/device/1");
  }
}

// ================== FUNCIONES WEBSOCKET ==================
void configurarWebSocket() {
  webSocket.begin(API_HOST, API_PORT, "/ws/device/1");
  webSocket.onEvent(webSocketEvent);
  webSocket.setReconnectInterval(5000);
  webSocket.enableHeartbeat(15000, 3000, 2);
  
  Serial.println("[WS] 🔄 WebSocket configurado");
}

void webSocketEvent(WStype_t type, uint8_t* payload, size_t length) {
  switch (type) {
    case WStype_DISCONNECTED:
      Serial.println("[WS] 🔌 Desconectado");
      break;

    case WStype_CONNECTED:
      Serial.println("[WS] ✅ Conectado al servidor");
      // Autenticar si tenemos token
      if (tokenActual != "") {
        String authMsg = "{\"type\":\"auth\",\"token\":\"" + tokenActual + "\"}";
        webSocket.sendTXT(authMsg);
        Serial.println("[WS] 🔐 Enviando autenticación");
      }
      break;

    case WStype_TEXT:
      {
        Serial.printf("[WS] 📩 Mensaje recibido: %s\n", payload);
        procesarMensajeWebSocket(payload, length);
        break;
      }

    case WStype_ERROR:
      Serial.println("[WS] ❌ Error en WebSocket");
      break;

    default:
      break;
  }
}

void procesarMensajeWebSocket(uint8_t* payload, size_t length) {
  DynamicJsonDocument doc(1024);
  DeserializationError error = deserializeJson(doc, payload, length);
  
  if (error) {
    Serial.println("[WS] ❌ Error parse JSON");
    return;
  }

  String tipo = doc["type"] | "";
  String event = doc["event"] | "";

  // Login desde app web
  if (tipo == "login" || tipo == "auth_success") {
    bool success = doc["success"] | false;
    
    if (success) {
      if (doc.containsKey("token")) {
        tokenActual = doc["token"].as<String>();
      }
      
      if (doc.containsKey("user")) {
        JsonObject user = doc["user"];
        if (user.containsKey("name")) {
          userName = user["name"].as<String>();
        }
      } else if (doc.containsKey("name")) {
        userName = doc["name"].as<String>();
      }

      logeado = true;
      intentosLogin = 0;
      
      mostrarMensajeLCD("LOGIN EXITOSO", "Bienvenido " + userName, 2000);
      mostrarMenuPrincipal();
      
      Serial.println("[WS] 👤 Login exitoso - Usuario: " + userName);
    }
  }
  
  // Acciones desde el backend
  else if (event == "new_action" || tipo == "action" || tipo == "action_execute") {
    String actionType = doc["action_type"] | doc["type"] | "";
    String command = doc["command"] | "";
    int actionId = doc["action_id"] | doc["id"] | 0;

    Serial.printf("[WS] ⚡ Acción recibida: %s (ID:%d)\n", actionType.c_str(), actionId);

    if (actionType == "DOOR_OPEN" || command == "DOOR_OPEN") {
      activarServo(servoPrincipal, "PUERTA PRINCIPAL");
      confirmarAccion(actionId);
    } 
    else if (actionType == "GARAGE_OPEN" || command == "GARAGE_OPEN") {
      activarServo(servoSecundario, "GARAJE");
      confirmarAccion(actionId);
    }
    else if (actionType == "SYSTEM_LOCK" || command == "SYSTEM_LOCK") {
      sistemaActivo = false;
      modoEmergencia = true;
      mostrarMensajeLCD("SISTEMA BLOQUEADO", "Modo Emergencia", 3000);
      digitalWrite(LED_ROJO, HIGH);
      digitalWrite(LED_VERDE, LOW);
    }
    else if (actionType == "SYSTEM_UNLOCK" || command == "SYSTEM_UNLOCK") {
      sistemaActivo = true;
      modoEmergencia = false;
      mostrarMensajeLCD("SISTEMA ACTIVO", "Acceso Permitido", 3000);
      digitalWrite(LED_ROJO, LOW);
    }
    else if (actionType == "NFC_DISABLE" || command == "NFC_DISABLE") {
      sistemaActivo = false;
      mostrarMensajeLCD("LECTOR NFC", "DESACTIVADO", 3000);
    }
    else if (actionType == "NFC_ENABLE" || command == "NFC_ENABLE") {
      sistemaActivo = true;
      mostrarMensajeLCD("LECTOR NFC", "ACTIVADO", 3000);
    }
  }
  
  // Registro de tarjeta NFC
  else if (tipo == "nfc_registration") {
    usuarioRegistroId = doc["user_id"] | 0;
    nombreTarjetaRegistro = doc["card_name"] | "";
    esperandoTarjetaRegistro = true;
    
    mostrarMensajeLCD("REGISTRO TARJETA", "Acerca tarjeta NFC", 0);
    Serial.println("[NFC] 📝 Modo registro activado");
  }
}

// ================== FUNCIONES NFC ==================
bool verificarLector(MFRC522 &lector) {
  byte version = lector.PCD_ReadRegister(lector.VersionReg);
  Serial.print("Versión Lector: 0x");
  Serial.print(version, HEX);
  
  if (version == 0x00 || version == 0xFF) {
    Serial.println(" ❌ FALLÓ");
    return false;
  } else {
    Serial.println(" ✅ OK");
    return true;
  }
}

void procesarAcceso() {
  // Procesar NFC cada intervalo
  unsigned long tiempoActual = millis();
  if (tiempoActual - ultimaLectura >= intervaloLectura) {
    procesarNFC();
    ultimaLectura = tiempoActual;
  }
  
  // Procesar teclado para login manual
  char tecla = keypad.getKey();
  if (tecla && !loginManualActivo) {
    if (tecla == '*') {  // Tecla * para login manual
      iniciarLoginManual();
    }
  }
}

void procesarNFC() {
  if (!lector1.PICC_IsNewCardPresent()) return;
  if (!lector1.PICC_ReadCardSerial()) return;
  
  String uid = obtenerUID(lector1);
  Serial.print("🎯 Tarjeta detectada: ");
  Serial.println(uid);

  // Mostrar en LCD
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("TARJETA DETECT.");
  lcd.setCursor(0, 1);
  
  String uidDisplay = uid;
  if (uidDisplay.length() > 15) uidDisplay = uidDisplay.substring(0, 15);
  lcd.print(uidDisplay);
  
  delay(1000);

  // Verificar con backend
  validarTarjetaNFC(uid);
  
  lector1.PICC_HaltA();
  lector1.PCD_StopCrypto1();
}

String obtenerUID(MFRC522 &lector) {
  String uid = "";
  for (byte i = 0; i < lector.uid.size; i++) {
    if (lector.uid.uidByte[i] < 0x10) uid += "0";
    uid += String(lector.uid.uidByte[i], HEX);
    if (i < lector.uid.size - 1) uid += " ";
  }
  uid.toUpperCase();
  return uid;
}

void validarTarjetaNFC(String uid) {
  if (!sistemaActivo) {
    mostrarMensajeLCD("SISTEMA", "INACTIVO", 2000);
    mostrarPantallaInicial();
    return;
  }

  if (WiFi.status() != WL_CONNECTED) {
    mostrarMensajeLCD("ERROR CONEXION", "Sin WiFi", 2000);
    mostrarPantallaInicial();
    return;
  }

  lcd.clear();
  lcd.print("VALIDANDO...");
  
  HTTPClient http;
  String url = API_BASE + "/nfc-cards/validate?card_uid=" + uid;
  http.begin(url);
  
  int httpCode = http.GET();
  Serial.printf("[NFC] HTTP Code: %d\n", httpCode);
  
  if (httpCode == 200) {
    String response = http.getString();
    DynamicJsonDocument doc(512);
    deserializeJson(doc, response);
    
    bool valid = doc["valid"];
    String message = doc["message"];
    
    if (valid) {
      String userName = doc["user"]["name"] | "Usuario";
      logeado = true;
      intentosLogin = 0;
      
      // LEDs: Verde ON, Rojo OFF
      digitalWrite(LED_ROJO, LOW);
      digitalWrite(LED_VERDE, HIGH);
      
      mostrarMensajeLCD("ACCESO CONCEDIDO", "Bienvenido " + userName, 3000);
      mostrarMenuPrincipal();
      
      Serial.println("✅ Acceso concedido via NFC: " + userName);
    } else {
      // LEDs: Rojo intermitente
      for (int i = 0; i < 4; i++) {
        digitalWrite(LED_ROJO, !digitalRead(LED_ROJO));
        delay(300);
      }
      digitalWrite(LED_ROJO, HIGH);
      
      mostrarMensajeLCD("ACCESO DENEGADO", message, 3000);
      mostrarPantallaInicial();
      
      Serial.println("❌ Acceso denegado: " + message);
    }
  } else {
    mostrarMensajeLCD("ERROR", "Servicio no disp.", 2000);
    mostrarPantallaInicial();
  }
  
  http.end();
}

// ================== REGISTRO DE TARJETA NFC ==================
void procesarRegistroTarjeta() {
  if (!lector1.PICC_IsNewCardPresent()) return;
  if (!lector1.PICC_ReadCardSerial()) return;
  
  String uid = obtenerUID(lector1);
  Serial.print("🎯 Tarjeta para registro: ");
  Serial.println(uid);
  
  registrarTarjetaEnBackend(uid);
  
  lector1.PICC_HaltA();
  lector1.PCD_StopCrypto1();
}

void registrarTarjetaEnBackend(String uid) {
  HTTPClient http;
  String url = API_BASE + "/nfc-cards/";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("Authorization", "Bearer " + tokenActual);
  
  DynamicJsonDocument doc(512);
  doc["card_uid"] = uid;
  doc["id_user"] = usuarioRegistroId;
  doc["card_name"] = nombreTarjetaRegistro;
  doc["status"] = true;
  
  String requestBody;
  serializeJson(doc, requestBody);
  
  int httpCode = http.POST(requestBody);
  
  if (httpCode == 200 || httpCode == 201) {
    mostrarMensajeLCD("TARJETA REGISTRADA", "EXITOSAMENTE", 3000);
    Serial.println("✅ Tarjeta registrada exitosamente");
  } else {
    mostrarMensajeLCD("ERROR REGISTRO", "Intentar nuevamente", 3000);
    Serial.println("❌ Error registrando tarjeta");
  }
  
  http.end();
  
  // Resetear estado de registro
  esperandoTarjetaRegistro = false;
  usuarioRegistroId = 0;
  nombreTarjetaRegistro = "";
  mostrarPantallaInicial();
}

// ================== LOGIN MANUAL CON PIN ==================
void iniciarLoginManual() {
  loginManualActivo = true;
  inputPin = "";
  intentosLogin++;
  
  lcd.clear();
  lcd.print("INGRESE PIN (6 dig):");
  lcd.setCursor(0, 1);
  lcd.print("> ");
  
  Serial.println("🔑 Modo login manual activado");
}

void procesarTecladoLogin() {
  char tecla = keypad.getKey();
  
  if (!tecla) return;
  
  if (tecla == '#') {  // Tecla # para enviar
    if (inputPin.length() == 6) {
      validarPinManual(inputPin);
    } else {
      mostrarMensajeLCD("PIN INCOMPLETO", "6 digitos requeridos", 2000);
      iniciarLoginManual();
    }
  } 
  else if (tecla == '*') {  // Tecla * para cancelar
    loginManualActivo = false;
    mostrarPantallaInicial();
    Serial.println("🔑 Login manual cancelado");
  }
  else if (isdigit(tecla)) {  // Solo aceptar dígitos
    if (inputPin.length() < 6) {
      inputPin += tecla;
      lcd.setCursor(2 + inputPin.length() - 1, 1);
      lcd.print("*");
    }
  }
}

void validarPinManual(String pin) {
  if (!sistemaActivo) {
    mostrarMensajeLCD("SISTEMA", "INACTIVO", 2000);
    loginManualActivo = false;
    mostrarPantallaInicial();
    return;
  }

  if (intentosLogin >= maxIntentos) {
    mostrarMensajeLCD("BLOQUEADO", "Max intentos", 5000);
    loginManualActivo = false;
    sistemaActivo = false;
    mostrarPantallaInicial();
    return;
  }

  lcd.clear();
  lcd.print("VALIDANDO PIN...");
  
  HTTPClient http;
  String url = API_BASE + "/access-pins/validate?pin_code=" + pin;
  http.begin(url);
  
  int httpCode = http.GET();
  Serial.printf("[PIN] HTTP Code: %d\n", httpCode);
  
  if (httpCode == 200) {
    String response = http.getString();
    DynamicJsonDocument doc(512);
    deserializeJson(doc, response);
    
    bool valid = doc["valid"];
    String message = doc["message"];
    
    if (valid) {
      String userName = doc["user"]["name"] | "Usuario";
      logeado = true;
      intentosLogin = 0;
      loginManualActivo = false;
      
      // LEDs: Verde ON, Rojo OFF
      digitalWrite(LED_ROJO, LOW);
      digitalWrite(LED_VERDE, HIGH);
      
      mostrarMensajeLCD("ACCESO CONCEDIDO", "Bienvenido " + userName, 3000);
      mostrarMenuPrincipal();
      
      Serial.println("✅ Acceso concedido via PIN: " + userName);
    } else {
      intentosLogin++;
      mostrarMensajeLCD("PIN INCORRECTO", "Intentos: " + String(intentosLogin), 3000);
      
      if (intentosLogin < maxIntentos) {
        iniciarLoginManual();
      } else {
        mostrarMensajeLCD("BLOQUEADO", "Contacte admin", 5000);
        loginManualActivo = false;
        sistemaActivo = false;
        mostrarPantallaInicial();
      }
    }
  } else {
    mostrarMensajeLCD("ERROR", "Servicio no disp.", 2000);
    iniciarLoginManual();
  }
  
  http.end();
}

// ================== SELECCIÓN DE PUERTA ==================
void procesarSeleccionPuerta() {
  char tecla = keypad.getKey();
  
  if (tecla) {
    Serial.print("⌨️ Tecla presionada: ");
    Serial.println(tecla);
    
    if (tecla == '1') {
      abrirPuertaPrincipal();
    } 
    else if (tecla == '2') {
      abrirGaraje();
    }
    else if (tecla == '*') {
      // Logout
      logout();
    }
    else {
      mostrarMensajeLCD("OPCION NO VALIDA", "Use 1, 2 o *", 1500);
      mostrarMenuPrincipal();
    }
  }
}

void abrirPuertaPrincipal() {
  Serial.println("🚪 Activando PUERTA PRINCIPAL...");
  enviarAccionBackend("DOOR_OPEN");
  activarServo(servoPrincipal, "PUERTA PRINCIPAL");
}

void abrirGaraje() {
  Serial.println("🚗 Activando GARAJE...");
  enviarAccionBackend("GARAGE_OPEN");
  activarServo(servoSecundario, "GARAJE");
}

void logout() {
  logeado = false;
  userName = "";
  tokenActual = "";
  
  digitalWrite(LED_VERDE, LOW);
  digitalWrite(LED_ROJO, HIGH);
  
  mostrarMensajeLCD("SESION CERRADA", "Hasta pronto!", 2000);
  mostrarPantallaInicial();
  
  Serial.println("🔒 Sesión cerrada");
}

// ================== CONTROL SERVOMOTORES ==================
void activarServo(Servo &servo, String nombre) {
  Serial.print("🔓 Abriendo ");
  Serial.println(nombre);
  
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("ABRIENDO");
  lcd.setCursor(0, 1);
  lcd.print(nombre);
  
  // Abrir (90 grados)
  servo.write(90);
  delay(3000);

  Serial.print("🔒 Cerrando ");
  Serial.println(nombre);
  
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("CERRANDO");
  lcd.setCursor(0, 1);
  lcd.print(nombre);
  
  // Cerrar (0 grados)
  servo.write(0);
  delay(1000);

  // Restaurar pantalla
  if (logeado) {
    mostrarMenuPrincipal();
  } else {
    mostrarPantallaInicial();
  }
  
  Serial.println("✅ Operación completada");
}

// ================== COMUNICACIÓN BACKEND ==================
void enviarAccionBackend(String tipoAccion) {
  if (WiFi.status() != WL_CONNECTED) return;
  if (tokenActual == "") return;

  HTTPClient http;
  String url = API_BASE + "/actions/";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("Authorization", "Bearer " + tokenActual);

  DynamicJsonDocument doc(256);
  doc["id_device"] = 1;
  doc["action"] = tipoAccion;
  
  String body;
  serializeJson(doc, body);

  Serial.println("[ACTION] Enviando: " + body);

  int code = http.POST(body);
  Serial.printf("[ACTION] HTTP Code: %d\n", code);

  http.end();
}

void confirmarAccion(int actionId) {
  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  String url = API_BASE + "/actions/device/confirm/" + String(actionId);
  http.begin(url);
  
  int code = http.POST("");
  Serial.printf("[CONFIRM] Acción %d confirmada - HTTP: %d\n", actionId, code);
  
  http.end();
}

// ================== INTERFAZ LCD ==================
void mostrarPantallaInicial() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("SISTEMA ACCESO NFC");
  lcd.setCursor(0, 1);
  
  if (!sistemaActivo) {
    lcd.print("🔴 SISTEMA INACTIVO");
  } else if (modoEmergencia) {
    lcd.print("🚨 MODO EMERGENCIA");
  } else {
    lcd.print("*=PIN  ||  NFC->");
  }
}

void mostrarMenuPrincipal() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("ELIJA OPCION:");
  lcd.setCursor(0, 1);
  lcd.print("1.PUERTA 2.GARAJE");
}

void mostrarMensajeLCD(String linea1, String linea2, unsigned long duracion) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(linea1);
  lcd.setCursor(0, 1);
  lcd.print(linea2);
  
  if (duracion > 0) {
    delay(duracion);
  }
}