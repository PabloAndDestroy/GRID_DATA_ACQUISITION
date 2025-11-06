import time 
import board
import busio
import json
import os 
import csv 
import requests
from datetime import datetime

# --- INA219 ---
from adafruit_ina219 import INA219
from adafruit_ina219 import Gain

# --- DHT22 ---
import adafruit_dht

# --- DS18B20 ---
from w1thermsensor import W1ThermSensor, NoSensorFoundError

# ADS1015 (ADC)
import adafruit_ads1x15.ads1015 as ADS 
from adafruit_ads1x15.analog_in import AnalogIn

# ========== FUNCIONES ==============
def calcular_irradiancia(v_out):
    """ 
    In: v_out
    Output: convierte el voltaje de la salida del amplificador a irradiancia (W/m^2)
    """
    return v_out/0.0017457 # Donde 1 W/m^2 produce ~1.7457mV a la salida.and
def calcular_velocidad_viento(v_out):
    # Convierte el voltaje del anemómetro a velocidad del viento en m/s
    if v_out < 0.5:
        return 0.0 # Fuera de rango
    elif v_out > 2.0:
        return 70.0 # Límite del sensor según datasheet. 
    return (v_out-0.4)*31.25+0.5


# ============ INICIALIZACIONES ====================

# Payload a Thingworx

# I2C Común
i2c = busio.I2C(board.SCL, board.SDA)

# INA219
ina219 = INA219(i2c, addr=0x45)
ina219.set_calibration_32V_2A()

# Crea el objeto sensor usando GPIO21
dht_sensor = adafruit_dht.DHT22(board.D25)

# ADS1015 (ADC) Dirección 0x48 (GND)
ads1 = ADS.ADS1015(i2c, adress=0x48)
ads1.gain = 1
adc1_channels = [AnalogIn(ads1, ADS.P0), AnalogIn(ads1, ADS.P1), AnalogIn(ads1,ADS.P2), AnalogIn(ads1, ADS.P3)]


# ADS1015 (ADC) - Dirección 0x49 (3.3V)
ads2  = ADS.ADS1015(i2c, adress = 0x49)
ads.gain = 1
adc2_channels = [AnalogIn(ads2, ADS.P0), AnalogIn(ads2, ADS.P1)]

# DS18B20

ds18b20_sensores = W1ThermSensor.get_available_sensors()

SENSOR_MAP = {
    "0b239e885d69", "Temperatura_L1_1", #[1,1]
    "0623b2125e5e", "Temperatura_L1_2", #[1,2]
    "0823c06e945c", "Temperatura_L1_3", # [1,3]
    "0b239ecbbf1c", "Temperatura_L1_4", #[1,4]
    "0623c39ba7d6", "Temperatura_L1_5", #[1,5]
    "0b244071d0be", "Temperatura_L2_1", # [2,1]
    "0b2440059058", "Temperatura_L2_2", # [2,2]
    "0623c37c205d", "Temperatura_L2_3", # [2,3]
    "0623c3da8e07", "Temperatura_L2_4", # [2,4]
    "0b244009af8d", "Temperatura_L2_5", # [2,5]
    "0b24406a0d27", "Temperatura_L3_1", # [3,1]
    "0b2440d98a92", "Temperatura_L3_2", # [3,2]
    "0b2440007268", "Temperatura_L3_3", # [3,3]
    "0b24400afba2", "Temperatura_L3_4", # [3,4]
    "0b24404a8242", "Temperatura_L3_5", # [3,5]
}

