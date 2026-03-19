-- 为 scheduled_tasks 表添加元数据字段，支持任务排序、分组和友好名称显示
-- 用途：优化定时任务配置页面的展示效果，统一管理任务元数据

-- 添加元数据字段
ALTER TABLE scheduled_tasks
  ADD COLUMN IF NOT EXISTS display_name VARCHAR(100),           -- 友好显示名称
  ADD COLUMN IF NOT EXISTS category VARCHAR(50),                -- 任务分类（基础数据、行情数据等）
  ADD COLUMN IF NOT EXISTS display_order INTEGER DEFAULT 9999;  -- 显示排序（数字越小越靠前）

-- 创建索引优化查询性能
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_category_order
  ON scheduled_tasks (category, display_order, id);

-- 添加字段注释
COMMENT ON COLUMN scheduled_tasks.display_name IS '任务友好显示名称（用于前端展示）';
COMMENT ON COLUMN scheduled_tasks.category IS '任务分类（基础数据、行情数据、扩展数据、市场情绪、盘前分析、质量监控、报告通知、系统维护等）';
COMMENT ON COLUMN scheduled_tasks.display_order IS '任务显示顺序（数字越小越靠前，同分类内按此字段排序）';
