#!/usr/bin/env python3
"""
Debug endpoint to test imports and dependencies
"""
from flask import Flask, jsonify
import sys
import os

app = Flask(__name__)

@app.route('/api/debug')
def debug_imports():
    """Test all imports and show what's available"""
    results = {
        'python_version': sys.version,
        'python_path': sys.path,
        'working_directory': os.getcwd(),
        'files_in_directory': os.listdir('.'),
        'imports': {}
    }
    
    # Test basic imports
    imports_to_test = [
        'flask',
        'requests', 
        'json',
        'datetime',
        'os',
        'dotenv',
        'flask_cors',
        'google.generativeai',
        'google.api_core',
        'beautifulsoup4'
    ]
    
    for module_name in imports_to_test:
        try:
            __import__(module_name)
            results['imports'][module_name] = 'SUCCESS'
        except ImportError as e:
            results['imports'][module_name] = f'FAILED: {str(e)}'
        except Exception as e:
            results['imports'][module_name] = f'ERROR: {str(e)}'
    
    # Check environment variables
    env_vars = ['FOOTBALL_DATA_API_KEY', 'PYTHONPATH']
    results['environment_variables'] = {}
    for var in env_vars:
        value = os.environ.get(var)
        results['environment_variables'][var] = 'SET' if value else 'NOT_SET'
    
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)