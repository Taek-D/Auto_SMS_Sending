PyInstaller로 exe 빌드를 실행해주세요.

1. `python -m py_compile coupang_sms.py` 로 구문 검사
2. 구문 검사 통과 시 `pyinstaller 쿠팡문자발송기_v2.spec` 로 빌드
3. `dist/쿠팡문자발송기_v2.exe` 파일이 생성되었는지 확인
4. 빌드 결과(성공/실패, 파일 크기)를 알려주세요
