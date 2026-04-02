-- 删除扩展数据分类及其下的两个定时任务
-- 涉及任务：涨跌停价格同步(id=12)、停复牌信息同步(id=15)

DELETE FROM scheduled_tasks WHERE id IN (12, 15);
