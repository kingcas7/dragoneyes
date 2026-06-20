-- ============================================================
-- DragonEyes v1.7 — 캠페인 시스템 Phase 7+8 Step B (010)
-- 캠페인 + 설문 3종 (초/중/고) + 78문항 + 안내 컨텐츠 INSERT
-- ============================================================
-- 적용일 : 2026-06-20
-- 전제   : v17_001 ~ v17_009 모두 적용 완료.
-- ============================================================


-- ─────────────────────────────────────────────────────────────
-- 1. 캠페인 INSERT (2026)
-- ─────────────────────────────────────────────────────────────
INSERT INTO public.campaigns (year, code, title, description, status, start_at)
VALUES (
    2026,
    'CAMP-2026',
    '2026 온라인 유해콘텐츠 근절 캠페인',
    '드래곤아이즈 학사모 캠페인 · 청소년의 온라인 안전과 저작권 인식 향상',
    'active',
    NOW()
)
ON CONFLICT (code) DO UPDATE SET status='active';


-- ─────────────────────────────────────────────────────────────
-- 2. surveys 3건 (초/중/고)
-- ─────────────────────────────────────────────────────────────
WITH cmp AS (SELECT id FROM public.campaigns WHERE year = 2026 LIMIT 1)
INSERT INTO public.surveys
    (campaign_id, scope, title, description, target_band, target_minutes, total_questions, pass_integrity_score, min_completion_seconds, status, published_at)
SELECT cmp.id, 'national',
       '온라인 유해콘텐츠 근절 캠페인 설문 (초등학생용)',
       '약 10분 · 익명 · 총 26문항. 정답 없음, 솔직한 응답이 도움이 됩니다.',
       'elementary', 240, 26, 80, 600, 'active', NOW()
FROM cmp
UNION ALL
SELECT cmp.id, 'national',
       '온라인 유해콘텐츠 근절 캠페인 설문 (중학생용)',
       '약 10분 · 익명 · 총 26문항. 민감한 문항은 응답하고 싶지 않음 선택 가능.',
       'middle', 300, 26, 80, 600, 'active', NOW()
FROM cmp
UNION ALL
SELECT cmp.id, 'national',
       '온라인 유해콘텐츠 근절 캠페인 설문 (고등학생용)',
       '약 10~15분 · 익명 · 총 26문항. 정책 인식 포함, 솔직한 응답이 정책 개선의 근거가 됩니다.',
       'high', 360, 26, 80, 900, 'active', NOW()
FROM cmp
ON CONFLICT DO NOTHING;


-- ─────────────────────────────────────────────────────────────
-- 3. survey_questions — 초등학생용 (26문항)
-- ─────────────────────────────────────────────────────────────
WITH s AS (SELECT id FROM public.surveys WHERE target_band='elementary' AND scope='national' LIMIT 1)
INSERT INTO public.survey_questions (survey_id, qno, qtype, text, options, topic_tag, sort_order, required) VALUES
((SELECT id FROM s), 1, 'single_choice',
 '나는 온라인 콘텐츠(영상·게임·SNS 등)를 얼마나 자주 보나요?',
 '["거의 매일","일주일에 몇 번","가끔","거의 안 봐요"]'::jsonb, '온라인이용', 1, true),
((SELECT id FROM s), 2, 'multi_choice',
 '내가 주로 보는 것은 무엇인가요? (여러 개 선택 가능)',
 '["영상(유튜브 등)","게임","SNS(인스타·틱톡 등)","웹툰·웹소설","음악","기타"]'::jsonb, '온라인이용', 2, true),
((SELECT id FROM s), 3, 'single_choice',
 '나는 온라인에서 무엇이 나에게 좋은 것이고 나쁜(해로운) 것인지 스스로 구별할 수 있어요.',
 '["그렇다","보통이다","아니다"]'::jsonb, '인식', 3, true),
((SELECT id FROM s), 4, 'single_choice',
 '온라인 나쁜(유해) 콘텐츠 문제가 심각하다고 생각해요.',
 '["그렇다","보통이다","아니다"]'::jsonb, '인식', 4, true),
((SELECT id FROM s), 5, 'single_choice',
 '어린이·청소년도 온라인에서 나쁜 콘텐츠에 쉽게 노출될 수 있다고 생각해요.',
 '["그렇다","보통이다","아니다"]'::jsonb, '인식', 5, true),
