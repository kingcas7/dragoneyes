-- ════════════════════════════════════════════════════════════════
-- Phase 5-3: license_request_users 테이블 신설
-- 작성: 2026-05-14
-- 목적: PO 양식 ④ '사용자 일괄 지정' 정보 저장
--       라이선스 신청 검토 후 승인 시 users 테이블로 일괄 생성
-- ════════════════════════════════════════════════════════════════

-- 1) 테이블 생성
CREATE TABLE IF NOT EXISTS license_request_users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id      UUID NOT NULL REFERENCES license_requests(id) ON DELETE CASCADE,
    
    -- 사용자 기본 정보
    user_role       TEXT NOT NULL CHECK (user_role IN ('admin', 'user')),
    user_order      INTEGER NOT NULL,  -- 1=관리자, 2~=사용자N
    name            TEXT NOT NULL,
    email           TEXT NOT NULL,
    phone           TEXT,
    
    -- 보호자 정보 (PO 양식 기준)
    guardian_name   TEXT,
    guardian_phone  TEXT,
    
    -- 소속 장애인 단체/기관
    disability_org  TEXT,
    
    -- 워크플로 추적 (승인 시 채워짐)
    created_user_id UUID REFERENCES users(id),
    status          TEXT DEFAULT 'pending' 
                    CHECK (status IN ('pending', 'created', 'failed', 'skipped')),
    error_message   TEXT,
    
    -- 메타
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    activated_at    TIMESTAMPTZ,
    
    -- 제약
    UNIQUE(request_id, email)
);

-- 2) 인덱스
CREATE INDEX IF NOT EXISTS idx_lru_request ON license_request_users(request_id);
CREATE INDEX IF NOT EXISTS idx_lru_email ON license_request_users(email);
CREATE INDEX IF NOT EXISTS idx_lru_status ON license_request_users(status);

-- 3) RLS (프로토타입: 본부 admin 전체 접근)
ALTER TABLE license_request_users ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "allow_all_for_prototype" ON license_request_users;
CREATE POLICY "allow_all_for_prototype" ON license_request_users
    FOR ALL USING (true) WITH CHECK (true);

-- 4) 코멘트
COMMENT ON TABLE license_request_users IS 
    'PO 양식 ④ 사용자 일괄 지정 정보. 신청 검토 후 승인 시 users 테이블로 생성됨.';
COMMENT ON COLUMN license_request_users.user_order IS '1=관리자(필수), 2~=사용자1, 2, 3...';
COMMENT ON COLUMN license_request_users.status IS 
    'pending=대기, created=계정 생성됨, failed=실패, skipped=건너뜀';

-- 5) 검증 쿼리
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns 
WHERE table_name = 'license_request_users'
ORDER BY ordinal_position;