# === LOOP PRINCIPAL ===
try while True:
    print("\n==== LECTURA DE SENSORES=====")
    
    # INA219
    try:
        bus_v = ina219.bus_voltage
        shunt_v = ina219.shunt_voltage
        current_A = ina219.current*10
        power_W = ina219.power
        payload["Bus_V "] = round(bus_v, 2)
        payload["Shunt_V"] = round(shunt_v,3)
        payload["Corriente_mA"] = round(current_A, 3)
        payload["Potencia_W"] = rouns(power_W, 3)
        print(f"[INA219] Bus: {bus_v:.2f} V | Shunt: {shunt_v:.3f} V ° Corriente: {current_A:.3f} mA | Potencia: {power_W:.3f} W")
    except Exception as e:
        print("[INA219] error: " e)
    
    # DHT22
    try:
        temperatura_ambiente = dht_sensor. temperature 
        humedad = dht_sensor.humidity 
        if temperatura_ambiente is not None and humedad is not None: 
            payload["Temperatura_Ambiente"] = round(temperatura_ambiente, 2)
            payload["Humedad"] = round(humedad, 2)
            print(f"[DHT22] Temp: {temperatura_ambiente:.1f} °C | Humedad: {humedad:.1f} %")
        else:
            print("[DHT22] Lectura invalida")
        
    
    # ADS1015
    print("ADC #1 - 0x48")
    for i, chan in enumerate(adc1_channels):
        volt = chan.bus_voltage 
        if i in [1]:
            ajuste = 0.145
            valor_psi_0 = (200/(4.5-ajuste))* ((volt*((39000+100000)/100000))-ajuste)
            payload["Presion_IN"] = round(valor_psi_0, 2)
            print(f" Canal {i}: {volt:.3f} V (raw: {chan.value}) -> Valor en psi: {valor_psi_0:.2f}")
        elif i in [2]:
            ajuste = 0.434
            valor_psi_1 = (200/(4.5-ajuste))*((volt*((39000+100000)/100000))-ajuste)
            payload["Presion_out"] = round(valor_psi_1, 2)
            print(f" Canal {i}: {volt:.3f} V (raw: {chan.value}) -> Valor en psi: {valor_psi_1:.2f}")
        elif i in [3]:
            velocidad_viento = calcular_velocidad_viento(volt)
            payload["Velocidad_Viento"] = round(velocidad_viento, 2)
            print(f" Canal {i}: {volt:.3f} V (raw: {chan.value}) -> {velocidad_viento:.2f} m/s")
        else:
            print(f" Canal {i}: {volt:.3f} V (raw: {chan.value})")
        
        # ADS1015 #2 (0x49)
        
        print("[ADC #2 -0X49]")
        for i, chan in enumerate(adc2_channels):
            volt = chan.voltage 
            if i in [0]:
                irradiancia = calcular_irradiancia(volt)
                payload["Irradiancia"] = round(irradiancia, 2)
                print(f" Canal {i}: {volt:.3f} V (raw: {chan.value}) -> {irradiancia:.2f} W/m^2")
            elif i in [1]:
                volt_adc2_1 = volt/0.0796
                payload["Sensor_Voltaje"] = round(volt_adc2_1, 2)
                print(f" Canal {i}: {volt_adc2_1:.3f} V (raw: {chan.value})")
            else:
                print(f" Canal {i}: {volt:.3f} V (raw: {chan.value})")
                
    for sensor in ds18b20_sensores:
        try:
            sensor_id = sensor.id 
            temp_c = sensor.get_temperature()
            nombre = SENSOR_MAP.get(sensor_id, f"sensor_{sensor_id[-5:]}")
            payload[nombre] = round(temp_c,2)
            print(f"[DS18B20] {nombre}: {temp_c:.2f} °C")
            print(f"Sensor ID: {sensor_id}")
        except NoSensorFoundError:
            print(f"[DS1820] Sensor {sensor.id}: error al leer")
            
    
    # ============= IOT =======================0
    THINGWORX_HOST = "https://iot.dis.eafit.edu.co/Thingworx/Things/Proyecto_DIST_Fachada/Services/traductor"
    THINGWORX_APP_KEY ="d907d4e2-ccfa-4198-86f6-96e490d75da7"
    HEADERS = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "appKey": THINGWORX_APP_KEY
    }
    body = {"payload": payload}
    
    try: 
        print("JSON que se enviará al servicio 'traductor'")
        print(json.dumps(body, indent = 2))
        response = request.post(THINGWORX_HOST, headers = HEADERS, json = body, timeout = 10)
        if response.status_code != 200:
            print(f"Error al enviar datos a Thingworx: {response.status_code} - {response.text}")
        else:
            print(" Datos enviados correctamente al servicio 'traductor'")
        except requests.RequestException as e:
            print(f" Excepción de red al enviar datos: {e}")
    try:
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop", "datos_sensores.txt")
        with open(desktop_path, "a") as file:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            file.write(f"\[{timestamp}] {json.dumps(payload)}")
            print(f"Payload guardado en {desktop_path}")
    except Exception as e:
        print(f"Error al guardar el archivo: {e}")
        time.sleep(3)
        
        
except KeyboardInterrupt:
    print("\nLectura finalizada por el usuario.")
finally: 
    dht_sensor.exit()
                
            
