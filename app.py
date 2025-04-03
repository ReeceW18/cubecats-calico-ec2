from flask import Flask, request, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/your-endpoint', methods=['POST'])
def handle_post():
    data = request.json  # or request.data for raw data
    # Process the received data here
    return 'Data received', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # Runs the server on port 5000