-- 添加分析相关表

-- 分析任务表
CREATE TABLE IF NOT EXISTS analysis_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    market_type VARCHAR(20) NOT NULL,
    analysis_depth INTEGER NOT NULL DEFAULT 3,
    analysts JSONB NOT NULL DEFAULT '[]'::jsonb,
    llm_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    error_message TEXT,
    token_usage JSONB DEFAULT '{"input_tokens": 0, "output_tokens": 0}'::jsonb,
    cost_usd DECIMAL(10, 4) DEFAULT 0.0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    CONSTRAINT check_status CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    CONSTRAINT check_market_type CHECK (market_type IN ('stock', 'crypto', 'commodity')),
    CONSTRAINT check_progress CHECK (progress >= 0 AND progress <= 100),
    CONSTRAINT check_depth CHECK (analysis_depth >= 1 AND analysis_depth <= 5)
);

-- 分析报告表
CREATE TABLE IF NOT EXISTS analysis_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES analysis_tasks(id) ON DELETE CASCADE,
    analyst_type VARCHAR(50) NOT NULL,
    content JSONB NOT NULL,
    summary TEXT NOT NULL,
    rating VARCHAR(20),
    confidence_score DECIMAL(3, 2),
    key_findings JSONB DEFAULT '[]'::jsonb,
    recommendations JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT check_rating CHECK (rating IN ('bullish', 'neutral', 'bearish')),
    CONSTRAINT check_confidence CHECK (confidence_score >= 0 AND confidence_score <= 1)
);

-- 分析日志表
CREATE TABLE IF NOT EXISTS analysis_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES analysis_tasks(id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    level VARCHAR(20) NOT NULL,
    agent_name VARCHAR(50),
    message TEXT NOT NULL,
    details JSONB,
    
    CONSTRAINT check_level CHECK (level IN ('info', 'warning', 'error', 'debug'))
);

-- 创建索引
CREATE INDEX idx_analysis_tasks_user_id ON analysis_tasks(user_id);
CREATE INDEX idx_analysis_tasks_symbol ON analysis_tasks(symbol);
CREATE INDEX idx_analysis_tasks_status ON analysis_tasks(status);
CREATE INDEX idx_analysis_tasks_created_at ON analysis_tasks(created_at DESC);

CREATE INDEX idx_analysis_reports_task_id ON analysis_reports(task_id);
CREATE INDEX idx_analysis_reports_analyst_type ON analysis_reports(analyst_type);
CREATE INDEX idx_analysis_reports_created_at ON analysis_reports(created_at DESC);

CREATE INDEX idx_analysis_logs_task_id ON analysis_logs(task_id);
CREATE INDEX idx_analysis_logs_timestamp ON analysis_logs(timestamp DESC);

-- 更新时间触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_analysis_tasks_updated_at 
    BEFORE UPDATE ON analysis_tasks 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();