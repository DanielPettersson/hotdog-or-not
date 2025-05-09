# Hotdog Detector

A web application that uses OpperAI to determine if an image contains a hotdog.

## Features

- Upload images via browser or drag-and-drop
- Image analysis using OpperAI
- Confidence score with visual indicator
- Explanation of the AI's reasoning
- Automatic image resizing to optimize API calls
- Automatic cleanup of resized images after processing
- Custom hotdog favicon
- Animated flying hotdogs that bounce realistically off screen edges
- CRT screen effect with custom GLSL shader for video preview

## Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the project root with your OpperAI API key:
   ```
   OPPER_API_KEY=your_api_key_here
   ```

## Running the Server

### Basic Usage

```bash
python main.py
```

This will start the server on all network interfaces (0.0.0.0) on port 5000.

### Configuration Options

You can configure the server by setting environment variables either in your `.env` file or before running the server:

```bash
# In .env file
FLASK_HOST=0.0.0.0     # Listen on all interfaces (default)
FLASK_PORT=5000        # Port to listen on (default)
FLASK_DEBUG=false      # Enable/disable debug mode
FLASK_SECRET_KEY=your_secret_key   # For session encryption (auto-generated if not set)
CLEANUP_RESIZED=true   # Delete resized images after processing (default: true)
```

### Image Cleanup

By default, the application will delete the resized images after processing to save disk space, while preserving the original uploaded images. This behavior can be disabled by setting:

```
CLEANUP_RESIZED=false
```

in your `.env` file if you need to keep the resized images for debugging or other purposes.

### Accessing the Server Remotely

Once the server is running, it can be accessed:

1. From the same machine at: `http://localhost:5000`
2. From other devices on your network at: `http://your_ip_address:5000`

Where `your_ip_address` is the IP address of the machine running the server.

### Security Notice

This application is configured to be accessible from any network interface. For production use, consider:

- Adding user authentication
- Setting up HTTPS
- Implementing rate limiting
- Running behind a reverse proxy like Nginx
- Restricting access to trusted IP addresses only

## Usage

1. Open the application in a web browser
2. Upload an image by dragging and dropping or using the file browser
3. Click "Analyze Image"
4. View the result, confidence score, and explanation
