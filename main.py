import os
import base64
import asyncio
from opperai import AsyncOpper
from pydantic import BaseModel, Field
from opperai.types import ImageInput
from dotenv import load_dotenv
from flask import Flask, request, render_template, redirect, url_for, flash
import uuid
import os.path
from PIL import Image
from io import BytesIO
import re

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24).hex())
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESIZED_FOLDER'] = 'resized'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
# Server configuration
app.config['HOST'] = os.getenv('FLASK_HOST', '0.0.0.0')  # Listen on all interfaces
app.config['PORT'] = int(os.getenv('FLASK_PORT', 5000))
# Image cleanup
app.config['CLEANUP_RESIZED'] = os.getenv('CLEANUP_RESIZED', 'True').lower() == 'true'

# Create necessary folders if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESIZED_FOLDER'], exist_ok=True)

class HotdogImageInput(BaseModel):
    image_base64: str = Field(description="Base64 encoded image to analyze")
    question: str = Field(description="The question to answer about the image")

class HotdogAnalysisResult(BaseModel):
    thoughts: str = Field(description="The thoughts of the model while analyzing the image")
    contains_hotdog: bool = Field(description="Whether the image contains a hotdog or not")
    confidence_score: float = Field(description="A number between 0 and 1 indicating the confidence level of the hotdog detection")
    explanation: str = Field(description="A brief explanation of why the model thinks this is or is not a hotdog")

def resize_image(image_path, max_size=300):
    """Resize an image keeping the aspect ratio with a maximum dimension of max_size and save to disk."""
    # Create a unique filename for the resized image
    filename = f"resized_{os.path.basename(image_path)}"
    resized_path = os.path.join(app.config['RESIZED_FOLDER'], filename)
    
    with Image.open(image_path) as img:
        # Get the original size
        width, height = img.size
        
        # Calculate the ratio
        if width > height:
            # Width is the largest dimension
            ratio = max_size / width
            new_width = max_size
            new_height = int(height * ratio)
        else:
            # Height is the largest dimension
            ratio = max_size / height
            new_height = max_size
            new_width = int(width * ratio)
        
        # Resize the image
        resized_img = img.resize((new_width, new_height), Image.LANCZOS)
        
        # Save to disk
        resized_img.save(resized_path, format=img.format if img.format else 'JPEG')
        
        return resized_path

def save_base64_image(base64_data):
    """Save a base64 encoded image to a file and return the file path."""
    # Extract the base64 data (remove data URL prefix if present)
    if "," in base64_data:
        base64_data = base64_data.split(",", 1)[1]
    
    # Decode base64 string to bytes
    image_data = base64.b64decode(base64_data)
    
    # Create a unique filename
    filename = f"{uuid.uuid4()}.jpg"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    # Save to file
    with open(filepath, "wb") as f:
        f.write(image_data)
    
    return filepath

def delete_file_if_exists(file_path):
    """Delete a file if it exists."""
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            return True
        except Exception as e:
            print(f"Error deleting file {file_path}: {str(e)}")
            return False
    return True

async def check_hotdog(image_path):
    """Analyze the image and check if it contains a hotdog. Cleans up resized image afterwards."""
    # Check if API key is available
    if not os.getenv('OPPER_API_KEY'):
        raise ValueError("OPPER_API_KEY not found in environment variables or .env file")
    
    resized_path = None
    
    try:
        # Initialize OpperAI client
        opper = AsyncOpper()  # Automatically loads API key from OPPER_API_KEY env var
        
        # Resize the image and save to disk
        resized_path = resize_image(image_path)
        
        # Make the API call
        result, _ = await opper.call(
            name="analyze_hotdog_image",
            instructions="Analyze the given image and determine if it contains a hotdog. Be accurate in your assessment. Also provide a confidence score between 0 and 1, where 1 means you are 100% confident in your answer and 0 means you have no confidence.",
            output_type=HotdogAnalysisResult,
            input=ImageInput.from_path(resized_path),
        )
        
        return result
        
    finally:
        # Clean up only the resized image if configured to do so
        if app.config['CLEANUP_RESIZED'] and resized_path and os.path.exists(resized_path):
            delete_file_if_exists(resized_path)

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    image_path = None
    
    if request.method == 'POST':
        if 'image_data' in request.form and request.form['image_data']:
            # Process camera captured image
            try:
                # Save the base64 image data to a file
                filepath = save_base64_image(request.form['image_data'])
                
                # Process the image
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(check_hotdog(filepath))
                loop.close()
                
                # Store image path for display
                image_path = os.path.basename(filepath)
                    
            except Exception as e:
                flash(f"Error: {str(e)}")
        
        elif 'file' in request.files:
            # Fall back to traditional file upload if available
            file = request.files['file']
            
            if file.filename == '':
                flash('No selected file')
                return redirect(request.url)
                
            if file and allowed_file(file.filename):
                # Create a unique filename
                filename = str(uuid.uuid4()) + os.path.splitext(file.filename)[1]
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                # Save the file
                file.save(filepath)
                
                try:
                    # Process the image
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(check_hotdog(filepath))
                    loop.close()
                    
                    # Keep reference to the uploaded image for display
                    image_path = filename
                        
                except Exception as e:
                    flash(f"Error: {str(e)}")
            else:
                flash('Invalid file type. Please upload an image (PNG, JPG, JPEG, GIF)')
        else:
            flash('No image provided')
    
    return render_template('index.html', result=result, image_path=image_path)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    from flask import send_from_directory
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/resized/<filename>')
def resized_file(filename):
    from flask import send_from_directory
    return send_from_directory(app.config['RESIZED_FOLDER'], filename)

@app.route('/static/<filename>')
def static_file(filename):
    from flask import send_from_directory
    return send_from_directory('static', filename)

def main():
    # Check if running directly or via Flask
    if os.environ.get('FLASK_RUN_FROM_CLI') != 'true':
        app.run(
            host=app.config['HOST'], 
            port=app.config['PORT'],
            debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
        )

if __name__ == "__main__":
    main()
