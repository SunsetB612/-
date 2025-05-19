from flask import Flask, render_template, request, send_file
from PIL import Image, ImageDraw, ImageFont
import os
import cv2
import numpy as np
from rembg import remove
import io
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/background', methods=['GET', 'POST'])
def background():
    original_img = None
    removed_bg_img = None
    final_img = None

    file = request.files.get('file')
    bg_color = request.form.get('bg_color', '#ffffff')

    if file and allowed_file(file.filename):
        # 1. 保存原图
        filename = secure_filename(file.filename)
        original_path = os.path.join(app.config['UPLOAD_FOLDER'], f'original_{filename}')
        file.save(original_path)

        # 2. 去除背景
        with open(original_path, 'rb') as f:
            input_data = f.read()
        output_data = remove(input_data)  # rembg 去背景
        removed_img = Image.open(io.BytesIO(output_data)).convert('RGBA')
        removed_path = os.path.join(app.config['UPLOAD_FOLDER'], f'removed_{filename}')
        if removed_img.mode == 'RGBA':
            # 将透明通道背景填充为白色并转换为RGB模式
            background = Image.new("RGB", removed_img.size, (255, 255, 255))
            background.paste(removed_img, mask=removed_img.split()[3])  # 使用 alpha 通道作为掩膜
            background.save(removed_path, 'JPEG')

        # 3. 替换为新背景色
        bg = Image.new('RGBA', removed_img.size, bg_color)
        bg.paste(removed_img, mask=removed_img.split()[3])
        final_path = os.path.join(app.config['UPLOAD_FOLDER'], f'final_{filename}')
        bg.convert('RGB').save(final_path)

        # 4. 前端展示所需的图片路径（相对路径即可）
        original_img = '/' + original_path  # /static/uploads/original_XXX.png
        removed_bg_img = '/' + removed_path
        final_img = '/' + final_path

    return render_template(
        'background.html',
        original_img=original_img,
        removed_bg_img=removed_bg_img,
        final_img=final_img
    )

@app.route('/crop', methods=['GET', 'POST'])
def crop():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = "crop_" + file.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            output = crop_image(filepath)
            return send_file(output, mimetype='image/png', as_attachment=True, download_name='cropped.png')
    return render_template('crop.html')

@app.route('/watermark', methods=['GET', 'POST'])
def watermark():
    if request.method == 'POST':
        file = request.files['file']
        watermark_text = request.form.get('watermark', '')
        if file and allowed_file(file.filename):
            filename = "watermark_" + file.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            output = add_watermark(filepath, watermark_text)
            return send_file(output, mimetype='image/png', as_attachment=True, download_name='watermarked.png')
    return render_template('watermark.html')

def change_background(filepath, bg_color):
    with open(filepath, 'rb') as f:
        img = remove(f.read())
    img = Image.open(io.BytesIO(img)).convert("RGBA")
    bg = Image.new('RGBA', img.size, bg_color)
    bg.paste(img, mask=img.split()[3])
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'background_changed.png')
    bg.convert('RGB').save(output_path)
    return output_path

def crop_image(filepath):
    img = Image.open(filepath)
    width, height = img.size
    left = width * 0.1
    top = height * 0.1
    right = width * 0.9
    bottom = height * 0.9
    cropped_img = img.crop((left, top, right, bottom))
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'cropped.png')
    cropped_img.save(output_path)
    return output_path

def add_watermark(filepath, watermark):
    img = Image.open(filepath).convert("RGBA")
    txt = Image.new('RGBA', img.size, (255,255,255,0))
    draw = ImageDraw.Draw(txt)
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        font = ImageFont.load_default()
    text_bbox = draw.textbbox((0, 0), watermark, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    x = img.width - text_width - 10
    y = img.height - text_height - 10
    draw.text((x, y), watermark, fill=(255, 255, 255, 128), font=font)
    combined = Image.alpha_composite(img, txt)
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'watermarked.png')
    combined.convert('RGB').save(output_path)
    return output_path

if __name__ == '__main__':
    app.run(debug=True,port=5001)
