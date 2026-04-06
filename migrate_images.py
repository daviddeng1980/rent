"""数据迁移脚本：为现有房产添加 images 字段默认值"""
from app import app
from extensions import db
from models import Property

with app.app_context():
    # 为现有房产设置空的 images 数组
    properties = Property.query.all()
    for p in properties:
        if p.images is None or p.images == '':
            p.images = '[]'
            print(f"更新房产 {p.id} ({p.name}) 的 images 字段为空数组")

    db.session.commit()
    print(f"迁移完成，共处理 {len(properties)} 个房产")