((SELECT id FROM s), 6, 'single_choice',
 '온라인에서 본 것이 내 생각이나 말, 행동에 영향을 준다고 생각해요.',
 '["그렇다","보통이다","아니다"]'::jsonb, '인식', 6, true),
((SELECT id FROM s), 7, 'single_choice',
 '나는 지금까지 온라인에서 무섭거나 나쁜 콘텐츠(폭력·야한 것·도박·심한 욕설 등)를 본 적이 있어요.',
 '["예","아니오","말하고 싶지 않아요"]'::jsonb, '경험', 7, true),
((SELECT id FROM s), 8, 'multi_choice',
 '(있다면) 어떤 것을 보았나요? (여러 개 선택 가능)',
 '["폭력적인 것","야한 것(음란물)","도박·돈내기","심한 욕설·혐오","낯선 사람의 이상한 말","기타","해당 없음"]'::jsonb, '경험', 8, false),
((SELECT id FROM s), 9, 'single_choice',
 '내 친구나 아는 사람이 온라인 나쁜 콘텐츠 때문에 피해를 본 적이 있어요.',
 '["예","아니오","잘 모르겠어요"]'::jsonb, '경험', 9, true),
((SELECT id FROM s), 10, 'single_choice',
 '온라인에서 모르는 사람이 나에게 친구하자고 하거나 사진·전화번호 같은 개인정보를 보내달라고 한 적이 있어요.',
 '["예","아니오","말하고 싶지 않아요"]'::jsonb, '그루밍', 10, true),
((SELECT id FROM s), 11, 'single_choice',
 '온라인에서 보고 배운 거친 말이나 행동을 따라 하는 친구를 본 적이 있어요.',
 '["예","아니오","잘 모르겠어요"]'::jsonb, '경험', 11, true),
((SELECT id FROM s), 12, 'single_choice',
 '온라인에서 나쁜 콘텐츠를 봤을 때 부모님이나 선생님께 말한 적이 있어요.',
 '["예","아니오","본 적이 없어요"]'::jsonb, '대응', 12, true),
((SELECT id FROM s), 13, 'single_choice',
 '학교에서 ‘온라인 나쁜 콘텐츠를 보면 어떻게 해야 하는지’ 배운 적이 있어요.',
 '["예","아니오","기억이 안 나요"]'::jsonb, '대응', 13, true),
((SELECT id FROM s), 14, 'multi_choice',
 '나쁜 콘텐츠를 보면 어디에 알리거나 신고하는지 알아요? (여러 개 선택 가능)',
 '["부모님·선생님","112(경찰)","학교(117)","앱·사이트의 신고 버튼","잘 몰라요"]'::jsonb, '대응', 14, true),
((SELECT id FROM s), 15, 'single_choice',
 '온라인 안전에 대해 학교에서 자주 배우면 도움이 될 것 같아요.',
 '["그렇다","보통이다","아니다"]'::jsonb, '대응', 15, true),
((SELECT id FROM s), 16, 'single_choice',
 '영화·음악·게임·웹툰·책을 만든 사람에게는 ‘저작권’이라는 권리가 있다는 것을 알아요?',
 '["잘 알아요","조금 알아요","잘 몰라요"]'::jsonb, '저작권', 16, true),
((SELECT id FROM s), 17, 'single_choice',
 '인터넷에서 다른 사람이 만든 그림·영상·음악·게임·프로그램을 허락 없이 베끼거나 퍼뜨리면 안 된다는 것을 알아요?',
 '["잘 알아요","조금 알아요","잘 몰라요"]'::jsonb, '저작권', 17, true),
((SELECT id FROM s), 18, 'single_choice',
 '그렇게 허락 없이 베끼거나 퍼뜨리는 것은 법을 어기는 일이라서 처벌을 받을 수 있다는 것을 알아요?',
 '["잘 알아요","조금 알아요","잘 몰라요"]'::jsonb, '저작권', 18, true),
((SELECT id FROM s), 19, 'single_choice',
 '그런 일로 처벌을 받으면 나중에 기록이 남아 불이익이 될 수 있다는 것을 알아요?',
 '["잘 알아요","조금 알아요","잘 몰라요"]'::jsonb, '저작권', 19, true),
((SELECT id FROM s), 20, 'single_choice',
 '학교에서 저작권에 대해 배운 적이 있어요?',
 '["예","아니오","기억이 안 나요"]'::jsonb, '저작권', 20, true),
