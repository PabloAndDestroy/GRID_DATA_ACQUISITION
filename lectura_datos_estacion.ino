#include <Wire.h>
#include <Adafruit_ADS1X15.h>
#include <HardwareSerial.h>

// UARTs
HardwareSerial RS485_PIRA(1);   // UART1: piranómetro (GPIO19 TX1, GPIO18 RX1)
HardwareSerial WS3(2);          // UART2: estación WS3 (solo RX)

// Pines (ajusta si en tu montaje son otros)
#define RX1_PIRA 18
#define TX1_PIRA 19
#define SDA      21
#define SCL      22
#define RX_WS3   16   // WS3 solo RX por UART2; TX_WS3 no usado
#define TX_WS3   -1

Adafruit_ADS1115 ads;
float ws3v[4] = {0};   // Dir, Temp, Hum, Pres
float adcV[4] = {0};   // W, Corriente (V), Voltaje (V), Extra (V)
int   solar_p = 0;
char  output[80];

// --------- CRC16 Modbus ---------
uint16_t crc16_modbus(const uint8_t *d, uint8_t n){
  uint16_t c=0xFFFF; while(n--){ c^=*d++; for(int j=0;j<8;j++) c=(c&1)?(c>>1)^0xA001:c>>1; } return c;
}
bool validateCRC(uint8_t *data, uint16_t len){
  if(len<3) return false; uint16_t rx=(uint16_t(data[len-1])<<8)|data[len-2]; return rx==crc16_modbus(data,len-2);
}

// --------- Piranómetro (UART1 RS485) ---------
void sendRS485Command(uint8_t addr){
  uint8_t cmd[6]={addr,0x03,0x00,0x00,0x00,0x01};
  uint16_t crc=crc16_modbus(cmd,6);
  uint8_t tx[8]={cmd[0],cmd[1],cmd[2],cmd[3],cmd[4],cmd[5],uint8_t(crc&0xFF),uint8_t(crc>>8)};
  RS485_PIRA.write(tx,8); RS485_PIRA.flush();
}
int readRS485Response(){
  uint8_t r[7]; unsigned long t0=millis(); int i=0;
  while(millis()-t0<600){ if(RS485_PIRA.available()){ i+=RS485_PIRA.readBytes(r+i,7-i); if(i>=7) break; } }
  if(i!=7 || !validateCRC(r,7)) return 0;
  return (int(r[3])<<8)|r[4]; // HI,LO
}
int leerPiranometro(){ sendRS485Command(0x02); return readRS485Response(); } // ajusta 0x02 si tu esclavo es otro

// --------- WS3 por UART2 (solo RX) ---------
void leerEstacion(float a[]){
  String t;
  while(WS3.available()) WS3.read();
  delay(1000);
  while(WS3.available()) t = WS3.readStringUntil('\n');
  if(!t.startsWith("c")){ a[0]=a[1]=a[2]=a[3]=0; return; }
  a[0] = t.substring(1,4).toInt();            // Dir
  int tf = t.substring(13,16).toInt();        // Temp F
  a[1] = (tf - 32) * 5.0f/9.0f;               // °C
  a[2] = t.substring(25,27).toInt();          // Hum %
  
  int pr = t.substring(28,33).toInt();        // pres*100
  a[3] = pr / 100.0f;                         // kPa
}

// --------- Helper: lectura “fresca” por canal con ganancia ---------
static inline float readVolts(adsGain_t g, uint8_t ch){
  ads.setGain(g);
  (void)ads.readADC_SingleEnded(ch);          // dummy: descarta conversión previa
  int16_t raw = ads.readADC_SingleEnded(ch);  // conversión válida con g
  return ads.computeVolts(raw);               // en voltios según g activo
}

// --------- ADS1115 ---------
void leerAdc(float a[]){
  // Lee cada canal con su ganancia adecuada
  float v_a0 = readVolts(GAIN_TWO,        0); // anemómetro (0.4–2.0 V)
  float v_a1 = readVolts(GAIN_ONE,        1); // corriente
  float v_a2 = readVolts(GAIN_ONE,        2); // voltaje
  float v_a3 = readVolts(GAIN_TWOTHIRDS,  3); // extra

  // ---- Cálculo de velocidad de viento (W, m/s) ----
  const float vMin=0.415f, vMax=2.0f, wMax=32.0f;
  float W = (v_a0 <= vMin) ? 0.0f : (v_a0 - vMin) * (wMax / (vMax - vMin));
  float V_out = v_a2 * 6.25;
  float A_out = (v_a1-2.5f)/0.066f;
  Serial.println("/////////////////////////////////////////////");


  a[0] = W;
  a[1] = A_out;
  a[2] =V_out;
  a[3] = v_a3;
}

// --------- Trama ---------
void enviarDatos(){
  snprintf(output, sizeof(output),
    "S%04d;W%04.1f;D%03.0f;T%04.1f;H%02.0f;P%05.2f;V%04.2f;C%02.3f;E%05.2f",
    solar_p, adcV[0], ws3v[0], ws3v[1], ws3v[2], ws3v[3], adcV[2], adcV[1], adcV[3]);
  Serial.println(output);
}

// --------- Modo auto (muestreo periódico) ---------
bool autoMode=false;
unsigned long t0=0;
unsigned long period=500; // ms

void setup(){
  Serial.begin(115200);
  Serial.setTimeout(300);
  

  RS485_PIRA.begin(9600, SERIAL_8N1, RX1_PIRA, TX1_PIRA);
  WS3.begin(9600, SERIAL_8N1, RX_WS3, TX_WS3);

  Wire.begin(SDA, SCL);
  if(!ads.begin()){
    Serial.println("ERROR: ADS1115 no encontrado");
  }

  Serial.println("Listo. Escribe 'read' (una vez), 'auto on' o 'auto off'.");
}

void cicloLecturaYEnvio(){
  int v = leerPiranometro();
  //Serial.printf("[PIRA] raw=%d\n", v);
  solar_p = v;

  leerEstacion(ws3v);
  leerAdc(adcV);


  enviarDatos();
}

void loop(){
  
 
    String com = Serial.readStringUntil('\n'); com.trim();
    cicloLecturaYEnvio();
    autoMode = true;
    //if(com=="read"){
      //cicloLecturaYEnvio();
    //} else if(com=="auto on"){
      //autoMode = true; // Serial.println("AUTO ON");
   /* } else if(com=="auto off"){
      autoMode = false; Serial.println("AUTO OFF");
    } else if(com.startsWith("period ")){
      int p = com.substring(7).toInt();
      if(p >= 100) { period = (unsigned long)p; Serial.printf("Periodo=%lu ms\n", period); }
      else Serial.println("Periodo minimo 100 ms");
    }*/
  
  

  if(autoMode && millis()-t0 >= period){
    t0 = millis();
    cicloLecturaYEnvio();
  }
}
