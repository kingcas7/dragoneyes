# 레거시 SQL 세트 — 2026-05-11 (v2.1 기획/마이그레이션)

> **아카이브 정리일**: 2026-05-18
> **원본 위치**: `~/Desktop/With Claude/DragonEyes System files/`
> **아카이브 사유**: repo `docs/sql/`(현행 마이그레이션)와 phase 번호가
> 겹치는데 내용이 달라 혼동 방지를 위해 별도 폴더로 분리·git 보존.

## ⚠️ 번호 충돌 주의

| phase | 이 폴더(레거시) | repo `docs/sql/`(현행) |
|-------|----------------|------------------------|
| phase1 | phase1_create_tables.sql | phase1_create_tables.sql (내용 다름) |
| phase5_1 | phase5_1_drop_legacy_tables.sql | phase5_1_drop_legacy_tables.sql |
| phase6 | phase6_tables.sql | phase6_catalog_system.sql (이름·내용 다름) |

→ **현행 마이그레이션의 기준은 항상 repo `docs/sql/` 본 디렉토리.**

## 적용 상태 (2026-05-18 기준)

| 파일 | 적용 여부 |
|------|-----------|
| phase7_seed.sql (기존 10명 user_groups 시딩) | ✅ **적용 확정** (작성자 확인) |
| phase8_rls.sql (RLS 정책 정식화) | ❓ DB 검증 필요 |
| phase9_license_orders.sql (license_orders 등) | ❓ DB 검증 필요 — app.py 미참조 |
| phase10_partner_contracts.sql (partner_*_contracts) | ❓ DB 검증 필요 |
| phase11_prospects.sql (customer_prospects 등) | ❓ DB 검증 필요 — 현재 `opportunities`로 대체된 것으로 추정 |
| phase1 / phase5_1 / phase6_tables | repo `docs/sql/`의 동명 파일이 현행. 이건 구버전 참고용 |

## 후속 작업 (백로그)

phase8~11의 실제 적용 여부를 운영 Supabase의 `information_schema`로 확인 후,
적용된 것은 repo `docs/sql/`에 정식 마이그레이션으로 승격(재번호) 권장.