((SELECT id FROM s), 21, 'single_choice',
 '저작권에 대해 학교에서 자주 배우면 도움이 될 것 같아요.',
 '["그렇다","보통이다","아니다"]'::jsonb, '저작권', 21, true),
((SELECT id FROM s), 22, 'single_choice',
 '정부·학교·회사(기업)가 어린이를 위해 온라인 나쁜 콘텐츠를 없애려고 충분히 노력하고 있다고 생각해요.',
 '["그렇다","보통이다","아니다"]'::jsonb, '정책', 22, true),
((SELECT id FROM s), 23, 'single_choice',
 '온라인에서 위험한 일이 생기면 누구에게 도움을 청해야 하는지 알아요.',
 '["잘 알아요","조금 알아요","잘 몰라요"]'::jsonb, '대응', 23, true),
((SELECT id FROM s), 24, 'single_choice',
 '이 문제를 해결하려면 누가 가장 노력해야 할까요?',
 '["정부(나라)","회사(기업)","우리 모두","잘 모르겠어요"]'::jsonb, '정책', 24, true),
((SELECT id FROM s), 25, 'single_choice',
 '나도 친구들에게 온라인 안전을 알려주는 캠페인에 참여하고 싶어요.',
 '["그렇다","보통이다","아니다"]'::jsonb, '참여', 25, true),
((SELECT id FROM s), 26, 'long_text',
 '온라인을 더 안전하게 만들기 위해 하고 싶은 말이 있으면 자유롭게 적어 주세요.',
 NULL, '의견', 26, false)
ON CONFLICT (survey_id, qno) DO NOTHING;


-- ─────────────────────────────────────────────────────────────
-- 4. survey_questions — 중학생용 (26문항)
-- ─────────────────────────────────────────────────────────────
WITH s AS (SELECT id FROM public.surveys WHERE target_band='middle' AND scope='national' LIMIT 1)
INSERT INTO public.survey_questions (survey_id, qno, qtype, text, options, topic_tag, sort_order, required) VALUES
((SELECT id FROM s), 1, 'single_choice',
 '온라인 콘텐츠(영상·게임·SNS 등)를 얼마나 자주 이용하나요?',
 '["거의 매일 1시간 이상","주 3~4회","주 1~2회","거의 이용하지 않음"]'::jsonb, '온라인이용', 1, true),
((SELECT id FROM s), 2, 'multi_choice',
 '주로 이용하는 콘텐츠는 무엇인가요? (여러 개 선택 가능)',
 '["영상(유튜브 등)","게임","SNS","웹툰·웹소설","온라인 커뮤니티","기타"]'::jsonb, '온라인이용', 2, true),
((SELECT id FROM s), 3, 'single_choice',
 '나는 온라인 콘텐츠가 유익한지 유해한지 스스로 판단할 수 있다.',
 '["매우 그렇다","그렇다","보통이다","그렇지 않다","전혀 그렇지 않다"]'::jsonb, '인식', 3, true),
((SELECT id FROM s), 4, 'single_choice',
 '온라인 유해콘텐츠 문제가 심각하다고 인식하고 있다.',
 '["매우 그렇다","그렇다","보통이다","그렇지 않다","전혀 그렇지 않다"]'::jsonb, '인식', 4, true),
((SELECT id FROM s), 5, 'single_choice',
 '아동·청소년이 온라인에서 유해콘텐츠에 여과 없이 쉽게 노출되고 있다고 생각한다.',
 '["매우 그렇다","그렇다","보통이다","그렇지 않다","전혀 그렇지 않다"]'::jsonb, '인식', 5, true),
((SELECT id FROM s), 6, 'single_choice',
 '온라인 유해콘텐츠가 청소년의 생각·언어·행동에 영향을 준다고 생각한다.',
 '["매우 그렇다","그렇다","보통이다","그렇지 않다","전혀 그렇지 않다"]'::jsonb, '인식', 6, true),
((SELECT id FROM s), 7, 'single_choice',
 '지금까지 온라인에서 유해콘텐츠를 접한 적이 있다.',
 '["있다","없다","응답하고 싶지 않음"]'::jsonb, '경험', 7, true),
((SELECT id FROM s), 8, 'multi_choice',
 '(접한 적이 있다면) 어떤 유형이었나요? (여러 개 선택 가능)',
 '["폭력물","음란물·딥페이크","도박·불법 베팅","낯선 사람의 접근(그루밍)","혐오·욕설","불법 알바·약물 권유","불법 공유(저작권 침해)","기타","해당 없음"]'::jsonb, '경험', 8, false),
