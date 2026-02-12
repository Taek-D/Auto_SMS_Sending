# 쿠팡 주문 자동 SMS 발송기

## 프로젝트 개요
- Python tkinter 기반 Windows Desktop GUI 앱
- 쿠팡 OPEN API로 주문 조회 → 마이문자 API로 자동 SMS 발송
- PyInstaller로 .exe 빌드

## 기술 스택
- **언어**: Python 3
- **GUI**: tkinter
- **HTTP**: requests
- **빌드**: PyInstaller
- **플랫폼**: Windows

## 프로젝트 구조
```
coupang_sms.py          # 메인 앱 (전체 로직 단일 파일)
쿠팡문자발송기_v2.spec  # PyInstaller 빌드 설정
sent_orders.json        # 발송 기록 (런타임 생성)
build/                  # PyInstaller 빌드 중간 파일
dist/                   # 빌드 결과물 (.exe)
```

## 개발 순서
1. `coupang_sms.py` 수정
2. 테스트: `python coupang_sms.py`
3. 빌드: `pyinstaller 쿠팡문자발송기_v2.spec`

## 코딩 컨벤션
- 한국어 주석 사용
- tkinter 위젯은 `create_widgets()` 메서드에서 생성
- 네트워크 호출은 `threading.Thread(daemon=True)`로 실행 (UI 블로킹 방지)
- `self.log()` 메서드로 실행 로그 기록
- 발송 기록은 `sent_orders.json`에 저장하여 중복 발송 방지

## 주요 클래스
- `CoupangAutoSMSApp`: 메인 앱 클래스 (UI + 비즈니스 로직)

## 금지 사항
- build/, dist/ 디렉토리를 git에 커밋하지 않을 것
- API 키/비밀번호를 코드에 하드코딩하지 않을 것
- UI 스레드에서 네트워크 호출하지 않을 것 (tkinter 프리즈 방지)
