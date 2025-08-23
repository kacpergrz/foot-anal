#!/usr/bin/env python3
"""
Simple health check endpoint for Vercel debugging
"""
from flask import Flask, jsonify
import sys
import os

app = Flask(__name__)

@app.route('/api/health')
def health_check():
    """Simple health check to test if Vercel deployment works"""
    try:
        return jsonify({
            'status': 'ok',
            'python_version': sys.version,
            'working_directory': os.getcwd(),
            'environment': dict(os.environ),
            'message': 'Health check passed'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'type': type(e).__name__
        }), 500

if __name__ == '__main__':
    app.run(debug=True)