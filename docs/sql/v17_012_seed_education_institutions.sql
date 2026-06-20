-- ============================================================
-- DragonEyes v1.7 — Phase 7+8 보강 (012)
-- 교육부 + 시·도 교육청 17 + 시·도의회 교육위원회 17 시드
-- ============================================================
-- 적용일 : 2026-06-20
-- 목적   : 전국 교육 행정 기관·지방의회 교육위원회를 미리 INSERT 해서
--          가입 폼에서 바로 선택 가능하게.
-- 전제   : v17_011 적용 완료 (metro_council/local_council type 사용 가능)
-- ============================================================


-- ─────────────────────────────────────────────────────────────
-- 0. code 부분 UNIQUE 인덱스 (시드 중복 INSERT 방지)
-- ─────────────────────────────────────────────────────────────
CREATE UNIQUE INDEX IF NOT EXISTS institutions_code_unique
    ON public.institutions(code) WHERE code IS NOT NULL;


-- ─────────────────────────────────────────────────────────────
-- 1. 교육부 + 시·도 교육청 17곳
-- ─────────────────────────────────────────────────────────────
INSERT INTO public.institutions
    (type, name, code, region, status, verification_source, approved_at)
VALUES
-- 교육부
('ministry', '교육부', 'GOV-MOE', '세종특별자치시', 'approved', 'manual', NOW()),

-- 시·도 교육청 17곳 (지방자치단체 코드 기준)
('metro_office', '서울특별시교육청',       'METRO-OFFICE-11', '서울특별시',        'approved', 'manual', NOW()),
('metro_office', '부산광역시교육청',       'METRO-OFFICE-26', '부산광역시',        'approved', 'manual', NOW()),
('metro_office', '대구광역시교육청',       'METRO-OFFICE-27', '대구광역시',        'approved', 'manual', NOW()),
('metro_office', '인천광역시교육청',       'METRO-OFFICE-28', '인천광역시',        'approved', 'manual', NOW()),
('metro_office', '광주광역시교육청',       'METRO-OFFICE-29', '광주광역시',        'approved', 'manual', NOW()),
('metro_office', '대전광역시교육청',       'METRO-OFFICE-30', '대전광역시',        'approved', 'manual', NOW()),
('metro_office', '울산광역시교육청',       'METRO-OFFICE-31', '울산광역시',        'approved', 'manual', NOW()),
('metro_office', '세종특별자치시교육청',   'METRO-OFFICE-36', '세종특별자치시',    'approved', 'manual', NOW()),
('metro_office', '경기도교육청',           'METRO-OFFICE-41', '경기도',            'approved', 'manual', NOW()),
('metro_office', '강원특별자치도교육청',   'METRO-OFFICE-51', '강원특별자치도',    'approved', 'manual', NOW()),
('metro_office', '충청북도교육청',         'METRO-OFFICE-43', '충청북도',          'approved', 'manual', NOW()),
('metro_office', '충청남도교육청',         'METRO-OFFICE-44', '충청남도',          'approved', 'manual', NOW()),
('metro_office', '전북특별자치도교육청',   'METRO-OFFICE-52', '전북특별자치도',    'approved', 'manual', NOW()),
('metro_office', '전라남도교육청',         'METRO-OFFICE-46', '전라남도',          'approved', 'manual', NOW()),
('metro_office', '경상북도교육청',         'METRO-OFFICE-47', '경상북도',          'approved', 'manual', NOW()),
('metro_office', '경상남도교육청',         'METRO-OFFICE-48', '경상남도',          'approved', 'manual', NOW()),
('metro_office', '제주특별자치도교육청',   'METRO-OFFICE-50', '제주특별자치도',    'approved', 'manual', NOW())
ON CONFLICT (code) DO NOTHING;


-- ─────────────────────────────────────────────────────────────
-- 2. 시·도의회 교육위원회 17곳
-- ─────────────────────────────────────────────────────────────
INSERT INTO public.institutions
    (type, name, code, region, status, verification_source, approved_at)
VALUES
('metro_council', '서울특별시의회 교육위원회',       'METRO-COUNCIL-11', '서울특별시',        'approved', 'manual', NOW()),
('metro_council', '부산광역시의회 교육위원회',       'METRO-COUNCIL-26', '부산광역시',        'approved', 'manual', NOW()),
('metro_council', '대구광역시의회 교육위원회',       'METRO-COUNCIL-27', '대구광역시',        'approved', 'manual', NOW()),
('metro_council', '인천광역시의회 교육위원회',       'METRO-COUNCIL-28', '인천광역시',        'approved', 'manual', NOW()),
('metro_council', '광주광역시의회 교육위원회',       'METRO-COUNCIL-29', '광주광역시',        'approved', 'manual', NOW()),
('metro_council', '대전광역시의회 교육위원회',       'METRO-COUNCIL-30', '대전광역시',        'approved', 'manual', NOW()),
('metro_council', '울산광역시의회 교육위원회',       'METRO-COUNCIL-31', '울산광역시',        'approved', 'manual', NOW()),
('metro_council', '세종특별자치시의회 교육위원회',   'METRO-COUNCIL-36', '세종특별자치시',    'approved', 'manual', NOW()),
('metro_council', '경기도의회 교육위원회',           'METRO-COUNCIL-41', '경기도',            'approved', 'manual', NOW()),
('metro_council', '강원특별자치도의회 교육위원회',   'METRO-COUNCIL-51', '강원특별자치도',    'approved', 'manual', NOW()),
('metro_council', '충청북도의회 교육위원회',         'METRO-COUNCIL-43', '충청북도',          'approved', 'manual', NOW()),
('metro_council', '충청남도의회 교육위원회',         'METRO-COUNCIL-44', '충청남도',          'approved', 'manual', NOW()),
('metro_council', '전북특별자치도의회 교육위원회',   'METRO-COUNCIL-52', '전북특별자치도',    'approved', 'manual', NOW()),
('metro_council', '전라남도의회 교육위원회',         'METRO-COUNCIL-46', '전라남도',          'approved', 'manual', NOW()),
('metro_council', '경상북도의회 교육위원회',         'METRO-COUNCIL-47', '경상북도',          'approved', 'manual', NOW()),
('metro_council', '경상남도의회 교육위원회',         'METRO-COUNCIL-48', '경상남도',          'approved', 'manual', NOW()),
('metro_council', '제주특별자치도의회 교육위원회',   'METRO-COUNCIL-50', '제주특별자치도',    'approved', 'manual', NOW())
ON CONFLICT (code) DO NOTHING;


-- ─────────────────────────────────────────────────────────────
-- 검증
-- ─────────────────────────────────────────────────────────────
SELECT type, COUNT(*) AS cnt
FROM public.institutions
WHERE deleted_at IS NULL
GROUP BY type
ORDER BY type;
-- 기대:
--   ministry        1
--   metro_office   17
--   metro_council  17

SELECT 'TOTAL seeded' AS label,
       COUNT(*) FILTER (WHERE type='ministry')       AS ministry,
       COUNT(*) FILTER (WHERE type='metro_office')   AS metro_offices,
       COUNT(*) FILTER (WHERE type='metro_council')  AS metro_councils
FROM public.institutions
WHERE deleted_at IS NULL;
-- 기대: 1 / 17 / 17

-- 끝.
