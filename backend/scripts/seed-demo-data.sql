-- carefull 데모 데이터 시드 스크립트
-- 실행: psql -U <user> -d <database> -f seed-demo-data.sql
-- 멱등성: 동일 이메일 데이터가 이미 존재하면 건너뜀
-- 생성 데이터: 보호자 계정, 환자, 기기, 스케줄 3개, 복약 로그 90건 (30일×3회), 알림 10개

DO $$
DECLARE
    v_mem_id      INTEGER;
    v_patient_id  INTEGER;
    v_medi_id_1   INTEGER;
    v_medi_id_2   INTEGER;
    v_medi_id_3   INTEGER;
    v_sche_id_1   INTEGER;
    v_sche_id_2   INTEGER;
    v_sche_id_3   INTEGER;
    i             INTEGER;
    v_success     BOOLEAN;
    v_base_ts     TIMESTAMPTZ;
BEGIN
    RAISE NOTICE '=== carefull 데모 데이터 시드 시작 ===';

    -- ── 1. 데모 보호자 계정 ──────────────────────────────────────────────────
    SELECT mem_id INTO v_mem_id FROM members WHERE email = 'demo@carefull.app' LIMIT 1;
    IF v_mem_id IS NULL THEN
        INSERT INTO members (social_id, provider, email, nick, profile_img, joined_at)
        VALUES ('DEMO_CAREFULL_ADMIN_VIEW', 'kakao', 'demo@carefull.app', '김보호자', '', NOW() - INTERVAL '60 days')
        RETURNING mem_id INTO v_mem_id;
        RAISE NOTICE '[1] 보호자 계정 생성 완료: mem_id=%', v_mem_id;
    ELSE
        RAISE NOTICE '[1] 보호자 계정 이미 존재: mem_id=%', v_mem_id;
    END IF;

    -- ── 2. 환자 등록 ─────────────────────────────────────────────────────────
    SELECT patient_id INTO v_patient_id FROM patients WHERE mem_id = v_mem_id LIMIT 1;
    IF v_patient_id IS NULL THEN
        INSERT INTO patients (mem_id, patient_name, birthdate, gender, phone, bloodtype, guardian_name, created_at)
        VALUES (
            v_mem_id,
            '김순자',
            '1952-03-15',
            'F',
            '010-1234-5678',
            'A+',
            '김보호자',
            NOW() - INTERVAL '55 days'
        )
        RETURNING patient_id INTO v_patient_id;
        RAISE NOTICE '[2] 환자 등록 완료: patient_id=%', v_patient_id;
    ELSE
        RAISE NOTICE '[2] 환자 이미 존재: patient_id=%', v_patient_id;
    END IF;

    -- ── 3. 기기 등록 ─────────────────────────────────────────────────────────
    IF NOT EXISTS (SELECT 1 FROM devices WHERE patient_id = v_patient_id) THEN
        INSERT INTO devices (device_uid, patient_id, device_status, device_name, registered_at, last_ping)
        VALUES (
            'CF-DEMO-0001',
            v_patient_id,
            'REGISTERED',
            '데모 디스펜서',
            NOW() - INTERVAL '50 days',
            NOW() - INTERVAL '2 hours'
        );
        RAISE NOTICE '[3] 기기 등록 완료: CF-DEMO-0001';
    ELSE
        RAISE NOTICE '[3] 기기 이미 존재, 스킵';
    END IF;

    -- ── 4. 약 데이터 ─────────────────────────────────────────────────────────
    SELECT medi_id INTO v_medi_id_1 FROM medications WHERE medi_name = '아스피린 100mg (데모)' LIMIT 1;
    IF v_medi_id_1 IS NULL THEN
        INSERT INTO medications (medi_name) VALUES ('아스피린 100mg (데모)') RETURNING medi_id INTO v_medi_id_1;
    END IF;

    SELECT medi_id INTO v_medi_id_2 FROM medications WHERE medi_name = '암로디핀 5mg (데모)' LIMIT 1;
    IF v_medi_id_2 IS NULL THEN
        INSERT INTO medications (medi_name) VALUES ('암로디핀 5mg (데모)') RETURNING medi_id INTO v_medi_id_2;
    END IF;

    SELECT medi_id INTO v_medi_id_3 FROM medications WHERE medi_name = '메트포르민 500mg (데모)' LIMIT 1;
    IF v_medi_id_3 IS NULL THEN
        INSERT INTO medications (medi_name) VALUES ('메트포르민 500mg (데모)') RETURNING medi_id INTO v_medi_id_3;
    END IF;
    RAISE NOTICE '[4] 약 데이터: medi_id %, %, %', v_medi_id_1, v_medi_id_2, v_medi_id_3;

    -- ── 5. 복약 스케줄 (아침 08:00 / 점심 13:00 / 저녁 20:00) ────────────────
    SELECT sche_id INTO v_sche_id_1
    FROM schedules WHERE patient_id = v_patient_id AND time_to_take::TEXT = '08:00:00' LIMIT 1;
    IF v_sche_id_1 IS NULL THEN
        INSERT INTO schedules (patient_id, medi_id, time_to_take, start_date, end_date, dose_interval, status)
        VALUES (v_patient_id, v_medi_id_1, '08:00:00', CURRENT_DATE - 30, CURRENT_DATE + 60, 1, 'ACTIVE')
        RETURNING sche_id INTO v_sche_id_1;
    END IF;

    SELECT sche_id INTO v_sche_id_2
    FROM schedules WHERE patient_id = v_patient_id AND time_to_take::TEXT = '13:00:00' LIMIT 1;
    IF v_sche_id_2 IS NULL THEN
        INSERT INTO schedules (patient_id, medi_id, time_to_take, start_date, end_date, dose_interval, status)
        VALUES (v_patient_id, v_medi_id_2, '13:00:00', CURRENT_DATE - 30, CURRENT_DATE + 60, 1, 'ACTIVE')
        RETURNING sche_id INTO v_sche_id_2;
    END IF;

    SELECT sche_id INTO v_sche_id_3
    FROM schedules WHERE patient_id = v_patient_id AND time_to_take::TEXT = '20:00:00' LIMIT 1;
    IF v_sche_id_3 IS NULL THEN
        INSERT INTO schedules (patient_id, medi_id, time_to_take, start_date, end_date, dose_interval, status)
        VALUES (v_patient_id, v_medi_id_3, '20:00:00', CURRENT_DATE - 30, CURRENT_DATE + 60, 1, 'ACTIVE')
        RETURNING sche_id INTO v_sche_id_3;
    END IF;
    RAISE NOTICE '[5] 스케줄: sche_id %, %, %', v_sche_id_1, v_sche_id_2, v_sche_id_3;

    -- ── 6. 복약 로그 30일치 (아침·점심·저녁 각 30건 = 총 90건) ───────────────
    -- 성공률: 아침 73%, 점심 73%, 저녁 83%
    IF NOT EXISTS (SELECT 1 FROM activities WHERE patient_id = v_patient_id) THEN
        FOR i IN 1..30 LOOP
            -- [ 아침 08:00 ] missed: 3,6,10,14,17,21,25,29
            v_success := NOT (i = ANY(ARRAY[3,6,10,14,17,21,25,29]));
            v_base_ts := (CURRENT_DATE - i + TIME '08:00:00')::TIMESTAMP AT TIME ZONE 'Asia/Seoul';
            INSERT INTO activities
                (sche_id, patient_id, sche_time, actual_time, status, is_face_auth, is_ai_check, similarity_score, created_at)
            VALUES (
                v_sche_id_1,
                v_patient_id,
                v_base_ts,
                CASE WHEN v_success THEN v_base_ts + INTERVAL '2 minutes 30 seconds' ELSE NULL END,
                CASE WHEN v_success THEN 'SUCCESS' ELSE 'MISSED' END,
                v_success,
                v_success,
                CASE WHEN v_success THEN ROUND((0.85 + (i % 13) * 0.008)::NUMERIC, 3) ELSE NULL END,
                CASE WHEN v_success THEN v_base_ts + INTERVAL '2 minutes 30 seconds' ELSE v_base_ts + INTERVAL '31 minutes' END
            );

            -- [ 점심 13:00 ] missed: 2,5,9,12,16,19,23,27
            v_success := NOT (i = ANY(ARRAY[2,5,9,12,16,19,23,27]));
            v_base_ts := (CURRENT_DATE - i + TIME '13:00:00')::TIMESTAMP AT TIME ZONE 'Asia/Seoul';
            INSERT INTO activities
                (sche_id, patient_id, sche_time, actual_time, status, is_face_auth, is_ai_check, similarity_score, created_at)
            VALUES (
                v_sche_id_2,
                v_patient_id,
                v_base_ts,
                CASE WHEN v_success THEN v_base_ts + INTERVAL '3 minutes 10 seconds' ELSE NULL END,
                CASE WHEN v_success THEN 'SUCCESS' ELSE 'MISSED' END,
                v_success,
                v_success,
                CASE WHEN v_success THEN ROUND((0.88 + (i % 11) * 0.007)::NUMERIC, 3) ELSE NULL END,
                CASE WHEN v_success THEN v_base_ts + INTERVAL '3 minutes 10 seconds' ELSE v_base_ts + INTERVAL '32 minutes' END
            );

            -- [ 저녁 20:00 ] missed: 4,9,15,21,28
            v_success := NOT (i = ANY(ARRAY[4,9,15,21,28]));
            v_base_ts := (CURRENT_DATE - i + TIME '20:00:00')::TIMESTAMP AT TIME ZONE 'Asia/Seoul';
            INSERT INTO activities
                (sche_id, patient_id, sche_time, actual_time, status, is_face_auth, is_ai_check, similarity_score, created_at)
            VALUES (
                v_sche_id_3,
                v_patient_id,
                v_base_ts,
                CASE WHEN v_success THEN v_base_ts + INTERVAL '1 minute 45 seconds' ELSE NULL END,
                CASE WHEN v_success THEN 'SUCCESS' ELSE 'MISSED' END,
                v_success,
                v_success,
                CASE WHEN v_success THEN ROUND((0.86 + (i % 12) * 0.009)::NUMERIC, 3) ELSE NULL END,
                CASE WHEN v_success THEN v_base_ts + INTERVAL '1 minute 45 seconds' ELSE v_base_ts + INTERVAL '31 minutes' END
            );
        END LOOP;
        RAISE NOTICE '[6] 복약 로그 90건 (30일 × 3회) 생성 완료';
    ELSE
        RAISE NOTICE '[6] 복약 로그 이미 존재, 스킵';
    END IF;

    -- ── 7. 알림 내역 10건 ────────────────────────────────────────────────────
    IF NOT EXISTS (SELECT 1 FROM notifications WHERE mem_id = v_mem_id) THEN
        INSERT INTO notifications (mem_id, patient_id, noti_type, noti_title, noti_msg, is_received, created_at)
        VALUES
        (v_mem_id, v_patient_id, 'MISSED',  '미복용 알림', '김순자님이 오늘 점심 약을 복용하지 않으셨습니다.',         false, NOW() - INTERVAL '1 hour'),
        (v_mem_id, v_patient_id, 'SUCCESS', '복약 완료',   '김순자님이 오늘 아침 약을 복용하셨습니다.',                true,  NOW() - INTERVAL '5 hours 58 minutes'),
        (v_mem_id, v_patient_id, 'MISSED',  '미복용 알림', '김순자님이 어제 저녁 약을 복용하지 않으셨습니다.',         true,  NOW() - INTERVAL '1 day 3 hours 30 minutes'),
        (v_mem_id, v_patient_id, 'SUCCESS', '복약 완료',   '김순자님이 어제 점심 약을 복용하셨습니다.',                true,  NOW() - INTERVAL '1 day 9 hours 57 minutes'),
        (v_mem_id, v_patient_id, 'SUCCESS', '복약 완료',   '김순자님이 어제 아침 약을 복용하셨습니다.',                true,  NOW() - INTERVAL '1 day 13 hours 57 minutes'),
        (v_mem_id, v_patient_id, 'MISSED',  '미복용 알림', '김순자님이 이틀 전 저녁 약을 복용하지 않으셨습니다.',     true,  NOW() - INTERVAL '2 days 3 hours 30 minutes'),
        (v_mem_id, v_patient_id, 'SUCCESS', '복약 완료',   '김순자님이 이틀 전 점심 약을 복용하셨습니다.',             true,  NOW() - INTERVAL '2 days 9 hours 57 minutes'),
        (v_mem_id, v_patient_id, 'SUCCESS', '복약 완료',   '김순자님이 이틀 전 아침 약을 복용하셨습니다.',             true,  NOW() - INTERVAL '2 days 13 hours 57 minutes'),
        (v_mem_id, v_patient_id, 'MISSED',  '미복용 알림', '김순자님이 사흘 전 점심 약을 복용하지 않으셨습니다.',     true,  NOW() - INTERVAL '3 days 9 hours 3 minutes'),
        (v_mem_id, v_patient_id, 'SUCCESS', '복약 완료',   '김순자님이 사흘 전 아침 약을 복용하셨습니다.',             true,  NOW() - INTERVAL '3 days 13 hours 58 minutes');
        RAISE NOTICE '[7] 알림 10건 생성 완료';
    ELSE
        RAISE NOTICE '[7] 알림 이미 존재, 스킵';
    END IF;

    RAISE NOTICE '=== 데모 데이터 시드 완료! ===';
    RAISE NOTICE '  보호자 이메일 : demo@carefull.app';
    RAISE NOTICE '  환자          : 김순자 (1952-03-15, 만 72세)';
    RAISE NOTICE '  기기 UID      : CF-DEMO-0001';
    RAISE NOTICE '  스케줄        : 아침 08:00 / 점심 13:00 / 저녁 20:00';
    RAISE NOTICE '  복약 로그     : 90건 / 30일치, 성공률 약 77%%';
    RAISE NOTICE '  알림          : 10건';

EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE '시드 실패: % (SQLSTATE: %)', SQLERRM, SQLSTATE;
    RAISE;
END $$;
