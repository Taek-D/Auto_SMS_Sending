---
name: tkinter-threading
description: tkinter GUI + 스레딩 패턴 작업 시 적용. Use when working with UI updates, background tasks, threading.
---

# tkinter + Threading 패턴

## 핵심 규칙
- UI 업데이트는 반드시 메인 스레드에서 실행
- 백그라운드 작업 → `threading.Thread(daemon=True)`
- 백그라운드 → UI 업데이트: `root.after(0, callback)` 사용

## 올바른 패턴
```python
# 백그라운드에서 UI 업데이트
def background_task(self):
    result = self.api_call()  # 네트워크 호출
    self.root.after(0, lambda: self.update_ui(result))  # UI 업데이트
```

## 금지 패턴
```python
# 절대 하지 말 것: 백그라운드 스레드에서 직접 위젯 조작
def background_task(self):
    self.label.configure(text="결과")  # 크래시 위험!
```

## 버튼 상태 관리
- 작업 시작 시 버튼 disable → 완료 시 enable
- `self.btn.configure(state="disabled" / "normal")`

## 로그 기록
- `self.log()` 메서드 사용 (thread-safe, log_lock 적용됨)
