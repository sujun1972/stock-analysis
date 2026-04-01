-- 用户股票列表（自选股分组）
-- 允许已登录用户创建多个命名股票列表，并将股票加入/移出列表

CREATE TABLE IF NOT EXISTS user_stock_lists (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL,
    description VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, name)
);

CREATE TABLE IF NOT EXISTS user_stock_list_items (
    id SERIAL PRIMARY KEY,
    list_id INTEGER NOT NULL REFERENCES user_stock_lists(id) ON DELETE CASCADE,
    ts_code VARCHAR(20) NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (list_id, ts_code)
);

CREATE INDEX IF NOT EXISTS idx_user_stock_lists_user_id ON user_stock_lists(user_id);
CREATE INDEX IF NOT EXISTS idx_user_stock_list_items_list_id ON user_stock_list_items(list_id);

COMMENT ON TABLE user_stock_lists IS '用户自选股列表';
COMMENT ON TABLE user_stock_list_items IS '自选股列表成分股';
