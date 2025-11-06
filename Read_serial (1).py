import serial
import csv
import time

from datetime import datetime

def read_serial_data(port='/dev/ttyUSB0', baudrate=9600, timeout=1):
    try:
        ser = serial.Serial(port, baudrate, timeout=timeout)
        print(f"Listening on {port} at {baudrate} baud...")

        while True:
            ser.write(b'read\n')
            print('Datos pedidos...')
            line = ser.readline().decode('utf-8').strip()
            print(line)
            if line:
                try:
                    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop", "datos_fachada_SERIAL.csv")
                    with open(desktop_path, 'a') as file:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        writer = csv.writer(file)
                        writer.writerow([timestamp, line])
                except Exception as e:
                    print(f"Error al guardar los datos: {e}")
                    
               
                
                """with open(filename, mode='w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(["Timestamp", "Data"])
                    writer.writerow([timestamp, line])
                
                print(f"Data saved to {filename}: {line}")"""
            time.sleep(1)
    
    except serial.SerialException as e:
        print(f"Error: {e}")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == "__main__":
    read_serial_data(port='/dev/serial0')  # Change to your actual port dmesg | grep serial
