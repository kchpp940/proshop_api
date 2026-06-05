# Migration Guard - 数据库迁移发布前检查工具

## 概述

Migration Guard 是一个数据库迁移发布前的质量检查工具，用于确保 Django 迁移文件的完整性和安全性。它会在部署前自动扫描迁移图、检测未合并分支、缺失依赖、未生成迁移和危险删表操作，发现问题时直接失败并输出具体迁移文件和修复建议。

## 功能特性

### 1. 同编号未合并分支检查
检测同一 app 内同一编号的多条迁移是否仍为未合并的分支。

Django 允许同一 app 下存在同编号的分支迁移（branch），只要后续有 merge 迁移把它们合在一起就不算错误。只有当同编号迁移都是叶子节点（无下游合并迁移收拢）时才报错。

**已合并分支** → 仅 warning 提示，无需操作
**未合并分支** → error 阻断，需要创建 merge 迁移

**修复建议**：
```bash
python manage.py makemigrations --merge <app_label>
```

### 2. 缺失依赖检查
检测迁移文件中引用的依赖是否存在。

**修复建议**：
- 恢复被误删的迁移文件
- 或更新 dependencies 指向存在的迁移

### 3. 迁移图完整性检查
检测迁移图中的问题：
- 同一 app 内多个叶子节点（迁移分叉未合并）
- 循环依赖

**修复建议**：
```bash
python manage.py makemigrations --merge <app_label>
```

### 4. 未生成迁移检查
检测模型变更是否已生成迁移文件。

**修复建议**：
```bash
python manage.py makemigrations <app_label>
```

### 5. 危险操作检查
检测迁移中的危险操作：
- **DeleteModel**（错误级别）：删除整个模型和数据表
- **RemoveField**（错误级别）：删除字段和数据列
- **AlterUniqueTogether**（警告级别）：可能导致大表索引重建
- **AddField**（警告级别）：可能需要为现有行提供默认值

**修复建议**：
- DeleteModel/RemoveField：先创建数据迁移备份数据，或使用 `--fake` 跳过
- AddField：确保字段有默认值或设置为 nullable

### 6. 迁移与模型一致性检查
检测：
- 磁盘上有但未应用到数据库的迁移
- 数据库已应用但磁盘上缺失的迁移

## 使用方法

### 手动运行

```bash
# 完整检查（发现错误时退出码为1）
python manage.py migration_guard

# 仅检查不失败（用于预览问题）
python manage.py migration_guard --check-only

# 将错误视为警告（不中断流程）
python manage.py migration_guard --warn-only
```

### 自动部署

#### Procfile release 链路
已集成到 Procfile 的 `release` 命令中，部署时按以下顺序自动执行（层层递进，轻量在前）：

1. **`bin/check_config.sh --strict`** — 最小启动前检查（秒级完成）
   - 仅检查 Django 启动必需的环境变量（SECRET_KEY、DJANGO_SETTINGS_MODULE）
   - --strict 模式下增加数据库连接变量检查
   - 失败快，避免无谓的 Django 进程启动
   - **注意**：此脚本不做任何深度配置检查，深度检查由下一步完成

2. **`python manage.py check_config`** — Django 深度配置检查
   - 12 大类检查覆盖：系统检查、数据库连通性、关键设置、
     JWT 配置、OAuth/Social Auth、CORS、Email、DJOSER、
     Static 配置、Media 可写性、生产安全配置、认证配置
   - 区分 error（阻断部署）和 warning（仅提示）
   - 生产环境自动执行额外的安全配置检查（SSL、Cookie、XSS 等）

3. **`python manage.py migration_guard`** — 迁移完整性检查
   - 同编号未合并分支检测、缺失依赖、迁移图完整性、未生成迁移、
     危险操作检测（DeleteModel、RemoveField 等）、迁移与数据库一致性

4. **`python manage.py migrate`** — 执行数据库迁移

任何一步失败都会中止 release，部署回滚。

#### GitHub Actions CI/CD
已在 `.github/workflows/master_proshop-eshop.yml` 中集成，在构建阶段自动运行完整检查链路，发现问题会阻止部署。

## 常见问题修复指南

### 问题1：同编号未合并分支

```
❌ App 'base' has unmerged branch at number 0010: 0010_order_status_history.py, 0010_orderstatushistory_alter_cartitem...
```

**修复步骤**：
```bash
python manage.py makemigrations --merge base
```

### 问题2：同编号已合并分支（warning）

```
⚠️  App 'base' has same-number migrations at 0003: 0003_remove_product_image_url.py, 0003_subcategory_image.py (already merged downstream)
```

**无需操作**。分支已被下游迁移合并，如需简化历史可考虑 squash。

### 问题3：缺失的依赖迁移

```
❌ Migration base.0008_alter_cartitem... depends on non-existent migration: ('base', '0007_coupon_order_discount')
```

**修复步骤**：
1. 检查 Git 历史，确认 `0007_coupon_order_discount.py` 是否被误删
2. 如果是误删，从版本控制恢复
3. 如果该迁移确实不存在，修改 `0008` 的 dependencies 指向存在的迁移（如 `0006`）

### 问题4：多个叶子节点

```
❌ App 'base' has 2 leaf migrations: 0010_order_status_history, 0010_orderstatushistory_alter_cartitem...
```

**修复步骤**：
```bash
python manage.py makemigrations --merge base
```

### 问题5：危险的 DeleteModel 操作

```
❌ Migration base/0008_alter_cartitem... contains dangerous operation: DeleteModel
```

**修复步骤**：
1. 确认该表确实需要删除
2. 如果有重要数据，先创建数据迁移备份
3. 如果表已手动删除，使用 fake 迁移：
   ```bash
   python manage.py migrate --fake base 0008
   ```

## 迁移最佳实践

1. **每次提交前检查**：运行 `python manage.py migration_guard` 确保迁移健康
2. **避免手动修改迁移**：除非必要，不要手动编辑迁移文件
3. **并行开发协调**：多人开发时，合并分支后及时 `makemigrations --merge`
4. **生产环境验证**：在预发布环境先运行迁移检查和迁移
5. **备份重要数据**：执行 DeleteModel/RemoveField 前务必备份数据

## 输出说明

- **❌ ERRORS**：必须修复的严重问题，会阻止部署
- **⚠️ WARNINGS**：需要关注的潜在问题，不会阻止部署但建议处理
- **✅ All checks passed**：所有检查通过，可以安全部署

## 代码位置

- 核心逻辑：[base/management/commands/migration_guard.py](file:///Users/pkcha/proshop_api/base/management/commands/migration_guard.py)
- 发布链路：[Procfile](file:///Users/pkcha/proshop_api/Procfile)
- CI/CD 配置：[.github/workflows/master_proshop-eshop.yml](file:///Users/pkcha/proshop_api/.github/workflows/master_proshop-eshop.yml)
