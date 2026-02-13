---
name: coupang-api
description: 쿠팡 OPEN API 관련 작업 시 적용. Use when working with Coupang orders, API calls, HMAC signing.
---

# 쿠팡 OPEN API

## 인증 방식
- HMAC-SHA256 서명 필수
- 필요 키: Vendor ID + Access Key + Secret Key
- 서명 생성: datetime + method + path + query string 조합

## 주문 조회 API
- 엔드포인트: `/v2/providers/openapi/apis/api/v4/vendors/{vendorId}/ordersheets`
- Method: GET
- 응답 필드: orderId, ordererName, ordererSafeNumber

## 주의사항
- API 키를 코드에 하드코딩하지 않을 것 (UI 입력으로 받음)
- API 호출은 반드시 별도 스레드에서 실행 (UI 프리즈 방지)
- 호출 실패 시 재시도 로직 필요 (네트워크 불안정 대비)
- Rate limit 주의: 과도한 호출 자제
