-- When.Trade Database Schema Creation Script
-- 手动创建表结构

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    avatar VARCHAR(255),
    bio TEXT,
    role VARCHAR(50) DEFAULT 'user' NOT NULL CHECK (role IN ('user', 'admin', 'moderator')),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    is_superuser BOOLEAN DEFAULT FALSE,
    language VARCHAR(10) DEFAULT 'zh',
    timezone VARCHAR(50) DEFAULT 'Asia/Shanghai',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP
);

-- 订阅表
CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tier VARCHAR(50) DEFAULT 'free' NOT NULL CHECK (tier IN ('free', 'basic', 'professional', 'enterprise')),
    status VARCHAR(50) DEFAULT 'active' NOT NULL CHECK (status IN ('active', 'cancelled', 'expired', 'trial')),
    research_credits INTEGER DEFAULT 0,
    chat_credits INTEGER DEFAULT 0,
    monthly_research_limit INTEGER DEFAULT 10,
    monthly_chat_limit INTEGER DEFAULT 100,
    used_research_credits INTEGER DEFAULT 0,
    used_chat_credits INTEGER DEFAULT 0,
    price DECIMAL(10, 2) DEFAULT 0.00,
    currency VARCHAR(10) DEFAULT 'USD',
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP,
    trial_end_date TIMESTAMP,
    cancelled_at TIMESTAMP,
    stripe_subscription_id VARCHAR(255),
    stripe_customer_id VARCHAR(255),
    payment_method VARCHAR(50),
    can_use_research_mode BOOLEAN DEFAULT TRUE,
    can_use_chat_mode BOOLEAN DEFAULT TRUE,
    can_use_mcp_tools BOOLEAN DEFAULT FALSE,
    can_export_reports BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 任务表
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    task_id VARCHAR(255) UNIQUE NOT NULL,
    type VARCHAR(50) NOT NULL CHECK (type IN ('research', 'chat', 'analysis')),
    status VARCHAR(50) DEFAULT 'pending' NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    mode VARCHAR(50),
    query TEXT NOT NULL,
    parameters JSONB,
    target_symbol VARCHAR(50),
    research_domains JSONB,
    analysis_depth INTEGER DEFAULT 3,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    progress FLOAT DEFAULT 0.0,
    current_step VARCHAR(255),
    total_steps INTEGER DEFAULT 0,
    completed_steps INTEGER DEFAULT 0,
    estimated_cost FLOAT DEFAULT 0.0,
    actual_cost FLOAT DEFAULT 0.0,
    token_usage JSONB,
    result_summary TEXT,
    result_data JSONB,
    task_metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 报告表
CREATE TABLE IF NOT EXISTS reports (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    report_id VARCHAR(255) UNIQUE NOT NULL,
    type VARCHAR(50) NOT NULL CHECK (type IN ('research', 'chat', 'analysis')),
    title VARCHAR(255) NOT NULL,
    summary TEXT,
    content TEXT NOT NULL,
    sections JSONB,
    report_metadata JSONB,
    tags JSONB,
    findings JSONB,
    recommendations JSONB,
    risk_assessment JSONB,
    data_sources JSONB,
    charts JSONB,
    tables JSONB,
    export_formats JSONB DEFAULT '["markdown"]'::jsonb,
    export_urls JSONB,
    is_public BOOLEAN DEFAULT FALSE,
    is_archived BOOLEAN DEFAULT FALSE,
    is_deleted BOOLEAN DEFAULT FALSE,
    view_count INTEGER DEFAULT 0,
    share_count INTEGER DEFAULT 0,
    download_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_task_id ON tasks(task_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_reports_user_id ON reports(user_id);
CREATE INDEX idx_reports_task_id ON reports(task_id);
CREATE INDEX idx_reports_report_id ON reports(report_id);

-- 创建更新时间触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为所有表添加更新时间触发器
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_reports_updated_at BEFORE UPDATE ON reports
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();