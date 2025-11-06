import serial
import csv
import time
import os
from datetime import datetime

def read_serial_data(port='/dev/ttyUSB0', baudrate=9600, timeout=1):
    try:
        ser = serial.Serial(port, baudrate, timeout=timeout)
        print(f"Listening on {port} at {baudrate} baud...")

        while True:
            ser.write(b'read\n')
            print('Datos pedidos...')
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            print(line)

            if line:
                try:
                    # Fecha actual para el nombre del archivo (día y mes)
                    fecha = datetime.now().strftime("%d_%m")
                    nombre_archivo = f"medicion_{fecha}.csv"

                    # Ruta al escritorio
                    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
                    file_path = os.path.join(desktop_path, nombre_archivo)

                    # Crear el archivo con encabezado si no existe
                    archivo_nuevo = not os.path.exists(file_path)

                    with open(file_path, mode='a', newline='') as file:
                        writer = csv.writer(file)
                        if archivo_nuevo:
                            writer.writerow(["Timestamp", "Data"])
                        
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        writer.writerow([timestamp, line])
                    
                    print(f"Datos guardados en {file_path}")

                except Exception as e:
                    print(f"Error al guardar los datos: {e}")

            time.sleep(1)
    
    except serial.SerialException as e:
        print(f"Error: {e}")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == "__main__":
    read_serial_data(port='/dev/serial0')  # Cambia al puerto real si es necesario
# escribir dsmeg | grep tty para encontrar el puerto en linux