((SELECT id FROM s), 9, 'single_choice',
 '친구나 지인이 온라인 유해콘텐츠로 피해를 본 적이 있다.',
 '["있다","없다","잘 모르겠다"]'::jsonb, '경험', 9, true),
((SELECT id FROM s), 10, 'single_choice',
 '온라인에서 모르는 사람이 접근해 친구 요청·개인정보·사진 등을 요구한 적이 있다.',
 '["있다","없다","응답하고 싶지 않음"]'::jsonb, '그루밍', 10, true),
((SELECT id FROM s), 11, 'single_choice',
 '학교에서 온라인에서 보고 배운 거친 말·행동을 하는 친구를 본 적이 있다.',
 '["자주 본다","가끔 본다","거의 없다"]'::jsonb, '경험', 11, true),
((SELECT id FROM s), 12, 'single_choice',
 '유해콘텐츠를 발견했을 때 부모님이나 선생님께 말한 적이 있다.',
 '["있다","없다","발견한 적 없음"]'::jsonb, '대응', 12, true),
((SELECT id FROM s), 13, 'single_choice',
 '학교에서 ‘유해콘텐츠를 발견하면 어떤 절차로 조치해야 하는지’ 교육받은 적이 있다.',
 '["있다","없다","기억나지 않음"]'::jsonb, '대응', 13, true),
((SELECT id FROM s), 14, 'multi_choice',
 '유해콘텐츠를 어디에 신고하는지 알고 있다. (여러 개 선택 가능)',
 '["경찰 112","디지털성범죄(1366·디성센터)","학교폭력 117","플랫폼 신고기능","방심위 등 기관","모름"]'::jsonb, '대응', 14, true),
((SELECT id FROM s), 15, 'single_choice',
 '대응 방법을 모를 경우, 온라인 안전에 대한 정기 교육이 학생들에게 유익하다고 생각한다.',
 '["매우 그렇다","그렇다","보통이다","그렇지 않다","전혀 그렇지 않다"]'::jsonb, '대응', 15, true),
((SELECT id FROM s), 16, 'single_choice',
 '저작권 침해가 어떤 행위인지 알고 있다.',
 '["잘 알고 있다","들어는 봤다","잘 모른다"]'::jsonb, '저작권', 16, true),
((SELECT id FROM s), 17, 'single_choice',
 '저작권이 영화·음반·출판·게임·소프트웨어 등 산업을 보호한다는 것을 알고 있다.',
 '["잘 알고 있다","들어는 봤다","잘 모른다"]'::jsonb, '저작권', 17, true),
((SELECT id FROM s), 18, 'single_choice',
 '온라인에서 타인의 저작물이나 불법 소프트웨어를 복제·전송·배포하면 청소년이라도 강력한 처벌을 받을 수 있다는 것을 알고 있다.',
 '["잘 알고 있다","들어는 봤다","잘 모른다"]'::jsonb, '저작권', 18, true),
((SELECT id FROM s), 19, 'single_choice',
 '그러한 처벌로 전과(범죄 기록)가 남을 수 있다는 것을 알고 있다.',
 '["잘 알고 있다","들어는 봤다","잘 모른다"]'::jsonb, '저작권', 19, true),
((SELECT id FROM s), 20, 'single_choice',
 '지금까지 학교에서 저작권 침해 근절을 위한 교육을 받은 적이 있다.',
 '["있다","없다","기억나지 않음"]'::jsonb, '저작권', 20, true),
((SELECT id FROM s), 21, 'single_choice',
 '저작권에 관한 정기적인 교육이 학생들에게 유익하다고 생각한다.',
 '["매우 그렇다","그렇다","보통이다","그렇지 않다","전혀 그렇지 않다"]'::jsonb, '저작권', 21, true),
((SELECT id FROM s), 22, 'single_choice',
 '우리나라 교육당국·정부·사법기관·기업이 온라인 유해콘텐츠 근절에 충분히 노력하고 있다고 생각한다.',
 '["매우 그렇다","그렇다","보통이다","그렇지 않다","전혀 그렇지 않다"]'::jsonb, '정책', 22, true),
