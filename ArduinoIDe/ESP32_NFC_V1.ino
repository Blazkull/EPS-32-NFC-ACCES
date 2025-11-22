#include <SPI.h>
#include <MFRC522.h>
#include <ESP32Servo.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Keypad.h>

// Pines SPI estándar para ESP32
#define SCK_PIN  18
#define MISO_PIN 19
#define MOSI_PIN 23

// Lector NFC principal
#define RST_PIN_1 17
#define SS_PIN_1 5

// Servos
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

// Crear instancia del lector
MFRC522 lector1(SS_PIN_1, RST_PIN_1);

// Servos
Servo servoPrincipal;
Servo servoSecundario;

// Pantalla LCD
LiquidCrystal_I2C lcd(LCD_DIRECCION, LCD_COLUMNAS, LCD_FILAS);

// Tarjetas autorizadas
String tarjetasAutorizadas[] = {
  "11 CD 89 A3",
  "A1 B2 C3 D4", 
  "E5 F6 78 9A",
  "B3 C4 D5 E6"
};
int numTarjetas = 4;

// Variables para control de tiempo
unsigned long ultimaLectura = 0;
const unsigned long intervaloLectura = 500;

// Variables para control de estado
String uidActual = "";
bool esperandoSeleccion = false;
bool accesoConcedidoActivo = false;

void setup() {
  Serial.begin(115200);
  Serial.println();
  Serial.println("🔧 INICIANDO SISTEMA NFC - CONTROL SEGURO");
  Serial.println("==========================================");

  // Inicializar I2C para LCD PRIMERO
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

  // Inicializar SPI DESPUÉS del I2C
  SPI.begin(SCK_PIN, MISO_PIN, MOSI_PIN);
  delay(300);

  // Inicializar lector NFC principal
  Serial.println();
  Serial.println("1. INICIALIZANDO LECTOR NFC PRINCIPAL:");
  lcd.clear();
  lcd.print("INIC. LECTOR...");

  Serial.print("   Lector Principal (SDA:5, RST:17): ");
  lector1.PCD_Init();
  delay(300);
  
  // Verificar lector sin bloquear
  if (!verificarLector(lector1, 1)) {
    lcd.clear();
    lcd.print("ERROR LECTOR!");
    lcd.setCursor(0, 1);
    lcd.print("REINICIAR...");
    delay(2000);
    ESP.restart();
  }

  // Configurar servos
  Serial.println();
  Serial.println("2. CONFIGURANDO SERVOS:");
  lcd.clear();
  lcd.print("CONFIG. SERVOS...");
  
  servoPrincipal.attach(SERVO_PRINCIPAL_PIN);
  servoSecundario.attach(SERVO_GARAJE_PIN);
  
  servoPrincipal.write(0);
  servoSecundario.write(0);
  
  Serial.println("   ✅ Servo principal listo - PIN 13");
  Serial.println("   ✅ Servo garaje listo - PIN 32");

  // Configurar LEDs
  Serial.println();
  Serial.println("3. CONFIGURANDO LEDs:");
  pinMode(LED_ROJO, OUTPUT);
  pinMode(LED_VERDE, OUTPUT);
  digitalWrite(LED_ROJO, HIGH);
  digitalWrite(LED_VERDE, LOW);
  Serial.println("   ✅ LEDs listos - Rojo ENCENDIDO");

  // Mostrar pantalla lista
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("SISTEMA SEGURO");
  lcd.setCursor(0, 1);
  lcd.print("ACERQUE TARJETA");
  
  // Mostrar instrucciones en consola
  Serial.println();
  Serial.println("🔒 SISTEMA DE ACCESO SEGURO");
  Serial.println("   1. Primero acercar tarjeta NFC válida");
  Serial.println("   2. Luego seleccionar puerta con teclado");
  Serial.println();
  Serial.println("📱 LISTO - Esperando tarjeta NFC...");
  Serial.println();
}

bool verificarLector(MFRC522 &lector, int numero) {
  byte version = lector.PCD_ReadRegister(lector.VersionReg);
  Serial.print("Versión: 0x");
  Serial.print(version, HEX);
  
  if (version == 0x00 || version == 0xFF) {
    Serial.println(" ❌ FALLÓ");
    return false;
  } else {
    Serial.println(" ✅ OK");
    return true;
  }
}

void loop() {
  // Procesar teclado solo si hay acceso concedido
  if (accesoConcedidoActivo) {
    procesarTeclado();
  }
  
  // Control de tiempo para no saturar el lector
  unsigned long tiempoActual = millis();
  if (tiempoActual - ultimaLectura >= intervaloLectura && !esperandoSeleccion) {
    procesarLectorPrincipal();
    ultimaLectura = tiempoActual;
  }
}

