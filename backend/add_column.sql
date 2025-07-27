-- 添加research_interests_text列到users表
ALTER TABLE users ADD COLUMN IF NOT EXISTS research_interests_text TEXT; 