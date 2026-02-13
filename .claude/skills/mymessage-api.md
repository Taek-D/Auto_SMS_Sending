---
name: mymessage-api
description: 마이문자 SMS 발송 API 관련 작업 시 적용. Use when working with SMS sending, message templates.
---

# 마이문자 API

## 인증
- 아이디 + 비밀번호 기반 인증
- 발신번호 사전 등록 필요

## SMS 발송
- 수신번호, 발신번호, 메시지 내용 필수
- 메시지 길이: SMS 90바이트 / LMS 2000바이트

## 메시지 템플릿 태그
- `{customer_name}`: 주문자 이름
- `{store_name}`: 스토어 이름
- `{order_id}`: 주문번호

## 주의사항
- 중복 발송 방지: sent_orders.json으로 이미 발송된 주문 추적
- 발송 실패 시 로그에 기록하고 다음 주문 계속 처리
- 잔여 건수 확인 로직 권장