void procesarTeclado() {
  char tecla = keypad.getKey();
  
  if (tecla && accesoConcedidoActivo) {
    Serial.print("⌨️ Tecla presionada: ");
    Serial.println(tecla);
    
    if (tecla == '1') {
      Serial.println("🚪 Activando PUERTA PRINCIPAL...");
      activarServo(servoPrincipal, "PUERTA PRINCIPAL");
      accesoConcedidoActivo = false;
      esperandoSeleccion = false;
    } else if (tecla == '2') {
      Serial.println("🚗 Activando GARAJE...");
      activarServo(servoSecundario, "GARAJE");
      accesoConcedidoActivo = false;
      esperandoSeleccion = false;
    } else {
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("OPCION NO VALIDA");
      lcd.setCursor(0, 1);
      lcd.print("USE 1 o 2");
      delay(1500);
      mostrarMenuSeleccion();
    }
  }
}

void mostrarMenuSeleccion() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("OPCION DE ABRIR");
  lcd.setCursor(0, 1);
  lcd.print("1.PUERTA 2.GARAJE");
}

void procesarLectorPrincipal() {
  // Solo verificar presencia, no leer inmediatamente
  if (!lector1.PICC_IsNewCardPresent()) {
    return;
  }
  
  // Si hay tarjeta presente, intentar leer
  if (!lector1.PICC_ReadCardSerial()) {
    return;
  }
  
  uidActual = obtenerUID(lector1);
  Serial.print("🎯 Lector Principal detectó: ");
  Serial.println(uidActual);

  // Mostrar en LCD brevemente
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("TARJETA DETECT.");
  lcd.setCursor(0, 1);
  
  // Mostrar UID truncado
  String uidDisplay = uidActual;
  if (uidDisplay.length() > 15) {
    uidDisplay = uidDisplay.substring(0, 15);
  }
  lcd.print(uidDisplay);
  
  delay(1000);

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("VERIFICANDO...");
  delay(500);

  bool autorizada = verificarAutorizacion(uidActual);

  if (autorizada) {
    Serial.println("✅ ACCESO CONCEDIDO");
    accesoConcedido(uidActual);
  } else {
    Serial.println("❌ ACCESO DENEGADO");
    accesoDenegado(uidActual);
  }

  lector1.PICC_HaltA();
  lector1.PCD_StopCrypto1();
}

void accesoConcedido(String uid) {
  // Mostrar en LCD - Acceso concedido
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("ACCESO CONCEDIDO");
  lcd.setCursor(0, 1);
  lcd.print("ELIGE PUERTA");
  delay(3000);
  
  // Mostrar menú de selección
  mostrarMenuSeleccion();
  
  // LED: Verde ON, Rojo OFF
  digitalWrite(LED_ROJO, LOW);
  digitalWrite(LED_VERDE, HIGH);

  Serial.println();
  Serial.println("🎯 SELECCIONE OPCIÓN:");
  Serial.println("   1 → Abrir PUERTA PRINCIPAL");
  Serial.println("   2 → Abrir GARAJE");
  Serial.println();
  Serial.println("⌨️ Use el teclado para seleccionar (1 o 2)");
  
  esperandoSeleccion = true;
  accesoConcedidoActivo = true;
}

bool verificarAutorizacion(String uid) {
  for (int i = 0; i < numTarjetas; i++) {
    if (uid == tarjetasAutorizadas[i]) {
      return true;
    }
  }
  return false;
}

String obtenerUID(MFRC522 &lector) {
  String uid = "";
  for (byte i = 0; i < lector.uid.size; i++) {
    if (lector.uid.uidByte[i] < 0x10) {
      uid += "0";
    }
    uid += String(lector.uid.uidByte[i], HEX);
    if (i < lector.uid.size - 1) {
      uid += " ";
    }
  }
  uid.toUpperCase();
  return uid;
}

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
  delay(2500);

  Serial.print("🔒 Cerrando ");
  Serial.println(nombre);
  
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("CERRANDO");
  lcd.setCursor(0, 1);
  lcd.print(nombre);
  
  // Cerrar (0 grados)
  servo.write(0);
  delay(800);

  // Restaurar LEDs
  digitalWrite(LED_VERDE, LOW);
  digitalWrite(LED_ROJO, HIGH);
  
  // Volver a pantalla de espera
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("SISTEMA SEGURO");
  lcd.setCursor(0, 1);
  lcd.print("ACERQUE TARJETA");
  
  Serial.println("🔒 Sistema en espera...");
  Serial.println();
}

void accesoDenegado(String uid) {
  Serial.println("🚫 ACCESO DENEGADO");
  
  // Mostrar en LCD - Acceso denegado
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("ACCESO DENEGADO");
  lcd.setCursor(0, 1);
  lcd.print("TARJETA NO VALIDA");

  // LED rojo intermitente
  Serial.println("🔴 LED rojo intermitente...");
  for (int i = 0; i < 4; i++) {
    digitalWrite(LED_ROJO, !digitalRead(LED_ROJO));
    delay(300);
  }
  digitalWrite(LED_ROJO, HIGH);
  
  // Volver a pantalla de espera
  delay(1500);
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("SISTEMA SEGURO");
  lcd.setCursor(0, 1);
  lcd.print("ACERQUE TARJETA");
  
  Serial.println("🔒 Sistema en espera...");
  Serial.println();
}