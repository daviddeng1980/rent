from flask import Blueprint, request, jsonify
import os
import uuid
from PIL import Image

upload_bp = Blueprint('upload', __name__)

UPLOAD_FOLDER = 'uploads'
THUMBNAIL_FOLDER = 'uploads/thumbs'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
MIN_WIDTH = 300
MIN_HEIGHT = 300
COMPRESS_QUALITY = 85
THUMBNAIL_SIZE = (300, 300)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def ensure_dirs():
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(THUMBNAIL_FOLDER, exist_ok=True)

@upload_bp.route('/upload/image', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    property_id = request.form.get('property_id', 'temp')

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    ensure_dirs()

    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{property_id}_{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    thumb_filepath = os.path.join(THUMBNAIL_FOLDER, f"thumb_{filename}")

    try:
        img = Image.open(file)

        # 转换为 RGB 模式
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')

        # 检查最小尺寸
        if img.width < MIN_WIDTH or img.height < MIN_HEIGHT:
            return jsonify({'error': f'图片尺寸太小，最小需要 {MIN_WIDTH}x{MIN_HEIGHT} 像素'}), 400

        # 压缩过大图片
        if img.width > 1920 or img.height > 1920:
            ratio = min(1920 / img.width, 1920 / img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        # 保存压缩后的原图
        img.save(filepath, 'JPEG', quality=COMPRESS_QUALITY, optimize=True)

        # 生成缩略图
        img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
        img.save(thumb_filepath, 'JPEG', quality=80, optimize=True)

        return jsonify({
            'image': f'/uploads/{filename}',
            'thumbnail': f'/uploads/thumbs/thumb_{filename}'
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@upload_bp.route('/upload/delete', methods=['POST'])
def delete_image():
    data = request.get_json()
    image_path = data.get('image')

    if not image_path:
        return jsonify({'error': 'No image path'}), 400

    image_path = image_path.lstrip('/')
    thumb_path = image_path.replace('/uploads/', '/uploads/thumbs/thumb_')

    try:
        if os.path.exists(image_path):
            os.remove(image_path)
        if os.path.exists(thumb_path):
            os.remove(thumb_path)
        return jsonify({'message': 'Image deleted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