((SELECT id FROM s), 23, 'single_choice',
 '미국 등은 온라인 유해콘텐츠를 ‘아동학대’ 문제로 보고 정부가 적극 개입한다. 우리 정부·기업도 아동·청소년 보호를 위해 충분히 노력하고 있다고 생각한다.',
 '["매우 그렇다","그렇다","보통이다","그렇지 않다","전혀 그렇지 않다"]'::jsonb, '정책', 23, true),
((SELECT id FROM s), 24, 'single_choice',
 '이 문제를 근본적으로 해결하려면 누가 가장 노력해야 한다고 생각하는가?',
 '["정부","기업(플랫폼)","시민·학생","모두 함께"]'::jsonb, '정책', 24, true),
((SELECT id FROM s), 25, 'single_choice',
 '또래에게 온라인 안전을 알리는 캠페인에 참여할 의향이 있다.',
 '["매우 그렇다","그렇다","보통이다","그렇지 않다","전혀 그렇지 않다"]'::jsonb, '참여', 25, true),
((SELECT id FROM s), 26, 'long_text',
 '온라인을 더 안전하게 만들기 위해 정부·기업·학교·시민에게 바라는 점을 자유롭게 적어 주세요.',
 NULL, '의견', 26, false)
ON CONFLICT (survey_id, qno) DO NOTHING;


-- ─────────────────────────────────────────────────────────────
-- 5. survey_questions — 고등학생용 (26문항)
-- ─────────────────────────────────────────────────────────────
WITH s AS (SELECT id FROM public.surveys WHERE target_band='high' AND scope='national' LIMIT 1)
INSERT INTO public.survey_questions (survey_id, qno, qtype, text, options, topic_tag, sort_order, required) VALUES
((SELECT id FROM s), 1, 'single_choice',
 '온라인 콘텐츠(영상·게임·SNS·커뮤니티 등)를 평소 얼마나 이용하나요?',
 '["하루 2시간 이상","하루 1~2시간","주 3~4회","주 1~2회 이하"]'::jsonb, '온라인이용', 1, true),
((SELECT id FROM s), 2, 'multi_choice',
 '주로 이용하는 콘텐츠 유형은 무엇인가요? (여러 개 선택 가능)',
 '["영상 플랫폼","게임","SNS","웹툰·웹소설","온라인 커뮤니티","스트리밍·라이브","기타"]'::jsonb, '온라인이용', 2, true),
((SELECT id FROM s), 3, 'single_choice',
 '나는 온라인 콘텐츠의 유익성과 유해성을 스스로 비판적으로 판단할 수 있다.',
 '["매우 그렇다","그렇다","보통이다","그렇지 않다","전혀 그렇지 않다"]'::jsonb, '인식', 3, true),
((SELECT id FROM s), 4, 'single_choice',
 '온라인 유해콘텐츠 문제의 심각성을 평소 충분히 인식하고 있다.',
 '["매우 그렇다","그렇다","보통이다","그렇지 않다","전혀 그렇지 않다"]'::jsonb, '인식', 4, true),
((SELECT id FROM s), 5, 'single_choice',
 '아동·청소년이 온라인에서 유해콘텐츠에 여과 없이, 그리고 쉽게 노출되고 있다고 생각한다.',
 '["매우 그렇다","그렇다","보통이다","그렇지 않다","전혀 그렇지 않다"]'::jsonb, '인식', 5, true),
((SELECT id FROM s), 6, 'single_choice',
 '온라인 유해콘텐츠가 청소년의 가치관·성인식·정서와 행동에 실질적 영향을 미친다고 생각한다.',
 '["매우 그렇다","그렇다","보통이다","그렇지 않다","전혀 그렇지 않다"]'::jsonb, '인식', 6, true),
((SELECT id FROM s), 7, 'single_choice',
 '지금까지 온라인에서 유해콘텐츠를 직접 접한 적이 있다.',
 '["있다","없다","응답하고 싶지 않음"]'::jsonb, '경험', 7, true),
((SELECT id FROM s), 8, 'multi_choice',
 '(접한 적이 있다면) 어떤 유형이었나요? (여러 개 선택 가능)',
 '["폭력물","음란물·딥페이크 합성물","온라인 도박·불법 베팅","그루밍(낯선 사람의 단계적 접근)","혐오 표현·사이버불링","불법 알바·마약 권유","저작권 침해(불법 공유·재유포)","AI 생성 유해물","기타","해당 없음"]'::jsonb, '경험', 8, false),
