-- =====================================================
-- AI 智能客服系统 v1.0 | 数据库初始化脚本
-- 数据库: ics_customer_service
-- =====================================================

CREATE DATABASE IF NOT EXISTS ics_customer_service
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE ics_customer_service;

-- =====================================================
-- 1. users — 用户表
-- =====================================================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '用户ID',
    phone VARCHAR(20) UNIQUE DEFAULT NULL COMMENT '手机号(与email至少一个非空)',
    email VARCHAR(255) UNIQUE DEFAULT NULL COMMENT '邮箱(与phone至少一个非空)',
    password_hash VARCHAR(255) NOT NULL COMMENT 'bcrypt哈希密码',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 2. sessions — 会话表
-- =====================================================
CREATE TABLE IF NOT EXISTS sessions (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '会话ID',
    user_id INT NOT NULL COMMENT '所属用户ID',
    title VARCHAR(100) DEFAULT '新会话' COMMENT '会话标题',
    status ENUM('active', 'closed') DEFAULT 'active' COMMENT '会话状态',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
    CONSTRAINT fk_sessions_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 3. messages — 消息表
-- =====================================================
CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '消息ID',
    session_id INT NOT NULL COMMENT '所属会话ID',
    role ENUM('user', 'assistant') NOT NULL COMMENT '发言角色',
    content TEXT NOT NULL COMMENT '消息正文',
    intent_tag VARCHAR(50) DEFAULT NULL COMMENT '意图标签(可选)',
    references_json JSON DEFAULT NULL COMMENT '引用来源JSON数组',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '发送时间',
    CONSTRAINT fk_messages_session
        FOREIGN KEY (session_id) REFERENCES sessions(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 4. feedback — 反馈表
-- =====================================================
CREATE TABLE IF NOT EXISTS feedback (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '反馈ID',
    message_id INT NOT NULL COMMENT '被评价的消息ID',
    rating ENUM('positive', 'negative') NOT NULL COMMENT '赞/踩',
    comment TEXT DEFAULT NULL COMMENT '反馈文字(可选)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '反馈时间',
    CONSTRAINT fk_feedback_message
        FOREIGN KEY (message_id) REFERENCES messages(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 5. knowledge_bases — 知识库表
-- =====================================================
CREATE TABLE IF NOT EXISTS knowledge_bases (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '知识库ID',
    user_id INT NOT NULL COMMENT '所属用户ID',
    name VARCHAR(100) NOT NULL COMMENT '知识库名称',
    description TEXT COMMENT '知识库描述',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    CONSTRAINT fk_kb_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 6. documents — 知识库文档表
-- =====================================================
CREATE TABLE IF NOT EXISTS documents (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '文档ID',
    user_id INT NOT NULL COMMENT '上传用户ID',
    kb_id INT DEFAULT NULL COMMENT '所属知识库ID',
    name VARCHAR(255) NOT NULL COMMENT '文档名称',
    file_type ENUM('txt', 'md', 'pdf') NOT NULL COMMENT '文件格式',
    status ENUM('processing', 'ready', 'failed') DEFAULT 'processing' COMMENT '处理状态',
    chunk_count INT DEFAULT 0 COMMENT '分块数量',
    file_size INT DEFAULT 0 COMMENT '文件大小(bytes)',
    milvus_ids JSON DEFAULT NULL COMMENT 'Milvus向量ID数组',
    error_msg TEXT DEFAULT NULL COMMENT '失败原因',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
    CONSTRAINT fk_documents_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_documents_kb
        FOREIGN KEY (kb_id) REFERENCES knowledge_bases(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 7. daily_question_count — 每日提问计数表
-- =====================================================
CREATE TABLE IF NOT EXISTS daily_question_count (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '记录ID',
    user_id INT NOT NULL COMMENT '用户ID',
    query_date DATE NOT NULL COMMENT '查询日期',
    count INT DEFAULT 0 COMMENT '当日次数',
    UNIQUE KEY uk_user_date (user_id, query_date),
    CONSTRAINT fk_dqc_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 索引 (唯一约束和主键已在建表时创建)
-- =====================================================
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_feedback_message_id ON feedback(message_id);
CREATE INDEX idx_sessions_updated_at ON sessions(updated_at DESC);
CREATE INDEX idx_messages_created_at ON messages(created_at ASC);
CREATE INDEX idx_kb_user_id ON knowledge_bases(user_id);
CREATE INDEX idx_documents_user_id ON documents(user_id);
CREATE INDEX idx_documents_kb_id ON documents(kb_id);
CREATE INDEX idx_documents_status ON documents(status);
