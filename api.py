from flask import Flask, request, jsonify
import json
import logging
from checker import check_account  # Import your existing check_account function

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def check_netflix_account():
    """
    Endpoint to check Netflix account credentials
    Usage: http://your-domain.com/?email=user@example.com&pass=password&proxy=proxy:port:user:pass
    """
    try:
        # Get parameters from URL query string
        email = request.args.get('email')
        password = request.args.get('pass')
        proxy = request.args.get('proxy')
        
        # Validate required parameters
        if not email or not password:
            return jsonify({
                "status": "ERROR",
                "message": "Missing required parameters. Please provide email and pass"
            }), 400
        
        logger.info(f"Processing request for email: {email}")
        
        # Call your existing check_account function
        result = check_account(email, password, proxy)
        
        # Return the result as JSON
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({
            "status": "ERROR",
            "message": f"Internal server error: {str(e)}"
        }), 500

@app.route('/health')
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    # Run the Flask app
    app.run(host='0.0.0.0', port=8080, debug=False)