((SELECT id FROM s), 9, 'single_choice',
 '친구나 지인이 온라인 유해콘텐츠로 피해(정신적·금전적·관계적)를 입은 적이 있다.',
 '["있다","없다","잘 모르겠다"]'::jsonb, '경험', 9, true),
((SELECT id FROM s), 10, 'single_choice',
 '온라인에서 모르는 사람이 접근해 친밀감을 쌓은 뒤 개인정보·사진·만남 등을 요구한 적이 있다.',
 '["있다","없다","응답하고 싶지 않음"]'::jsonb, '그루밍', 10, true),
((SELECT id FROM s), 11, 'single_choice',
 '학교에서 온라인에서 보고 배운 거친 언어·행동을 일상적으로 하는 친구를 본 적이 있다.',
 '["자주 본다","가끔 본다","거의 없다"]'::jsonb, '경험', 11, true),
((SELECT id FROM s), 12, 'single_choice',
 '유해콘텐츠를 발견했을 때 부모님이나 선생님 등 어른에게 알린 적이 있다.',
 '["있다","없다","발견한 적 없음"]'::jsonb, '대응', 12, true),
((SELECT id FROM s), 13, 'single_choice',
 '학교에서 ‘유해콘텐츠 발견 시 신고·차단 등 조치 절차’에 대해 구체적으로 교육받은 적이 있다.',
 '["있다","없다","기억나지 않음"]'::jsonb, '대응', 13, true),
((SELECT id FROM s), 14, 'multi_choice',
 '유해콘텐츠를 어디에, 어떻게 신고하는지 알고 있다. (여러 개 선택 가능)',
 '["경찰 112","디지털성범죄(1366·디지털성범죄피해자지원센터)","학교폭력 117","플랫폼 자체 신고기능","방송미디어통신심의위원회 등 기관","모름"]'::jsonb, '대응', 14, true),
((SELECT id FROM s), 15, 'single_choice',
 '대응 방법을 모르는 학생이 많은 현실에서, 온라인 안전에 대한 정기적 교육이 학생들에게 유익하다고 생각한다.',
 '["매우 그렇다","그렇다","보통이다","그렇지 않다","전혀 그렇지 않다"]'::jsonb, '대응', 15, true),
((SELECT id FROM s), 16, 'single_choice',
 '저작권 침해가 구체적으로 어떤 행위(복제·전송·배포 등)인지 알고 있다.',
 '["잘 알고 있다","들어는 봤다","잘 모른다"]'::jsonb, '저작권', 16, true),
((SELECT id FROM s), 17, 'single_choice',
 '저작권이 영화·음반·출판·게임·소프트웨어 등 핵심 산업을 보호하는 권리라는 것을 알고 있다.',
 '["잘 알고 있다","들어는 봤다","잘 모른다"]'::jsonb, '저작권', 17, true),
((SELECT id FROM s), 18, 'single_choice',
 '대부분의 저작권 침해는 온라인에서 손쉽게 이루어지며, 특히 청소년이 타인의 저작물·불법 소프트웨어를 복제·전송·배포하면 저작권법에 따라 강력히 처벌(징역 또는 벌금)될 수 있다는 것을 알고 있다.',
 '["잘 알고 있다","들어는 봤다","잘 모른다"]'::jsonb, '저작권', 18, true),
((SELECT id FROM s), 19, 'single_choice',
 '그러한 처벌로 전과(범죄 기록)가 남아 진학·취업 등에 불이익이 될 수 있다는 것을 알고 있다.',
 '["잘 알고 있다","들어는 봤다","잘 모른다"]'::jsonb, '저작권', 19, true),
((SELECT id FROM s), 20, 'single_choice',
 '지금까지 학교에서 저작권 침해 근절을 위한 교육을 받은 적이 있다.',
 '["있다","없다","기억나지 않음"]'::jsonb, '저작권', 20, true),
((SELECT id FROM s), 21, 'single_choice',
 '저작권에 관한 정기적 교육이 학생들에게 유익하다고 생각한다.',
 '["매우 그렇다","그렇다","보통이다","그렇지 않다","전혀 그렇지 않다"]'::jsonb, '저작권', 21, true),
((SELECT id FROM s), 22, 'single_choice',
 '우리나라 교육당국·정부·사법기관·기업이 온라인 유해콘텐츠 근절을 위해 충분한 노력을 기울이고 있다고 생각한다.',
 '["매우 그렇다","그렇다","보통이다","그렇지 않다","전혀 그렇지 않다"]'::jsonb, '정책', 22, true),
