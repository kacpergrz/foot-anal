#!/usr/bin/env python3
"""
Minimal working endpoint to test basic Vercel functionality
"""
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({'message': 'Minimal Flask app is working on Vercel!'})

@app.route('/api/test')
def test():
    return jsonify({
        'status': 'success',
        'message': 'Basic API endpoint is working',
        'data': {'test': True}
    })

# This is required for Vercel
if __name__ == '__main__':
    app.run(debug=True)