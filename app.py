from flask import Flask, request, render_template, jsonify
import json
from datetime import datetime
from pytz import timezone
import os
import threading  # For non-blocking file writing (simple approach)
import struct

app = Flask(__name__)

# File names
messages_file = 'rockblock_messages.jsonl'
data_file = 'decoded_data.jsonl'

# Landing page, redirects to /display_data
@app.route('/')
def home():
    return display_data()

# Endpoint to display stored data
@app.route('/display_data')
def display_data():
    # create arrays to hold data
    decoded_data = []
    rockblock_data = []

    # load data
    with open(data_file, 'r') as f:
        for line in f:
            decoded_data.append(json.loads(line))
    with open(messages_file, 'r') as f:
        for line in f:
            rockblock_data.append(json.loads(line))

    return render_template('display_data.html', decoded_data=decoded_data, rockblock_data=rockblock_data)

# saves json to file as json lines
def save_to_file(message_data, json_file = messages_file):
    # Append to the file (using JSON Lines format - one JSON object per line)
    with open(json_file, 'a') as file:
        file.write(json.dumps(message_data) + "\n")

# Endpoint to receive RockBLOCK messages
@app.route('/rockblock-webhook', methods=['POST'])
def rockblock_webhook():
    # Get message data from request
    if request.is_json:
        message_data = request.json
    else:
        message_data = request.form.to_dict()

    # Add timestamp
    message_data['receive_time'] = datetime.now(timezone('America/New_York')).strftime("%y-%m-%d %H:%M:%S")
    
    # save to file and unpack data
    threading.Thread(target=save_to_file, args=(message_data,)).start()
    threading.Thread(target=unpack_data, args=(message_data,)).start()
    
    # Always respond quickly with 200 status
    return "OK", 200

def unpack_data(data_json):
    # check that data exists and is a string
    if 'data' not in data_json or not isinstance(data_json['data'], str):
        print("Missing or invalid 'data' field in JSON")
        return -1

    # pull out data and convert to bytes
    hex_data = data_json['data']
    try:
        byte_data = bytes.fromhex(hex_data)
    except ValueError:
        print("Invalid hex-encoded data")

    # create empty dictionary to hold decoded data and offset to track location in data
    decoded_data = {}
    offset = 0

    try:
        # Time (3 bytes)
        decoded_data['time'] = {
            'second': byte_data[offset],
            'minute': byte_data[offset + 1],
            'hour': byte_data[offset + 2]
        }
        offset += 3

        # GPS (14 bytes), <I is little-endian unsigned int (4 bytes), make sure to use the correct endianness
        decoded_data['gps'] = {
            'latitude': struct.unpack('<I', byte_data[offset:offset + 4])[0],  # uint32_t (4 bytes)
            'longitude': struct.unpack('<I', byte_data[offset + 4:offset + 8])[0], # uint32_t (4 bytes)
            'altitude': struct.unpack('<I', byte_data[offset + 8:offset + 12])[0],  # uint32_t (4 bytes)
            'satellites': byte_data[offset + 12],                                  # uint8_t (1 byte)
            'fixtype': byte_data[offset + 13]                                     # uint8_t (1 byte)
        }
        offset += 14

        # Sensors (38 bytes)
        decoded_data['sensors'] = {
            'NO2': struct.unpack('<I', byte_data[offset:offset + 4])[0],     # uint32_t (4 bytes)
            'C2H5OH': struct.unpack('<I', byte_data[offset + 4:offset + 8])[0],  # uint32_t (4 bytes)
            'VOC': struct.unpack('<I', byte_data[offset + 8:offset + 12])[0],   # uint32_t (4 bytes)
            'CO': struct.unpack('<I', byte_data[offset + 12:offset + 16])[0],    # uint32_t (4 bytes)
            'ozone': struct.unpack('<H', byte_data[offset + 16:offset + 18])[0],  # uint16_t (2 bytes)
            'pressure': struct.unpack('<f', byte_data[offset + 18:offset + 22])[0], # float (4 bytes)
            'uv': struct.unpack('<f', byte_data[offset + 22:offset + 26])[0],     # float (4 bytes)
            'lux': struct.unpack('<f', byte_data[offset + 26:offset + 30])[0],    # float (4 bytes)
            'temperature': struct.unpack('<f', byte_data[offset + 30:offset + 34])[0], # float (4 bytes)
            'humidity': struct.unpack('<f', byte_data[offset + 34:offset + 38])[0]  # float (4 bytes)
        }
        offset += 38

        # warn if there was more data than expected
        if offset != len(byte_data):
            print(f"Warning: Data length mismatch. Expected {3 + 14 + 38} bytes, got {len(byte_data)} bytes.")

        # Save decoded data to file
        save_to_file(decoded_data, data_file)
        return -1

    except struct.error as e:
        print(f"Error unpacking data: {e}")
        return -1
    except IndexError:
        print("Incomplete data received. Not enough bytes to unpack.")
        return -1

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # Runs the server on port 5000
