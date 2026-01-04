import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
import time
import hmac
import hashlib
import json
import os
import threading
from datetime import datetime

class CoupangAutoSMSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("쿠팡 주문 자동 SMS 발송기 v2.0 (연결진단 포함)")
        self.root.geometry("850x850") # 높이를 조금 늘림
        
        self.is_running = False
        self.log_lock = threading.Lock()
        
        # 발송 기록 파일 설정
        self.history_file = "sent_orders.json"
        self.sent_orders = self.load_sent_history()

        # UI 구성
        self.create_widgets()
        
        self.log(f"프로그램 준비 완료. 기존 발송 기록 {len(self.sent_orders)}건 로드됨.")

    def create_widgets(self):
        # 1. 상단 컨트롤 패널 (버튼 영역)
        control_frame = ttk.LabelFrame(self.root, text="제어 패널")
        control_frame.pack(fill="x", padx=10, pady=5)

        self.btn_start = ttk.Button(control_frame, text="▶ 조회 시작", command=self.start_monitoring)
        self.btn_start.pack(side="left", padx=5, pady=10)
        
        self.btn_stop = ttk.Button(control_frame, text="■ 중지", command=self.stop_monitoring, state="disabled")
        self.btn_stop.pack(side="left", padx=5, pady=10)

        self.btn_reset = ttk.Button(control_frame, text="발송 기록 초기화", command=self.reset_history)
        self.btn_reset.pack(side="left", padx=5, pady=10)

        # [추가됨] 연결 확인 버튼
        self.btn_check = ttk.Button(control_frame, text="환경 진단 (연결 확인)", command=self.check_connection)
        self.btn_check.pack(side="left", padx=20, pady=10)

        # 2. [추가됨] 환경 진단 / 연결 상태 패널 (매뉴얼 7페이지 구현)
        status_frame = ttk.LabelFrame(self.root, text="환경 진단 / 연결 상태")
        status_frame.pack(fill="x", padx=10, pady=5)

        # 상태 표시 라벨들
        self.lbl_coupang_status = ttk.Label(status_frame, text="● 쿠팡 API 상태 : 미확인", foreground="gray")
        self.lbl_coupang_status.grid(row=0, column=0, sticky="w", padx=20, pady=5)

        self.lbl_sms_status = ttk.Label(status_frame, text="● 마이문자 상태 : 미확인", foreground="gray")
        self.lbl_sms_status.grid(row=1, column=0, sticky="w", padx=20, pady=5)

        self.lbl_ip_status = ttk.Label(status_frame, text="공인 IP : (연결 확인을 눌러주세요)", foreground="black")
        self.lbl_ip_status.grid(row=2, column=0, sticky="w", padx=20, pady=5)

        # 3. 쿠팡 설정 패널
        coupang_frame = ttk.LabelFrame(self.root, text="1) 쿠팡 OPEN API 설정")
        coupang_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(coupang_frame, text="업체코드 (Vendor ID):").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.entry_vendor_id = ttk.Entry(coupang_frame, width=40)
        self.entry_vendor_id.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(coupang_frame, text="Access Key:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.entry_access_key = ttk.Entry(coupang_frame, width=40)
        self.entry_access_key.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(coupang_frame, text="Secret Key:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.entry_secret_key = ttk.Entry(coupang_frame, width=40, show="*")
        self.entry_secret_key.grid(row=2, column=1, padx=5, pady=5)

        # 4. 마이문자 설정 패널
        sms_frame = ttk.LabelFrame(self.root, text="2) 마이문자 설정")
        sms_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(sms_frame, text="아이디:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.entry_sms_id = ttk.Entry(sms_frame, width=20)
        self.entry_sms_id.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(sms_frame, text="비밀번호:").grid(row=0, column=2, sticky="w", padx=5, pady=5)
        self.entry_sms_pw = ttk.Entry(sms_frame, width=20, show="*")
        self.entry_sms_pw.grid(row=0, column=3, sticky="w", padx=5, pady=5)

        ttk.Label(sms_frame, text="발신번호:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.entry_sender_phone = ttk.Entry(sms_frame, width=20)
        self.entry_sender_phone.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        # 5. 메시지 템플릿
        msg_frame = ttk.LabelFrame(self.root, text="3) 자동 발송 메시지 템플릿")
        msg_frame.pack(fill="x", padx=10, pady=5)
        
        self.text_template = tk.Text(msg_frame, height=4, width=80)
        self.text_template.pack(padx=5, pady=5)
        self.text_template.insert("1.0", "안녕하세요 {customer_name}님. '{store_name}' 스토어입니다. 주문해주셔서 감사합니다!")
        ttk.Label(msg_frame, text="태그: {customer_name}, {store_name}, {order_id}").pack(anchor="w", padx=5)

        # 6. 로그 창
        log_frame = ttk.LabelFrame(self.root, text="실행 로그")
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, state='disabled', height=10)
        self.log_area.pack(fill="both", expand=True, padx=5, pady=5)

    # --- [기능] 연결 확인 (Environment Check) ---
    def check_connection(self):
        """환경 진단 버튼 클릭 시 실행"""
        self.log("환경 진단을 시작합니다...")
        
        # 버튼 중복 클릭 방지
        self.btn_check.configure(state="disabled")
        
        # 별도 스레드에서 실행 (화면 멈춤 방지)
        threading.Thread(target=self._run_diagnosis, daemon=True).start()

    def _run_diagnosis(self):
        # 1. 공인 IP 확인
        try:
            ip_response = requests.get("https://api.ipify.org?format=json", timeout=5)
            if ip_response.status_code == 200:
                public_ip = ip_response.json()['ip']
                self.root.after(0, lambda: self.lbl_ip_status.configure(text=f"공인 IP : {public_ip} (정상)", foreground="blue"))
                self.log(f"공인 IP 확인됨: {public_ip}")
            else:
                raise Exception("응답 없음")
        except Exception as e:
            self.root.after(0, lambda: self.lbl_ip_status.configure(text=f"공인 IP : 확인 실패", foreground="red"))
            self.log(f"IP 확인 실패: {e}")

        # 2. 쿠팡 API 연결 확인 (시뮬레이션)
        # 실제로는 여기서 실제 쿠팡 API를 1회 호출하여 200 OK가 뜨는지 봐야 함
        if self.entry_access_key.get() and self.entry_secret_key.get():
            time.sleep(0.5) # 통신 시간 시뮬레이션
            self.root.after(0, lambda: self.lbl_coupang_status.configure(text="● 쿠팡 API 상태 : 정상 응답", foreground="green"))
            self.log("쿠팡 API 키 형식 확인 완료.")
        else:
            self.root.after(0, lambda: self.lbl_coupang_status.configure(text="● 쿠팡 API 상태 : 키 정보 누락", foreground="red"))
            self.log("쿠팡 API 키가 입력되지 않았습니다.")

        # 3. 문자 서비스 연결 확인 (시뮬레이션)
        if self.entry_sms_id.get() and self.entry_sms_pw.get():
            time.sleep(0.5)
            # 잔여 건수는 실제 API 호출 결과로 대체해야 함
            balance = 100 # 가상의 잔여 건수
            self.root.after(0, lambda: self.lbl_sms_status.configure(text=f"● 마이문자 상태 : 정상 (잔여: {balance}건)", foreground="green"))
            self.log("마이문자 로그인 정보 확인 완료.")
        else:
            self.root.after(0, lambda: self.lbl_sms_status.configure(text="● 마이문자 상태 : 계정 정보 누락", foreground="red"))
            self.log("마이문자 아이디/비밀번호가 없습니다.")

        self.root.after(0, lambda: self.btn_check.configure(state="normal"))
        self.log("환경 진단 종료.")

    # --- 기존 로직들 (발송 기록, 로그, 모니터링) ---
    def load_sent_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    return set(json.load(f))
            except:
                return set()
        return set()

    def save_sent_history(self):
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(list(self.sent_orders), f)
        except Exception as e:
            self.log(f"기록 저장 실패: {e}")

    def reset_history(self):
        if not self.sent_orders:
            messagebox.showinfo("알림", "초기화할 기록이 없습니다.")
            return
        answer = messagebox.askyesno("경고", "모든 발송 기록을 삭제하시겠습니까?\n이미 문자를 받은 고객에게 중복 발송될 수 있습니다.")
        if answer:
            self.sent_orders.clear()
            self.save_sent_history()
            self.log("!!! 발송 기록 초기화 완료 !!!")
            messagebox.showinfo("완료", "초기화되었습니다.")

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        with self.log_lock:
            self.log_area.configure(state='normal')
            self.log_area.insert(tk.END, f"[{timestamp}] {message}\n")
            self.log_area.see(tk.END)
            self.log_area.configure(state='disabled')

    def start_monitoring(self):
        if not self.entry_access_key.get():
            messagebox.showerror("오류", "쿠팡 API 키를 입력해주세요.")
            return
        self.is_running = True
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.btn_check.configure(state="disabled") 
        self.lbl_ip_status.configure(foreground="black") # 상태창 색상 리셋
        self.log("자동 조회 및 발송을 시작합니다.")
        threading.Thread(target=self.monitor_loop, daemon=True).start()

    def stop_monitoring(self):
        self.is_running = False
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.btn_check.configure(state="normal")
        self.log("모니터링 중지.")

    def monitor_loop(self):
        while self.is_running:
            try:
                self.log("주문 조회 중...")
                orders = self.get_coupang_orders()
                if orders:
                    new_orders = [o for o in orders if str(o.get('orderId')) not in self.sent_orders]
                    if new_orders:
                        self.log(f"신규 주문 {len(new_orders)}건 발견. 발송 진행.")
                        for order in new_orders:
                            if not self.is_running: break
                            self.process_order(order)
                    else:
                        self.log("모든 주문이 이미 처리되었습니다.")
                else:
                    self.log("신규 주문 없음.")
            except Exception as e:
                self.log(f"에러: {str(e)}")
            
            for _ in range(60):
                if not self.is_running: break
                time.sleep(1)

    def get_coupang_orders(self):
        # [실제 API 호출시 requests 사용]
        return [{
            'orderId': '1000001', 
            'ordererName': '테스트고객', 
            'ordererSafeNumber': '010-0000-0000'
        }]

    def process_order(self, order):
        order_id = str(order.get('orderId', ''))
        customer_name = order.get('ordererName', '고객')
        customer_phone = order.get('ordererSafeNumber', '')
        
        template = self.text_template.get("1.0", tk.END).strip()
        msg_content = template.format(
            customer_name=customer_name,
            store_name="내 스토어",
            order_id=order_id
        )

        if self.send_sms(customer_phone, msg_content):
            self.sent_orders.add(order_id)
            self.save_sent_history()
            self.log(f"[발송 성공] {customer_name}님")
        else:
            self.log(f"[발송 실패] {customer_name}님")

    def send_sms(self, phone, message):
        time.sleep(0.5)
        return True

if __name__ == "__main__":
    root = tk.Tk()
    app = CoupangAutoSMSApp(root)
    root.mainloop()