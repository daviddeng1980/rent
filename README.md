# 租金管理系统

基于 Flask 的租金物业管理 REST API 系统。

## 功能模块

- **房产管理** - 房产基础信息管理（名称、地址、面积、类型、装修、家具、贷款等）
- **租约管理** - 租赁合同管理，自动生成付款计划
- **租客管理** - 租客信息管理
- **付款管理** - 付款记录跟踪
- **利润分析** - 年度收益分析

## 技术栈

- Flask
- Flask-SQLAlchemy
- SQLite
- Flask-CORS

## 安装

```bash
pip install -r requirements.txt
python init_db.py
python app.py
```

## API 端点

- `GET /properties` - 获取房产列表
- `POST /properties` - 添加房产
- `GET/PUT/DELETE /properties/<id>` - 房产 CRUD
- `GET /leases` - 获取租约列表
- `POST /leases` - 创建租约
- `GET/PUT/DELETE /leases/<id>` - 租约 CRUD
- `GET /tenants` - 获取租客列表
- `POST /tenants` - 添加租客
- `GET/PUT/DELETE /tenants/<id>` - 租客 CRUD
- `GET /payments` - 获取付款记录
- `PUT /payments/<id>` - 更新付款状态
- `GET /analysis/summary` - 总收益概览
- `GET /analysis/property/<id>` - 单个房产收益分析

## 运行

访问 http://localhost:5001 查看前端界面。