((SELECT id FROM s), 23, 'single_choice',
 '미국 등은 온라인 유해콘텐츠를 ‘아동학대’ 사안으로 규정해 정부가 적극 개입하고 빅테크에 의무를 부과한다. 이에 비해 우리 정부·기업은 아동·청소년 보호를 위해 충분히 노력하고 있다고 생각한다.',
 '["매우 그렇다","그렇다","보통이다","그렇지 않다","전혀 그렇지 않다"]'::jsonb, '정책', 23, true),
((SELECT id FROM s), 24, 'single_choice',
 '이 문제에서 근본적 성과를 내려면 정부·기업·시민 중 누가 가장 노력해야 한다고 생각하는가?',
 '["정부(법·제도·예산)","기업(플랫폼의 책임)","시민·청소년의 참여","셋의 협력 없이는 불가능"]'::jsonb, '정책', 24, true),
((SELECT id FROM s), 25, 'single_choice',
 '또래 교육·캠페인 제작·모니터링 참여 등 온라인 안전을 위한 활동에 직접 참여할 의향이 있다.',
 '["매우 그렇다","그렇다","보통이다","그렇지 않다","전혀 그렇지 않다"]'::jsonb, '참여', 25, true),
((SELECT id FROM s), 26, 'long_text',
 '온라인 유해콘텐츠 문제 해결을 위해 정부·기업·학교·시민에게 제안하거나 바라는 점을 자유롭게 적어 주세요.',
 NULL, '의견', 26, false)
ON CONFLICT (survey_id, qno) DO NOTHING;


-- ─────────────────────────────────────────────────────────────
-- 6. 캠페인 안내 컨텐츠 (학생용 / 학부모용 default)
-- ─────────────────────────────────────────────────────────────
INSERT INTO public.campaign_overview_content (audience, section_key, title, body_md, sort_order, is_active) VALUES
('student', 'intro', '🎓 캠페인 소개',
 '**드래곤아이즈 온라인 유해콘텐츠 근절 캠페인**에 참여해 주셔서 고맙습니다.

이 캠페인은 우리 사회의 가장 큰 문제 중 하나인 **온라인 유해콘텐츠로부터 아동·청소년을 보호**하기 위해 시작되었어요. 여러분의 작은 참여가 모이면 사회 전체에 큰 변화를 만들 수 있습니다.',
 1, true),

('student', 'purpose', '🎯 캠페인의 목표',
 '- 온라인에서 무엇이 ‘좋은 것’이고 ‘나쁜 것’인지 스스로 판단하는 힘 기르기
- 그루밍·도박·불법 공유 같은 위험으로부터 자신을 지키는 방법 배우기
- 저작권을 존중하고 정당한 콘텐츠를 즐기는 습관 만들기
- 친구들에게도 안전한 온라인 문화를 알리는 또래 활동가 되기',
 2, true),

('student', 'benefits', '✨ 이 캠페인이 여러분에게 좋은 점',
 '- **봉사 시간 인정**: 설문을 성실히 완료하면 교육부 인정 봉사시간(4~6시간)이 적립됩니다.
- **자기 보호 능력 향상**: 위험을 미리 알고 대응하는 힘이 생깁니다.
- **사회 참여 경험**: 정책 개선의 근거가 되는 실제 데이터에 기여합니다.
- **저작권 인식**: 진학·취업 시 불이익이 될 수 있는 위반 행위를 미연에 방지합니다.',
 3, true),

('student', 'steps', '📋 캠페인 진행 순서',
 '**1단계** — 기본 교재 학습 (무료 제공, 어디서나 열람 가능)
**2단계** — 부모님 동의 시 프리미엄 교재 추가 학습 (선택 사항)
**3단계** — 학년에 맞는 설문 응시 (약 10~15분 · 익명)
**4단계** — 모든 문항 완료 후 **‘완료’ 버튼** 클릭
**5단계** — 봉사 시간 자동 적립 · 인증서 발급

> 💡 설문 링크와 QR 코드를 친구들에게 공유하면 더 많은 참여를 이끌어낼 수 있어요.',
 4, true),

('student', 'closing', '🌱 마지막으로',
 '여러분 한 사람 한 사람이 이 문제의 해결사예요. 솔직하게 답해 주세요. 정답은 없습니다.',
 5, true),

