# Proshop API

Proshop API is a RESTful API built with Django and Django REST Framework. It is the backend for the [Proshop](https://proshop-eshop.web.app/). Check out the [frontend repository](https://github.com/justicenyaga/proshop) for more details.

The project was inspired by [Dennis Ivanov](https://www.dennisivy.com/) and [Brad Traversy](https://www.traversymedia.com/). I followed their tutorial on udemy [Django with React | An Ecommerce Website](https://www.udemy.com/course/django-with-react-an-ecommerce-website/). I made some changes to the project to make it more interesting and to learn more about Django and React.

The API is hosted on Azure and can be accessed through this [link](https://proshop-eshop.azurewebsites.net/). The link will take you to the API home page which contains the various endpoints. A more detailed documentation will be provided soon.

## Features

The API has most of the features you would expect to find in an ecommerce web application. Some of the features include:

- User authentication
- Product reviews and ratings
- Product search feature
- Making and managing orders
- Admin product management
- Admin user management
- Admin order details page
- PayPal integration

## Technologies

### Backend

- [Django](https://www.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Django REST Framework Simple JWT](https://django-rest-framework-simplejwt.readthedocs.io/en/latest/)
- [Djoser](https://djoser.readthedocs.io/en/latest/)
- [social-auth-app-django](https://python-social-auth.readthedocs.io/en/latest/configuration/django.html)
- [PostgreSQL](https://www.postgresql.org/)

## Usage

### Prerequisites

- [Python 3.6 or higher](https://www.python.org/downloads/)
- [PostgreSQL](https://www.postgresql.org/) (optional) - You can use any other database of your choice

### Installation

I Will be providing a detailed documentation on this soon.

<!--

1. Clone the repository

   ```bash
   git clone https://github.com/justicenyaga/proshop.git && cd proshop
   ```

2. Create a virtual environment

   ```bash
   virtualenv -p python3 venv
   ```

3. Activate the virtual environment

   ```bash
   source venv/bin/activate
   ```

4. Install the dependencies

   ```bash
   pip install -r requirements.txt
   ```

5. Add the environment variables

   #### option 1: create a .env file in the root directory and add the following environment variables

   ```
   SECRET_KEY=your_secret_key
   ```

   #### option 2: export the environment variables in your terminal

   ```bash
   export SECRET_KEY=your_secret_key
   ```

6. Run the migrations

   ```bash
   python manage.py migrate
   ```

7. Load the initial data

   ```bash
   python manage.py loaddata data.json
   ```

8. Create a superuser

   ```bash
   python manage.py createsuperuser
   ```

9. Run the app

   ```bash
   python manage.py runserver
   ```

- Open [http://localhost:8000](http://localhost:8000) on your browser to view the app.

  ```
  use the superuser credentials to login to the admin panel
  ``` -->

## Migration Guard - 数据库迁移发布前检查工具

已集成 Migration Guard 工具，用于在部署前自动检查数据库迁移的完整性和安全性。

### 检查功能

- ✅ 同编号未合并分支检测（已合并仅 warning，未合并才阻断）
- ✅ 缺失依赖检测
- ✅ 迁移图完整性检查（多叶子节点、循环依赖）
- ✅ 未生成迁移检测
- ✅ 危险操作检测（DeleteModel、RemoveField 等）
- ✅ 迁移与数据库状态一致性检查

### 快速使用

```bash
# 运行迁移检查（发现错误时阻止部署）
python manage.py migration_guard

# 仅检查不中断（用于预览问题）
python manage.py migration_guard --check-only

# 将错误视为警告
python manage.py migration_guard --warn-only
```

### 自动部署

已接入 Procfile `release` 链路，部署时按以下顺序执行（层层递进，轻量在前）：

1. `bin/check_config.sh --strict` — **最小启动前检查**（秒级）
   - 仅检查 Django 启动必需的环境变量（SECRET_KEY、DJANGO_SETTINGS_MODULE）
   - --strict 模式下增加数据库连接变量检查
   - 失败快，避免无谓的 Django 进程启动

2. `python manage.py check_config` — **Django 深度配置检查**
   - 12 大类检查：系统检查、数据库连通性、JWT、OAuth、CORS、Email、DJOSER、
     Static/Media 可写性、生产安全配置、认证配置等
   - 区分 error（阻断）和 warning（提示）
   - 生产环境执行额外的安全配置检查

3. `python manage.py migration_guard` — **迁移完整性检查**
   - 同编号未合并分支、缺失依赖、迁移图完整性、未生成迁移、
     危险操作（DeleteModel/RemoveField）、迁移与数据库一致性

4. `python manage.py migrate` — **执行数据库迁移**

任何一步失败都会中止 release，部署回滚。

详细文档请参考 [MIGRATION_GUARD.md](file:///Users/pkcha/proshop_api/MIGRATION_GUARD.md)。
