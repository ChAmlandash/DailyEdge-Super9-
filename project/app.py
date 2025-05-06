from flask import Flask, request, send_file, render_template, redirect, url_for
import qrcode
import pyshorteners
import os
import cv2
import pikepdf
from PyPDF2 import PdfMerger
from werkzeug.utils import secure_filename
from pdf2docx import Converter
import platform
from threading import Timer
from datetime import datetime
from mailjet_rest import Client
import openai  # Added for LinkedIn post generation

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
STATIC_FOLDER = 'static'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)

# Mailjet settings
MAILJET_API_KEY = 'd8f44281e214d9f4dbfb714e1a0465de'
MAILJET_SECRET_KEY = '1654a82d957fab89c7552c4508285e34'
SENDER_EMAIL = 'mypersonalprojectswork@gmail.com'

# OpenAI API key (replace with your actual key)
openai.api_key = 'YOUR_OPENAI_API_KEY'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    data = request.form['qr_data']
    img = qrcode.make(data)
    qr_path = os.path.join(STATIC_FOLDER, 'qr_code.png')
    img.save(qr_path)
    return send_file(qr_path, as_attachment=True)

@app.route('/shorten_url', methods=['POST'])
def shorten_url():
    url = request.form['long_url']
    short_url = pyshorteners.Shortener().tinyurl.short(url)
    return f"<h2>Shortened URL:</h2><p><a href='{short_url}'>{short_url}</a></p><br><a href='/'>Back</a>"

@app.route('/merge_pdfs', methods=['POST'])
def merge_pdfs():
    files = request.files.getlist('pdfs')
    merger = PdfMerger()
    for f in files:
        path = os.path.join(UPLOAD_FOLDER, secure_filename(f.filename))
        f.save(path)
        merger.append(path)
    output_path = os.path.join(STATIC_FOLDER, 'merged.pdf')
    merger.write(output_path)
    merger.close()
    return send_file(output_path, as_attachment=True)

@app.route('/image_to_pdf', methods=['POST'])
def image_to_pdf():
    from PIL import Image  # Import locally to ensure Pillow is used here

    img_file = request.files['image']
    filename = secure_filename(img_file.filename)
    input_path = os.path.join(UPLOAD_FOLDER, filename)
    output_path = os.path.join(STATIC_FOLDER, 'converted.pdf')

    # Save uploaded image
    img_file.save(input_path)

    # Convert image to RGB and save as PDF
    with Image.open(input_path) as img:
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.save(output_path, "PDF", resolution=100.0)

    return send_file(output_path, as_attachment=True)

@app.route('/compress_pdf', methods=['POST'])
def compress_pdf():
    uploaded = request.files['pdf']
    in_path = os.path.join(UPLOAD_FOLDER, secure_filename(uploaded.filename))
    out_path = os.path.join(STATIC_FOLDER, 'compressed.pdf')
    uploaded.save(in_path)
    with pikepdf.open(in_path) as pdf:
        pdf.save(out_path, optimize_version=True, compression=pikepdf.CompressionLevel.compression_level_fast)
    return send_file(out_path, as_attachment=True)

@app.route('/pdf_to_word', methods=['POST'])
def pdf_to_word():
    file = request.files['pdf_file']
    input_path = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
    output_path = os.path.join(STATIC_FOLDER, 'converted.docx')
    file.save(input_path)
    cv = Converter(input_path)
    cv.convert(output_path)
    cv.close()
    return send_file(output_path, as_attachment=True)

@app.route('/word_to_pdf', methods=['POST'])
def word_to_pdf():
    if platform.system() == 'Windows':
        try:
            from docx2pdf import convert
        except ImportError:
            return "docx2pdf not installed."
        file = request.files['docx_file']
        input_path = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
        output_path = os.path.join(STATIC_FOLDER, 'converted.pdf')
        file.save(input_path)
        convert(input_path, output_path)
        return send_file(output_path, as_attachment=True)
    else:
        return "Word to PDF is only supported on Windows using docx2pdf."

def send_reminder_email(to_email, task_name):
    mailjet = Client(auth=(MAILJET_API_KEY, MAILJET_SECRET_KEY), version='v3.1')
    data = {
        'Messages': [
            {
                "From": {
                    "Email": SENDER_EMAIL,
                    "Name": "Super7 App"
                },
                "To": [
                    {
                        "Email": to_email,
                        "Name": "User"
                    }
                ],
                "Subject": f"Reminder: {task_name}",
                "TextPart": f"This is a reminder for your task: {task_name}",
                "HTMLPart": f"<h3>Reminder:</h3><p>{task_name}</p>"
            }
        ]
    }
    result = mailjet.send.create(data=data)
    print(result.status_code)
    print(result.json())

@app.route('/set_reminder', methods=['POST'])
def set_reminder():
    email = request.form['email']
    task = request.form['task']
    time_str = request.form['reminder_time']  # format: 'YYYY-MM-DDTHH:MM'
    reminder_time = datetime.strptime(time_str, "%Y-%m-%dT%H:%M")
    delay = (reminder_time - datetime.now()).total_seconds()

    if delay <= 0:
        return "Invalid time. Please set a future time."

    Timer(delay, send_reminder_email, args=(email, task)).start()
    return f"<h2>Reminder set for task '{task}' at {reminder_time}</h2><br><a href='/'>Back</a>"
import groq  # Groq's Python SDK

# Set your Groq API key (you fill this part in)
groq.api_key = ''


@app.route('/generate_linkedin_post', methods=['POST'])
def generate_linkedin_post():
    topic = request.form['post_topic']
    tone = request.form['tone']            # e.g., professional, casual, inspirational
    length = request.form['length']        # e.g., short, medium, long
    use_emojis = 'use_emojis' in request.form  # checkbox
     
    # Length mapping
    length_map = {
        "short": "about 50 words",
        "medium": "around 100 words",
        "long": "up to 150 words"
    }

    # Emoji instruction
    emoji_instruction = (
        "Use relevant emojis and symbols to enhance the post." 
        if use_emojis else "Avoid using any emojis or symbols."
    )

    # Construct prompt
    prompt = (
        f"Write a LinkedIn post about '{topic}' in a {tone} tone. "
        f"Make the post {length_map.get(length, 'around 100 words')}. "
        f"{emoji_instruction} "
        f"The post should be informative, engaging, and encourage interaction. "
        f"Also, add 3 to 5 relevant and trending hashtags related to the topic at the end."
    )

    try:
        client = groq.Groq(api_key=groq.api_key)
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )

        linkedin_post = response.choices[0].message.content
        formatted_post = linkedin_post.replace('\n', '<br>')
        return f"<h2>Your LinkedIn Post:</h2><p>{formatted_post}</p><br><a href='/'>Back</a>"
    except Exception as e:
        return f"<h3>Error generating post:</h3><p>{e}</p><br><a href='/'>Back</a>"



if __name__ == '__main__':
    app.run(debug=True)