-- ─── 학부모용 ───
('parent', 'intro', '🌟 학부모님께',
 '**드래곤아이즈 온라인 유해콘텐츠 근절 캠페인**에 자녀를 등록해 주셔서 감사합니다.

이 캠페인 참여 자체는 **완전 무료**입니다. 자녀는 캠페인을 통해 봉사 시간(교육부 인정 4~6시간)을 받고 온라인 안전 의식을 키울 수 있습니다.',
 1, true),

('parent', 'purpose', '🎯 캠페인의 목적',
 '- 자녀가 온라인 위험(그루밍·도박·딥페이크·저작권 침해 등)으로부터 **스스로를 지키는 힘**을 기르도록 돕습니다.
- 자녀와 학부모가 함께 **민감한 사회 문제**에 대해 토론하는 계기를 만듭니다.
- 정책 개선의 실제 데이터를 모아 **사회 전체를 더 안전하게** 바꿉니다.',
 2, true),

('parent', 'parent_discussion', '💬 학부모님께 드리는 토론 가이드',
 '자녀가 학습한 내용을 함께 이야기 나누시면 효과가 배가 됩니다.

- 자녀가 어떤 온라인 콘텐츠를 보는지 **편안하게 들어보세요**.
- 아동·청소년 보호에 대한 **학부모로서의 인식과 의견**을 나눠 주세요.
- 자녀에게 바라는 점을 **솔직하게** 이야기해 주세요.
- 무엇보다 우리 자녀가 올바른 생각과 행동을 할 때 **주저함이 없는 사람**이 되도록 따뜻하게 지도해 주세요.

> 이 캠페인은 자녀와 유대감을 쌓는 좋은 기회입니다. 자녀의 응답을 통계로 볼 수 있도록 ‘**내 자녀의 캠페인 둘러보기**’ 기능을 제공합니다.',
 3, true),

('parent', 'premium_recommend', '📚 프리미엄 자료 안내 (선택 사항)',
 '캠페인의 기본 교재는 **무료**로 제공됩니다.

원활한 캠페인 수행을 위해 **프리미엄 교재** 구독을 추천드립니다. 보다 구체적이고 자세한 교육 자료(영상·심화 자료·전문가 강의 등)가 포함되어 있어 자녀와 함께 살펴보시면서 깊이 있는 대화를 나누실 수 있습니다.

**연 1만원** · 자녀가 여러 명이어도 한 번의 결제로 모두 적용됩니다.',
 4, true),

('parent', 'steps', '📋 진행 순서',
 '**1단계** — 자녀 등록 (자녀 페이지에서 본인 인증)
**2단계** — 무료 기본 교재 함께 살펴보기
**3단계** — (선택) 프리미엄 자료 결제 → 자녀에게 자동 해금
**4단계** — 자녀의 설문 링크/QR 공유 (학부모 본인 SNS·메신저 등)
**5단계** — 자녀의 설문 완료 후 봉사 시간 적립 확인',
 5, true)
ON CONFLICT (audience, section_key) DO UPDATE SET
    body_md = EXCLUDED.body_md,
    title   = EXCLUDED.title,
    sort_order = EXCLUDED.sort_order,
    updated_at = NOW();


-- ─────────────────────────────────────────────────────────────
-- 7. 검증
-- ─────────────────────────────────────────────────────────────
SELECT 'campaigns'                AS tbl, COUNT(*) AS rows FROM public.campaigns WHERE year = 2026
UNION ALL
SELECT 'surveys (national)'       AS tbl, COUNT(*) FROM public.surveys WHERE scope = 'national'
UNION ALL
SELECT 'survey_questions'         AS tbl, COUNT(*) FROM public.survey_questions
UNION ALL
SELECT 'campaign_overview_content' AS tbl, COUNT(*) FROM public.campaign_overview_content;
-- 기대:
--   campaigns                 rows=1
--   surveys (national)        rows=3 (초/중/고)
--   survey_questions          rows=78 (26 × 3)
--   campaign_overview_content rows=10 (학생5 + 학부모5)

-- 학년대별 문항 수 확인
SELECT s.target_band, COUNT(q.id) AS qcount
FROM public.surveys s
LEFT JOIN public.survey_questions q ON q.survey_id = s.id
WHERE s.scope = 'national'
GROUP BY s.target_band
ORDER BY s.target_band;
-- 기대: 각 band별 26개

-- 끝.
