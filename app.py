from flask import Flask, request, render_template, jsonify
import json
from datetime import datetime
import os
import threading  # For non-blocking file writing (simple approach)

app = Flask(__name__)

# Directory to store received data files
DATA_DIRECTORY = 'received_data'
os.makedirs(DATA_DIRECTORY, exist_ok=True)  # Create the directory if it doesn't exist

@app.route('/')
def home():
    return render_template('index.html')

# Endpoint to display stored data
@app.route('/display_data')
def display_data():
    data_files = sorted([f for f in os.listdir(DATA_DIRECTORY) if f.endswith('.json')], reverse=True) # Sort by newest first
    all_data_with_time = []
    for filename in data_files:
        filepath = os.path.join(DATA_DIRECTORY, filename)
        try:
            file_write_timestamp = os.path.getmtime(filepath)
            file_write_time = datetime.fromtimestamp(file_write_timestamp).strftime("%Y-%m-%d %H:%M:%S")
            with open(filepath, 'r') as f:
                data = json.load(f)
                all_data_with_time.append({"data": data, "file_write_time": file_write_time})
        except Exception as e:
            print(f"Error reading file {filename}: {e}")
    return render_template('display_data.html', data_with_time=all_data_with_time)

def save_to_file(data):
    """Saves the received JSON data to a file with a timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"received_data_{timestamp}.json"
    filepath = os.path.join(DATA_DIRECTORY, filename)
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Data saved to: {filepath}")
    except Exception as e:
        print(f"Error saving data to file: {e}")

# Handle application/json (HTTP_JSON)
@app.route('/json_data', methods=['POST'])
def handle_json():
    start_time = datetime.now()
    data = request.get_json()  # Extract JSON data
    print("Received JSON data:", data)  # Log for debugging

    # Process the data (for now, just print and save)
    # In a real application, you might do more complex processing here

    # Save the data to a file in a separate thread to avoid blocking the response
    threading.Thread(target=save_to_file, args=(data,)).start()

    end_time = datetime.now()
    processing_time = (end_time - start_time).total_seconds()

    if processing_time <= 3:
        return jsonify({"message": "Success", "processing_time": processing_time}), 200
    else:
        return jsonify({"message": "Processed, but took longer than 3 seconds", "processing_time": processing_time}), 200 # Still return success

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # Runs the server on port 5000