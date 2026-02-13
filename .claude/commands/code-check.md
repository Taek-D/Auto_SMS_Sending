coupang_sms.py 코드 품질을 검사해주세요.

확인 항목:
1. 구문 오류: `python -m py_compile coupang_sms.py`
2. 스레드 안전성: tkinter UI 업데이트가 `root.after()`를 통해 이루어지는지
3. API 키 노출: 하드코딩된 키/비밀번호가 없는지
4. 에러 처리: try-except 누락된 네트워크 호출이 없는지
5. 중복 발송 방지: sent_orders 로직이 정상인지

결과를 항목별로 정리해주세요.
