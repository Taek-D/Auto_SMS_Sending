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
        self.root.title("쿠팡 주문 자동 SMS 발송기 v1.0")
        self.root.geometry("850x750")
        
        self.is_running = False
        self.log_lock = threading.Lock()
        
        # [기능] 발송된 주문 목록 파일 경로
        self.history_file = "sent_orders.json"
        
        # [기능] 앱 시작 시 기존 발송 기록 불러오기
        self.sent_orders = self.load_sent_history()

        # UI 구성
        self.create_widgets()
        
        # 시작 로그
        self.log(f"프로그램 시작. 기존 발송 기록 {len(self.sent_orders)}건 로드됨.")

    def create_widgets(self):
        # 1. 상단 컨트롤 패널 (버튼 영역)
        control_frame = ttk.LabelFrame(self.root, text="제어 및 상태")
        control_frame.pack(fill="x", padx=10, pady=5)

        self.btn_start = ttk.Button(control_frame, text="▶ 조회 시작", command=self.start_monitoring)
        self.btn_start.pack(side="left", padx=5, pady=10)
        
        self.btn_stop = ttk.Button(control_frame, text="■ 중지", command=self.stop_monitoring, state="disabled")
        self.btn_stop.pack(side="left", padx=5, pady=10)

        # [추가됨] 발송 기록 초기화 버튼
        self.btn_reset = ttk.Button(control_frame, text="↺ 발송 기록 초기화", command=self.reset_history)
        self.btn_reset.pack(side="left", padx=20, pady=10)

        self.lbl_status = ttk.Label(control_frame, text="상태: 대기 중", foreground="gray", font=("맑은 고딕", 10, "bold"))
        self.lbl_status.pack(side="right", padx=20)

        # 2. 쿠팡 설정 패널
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

        # 3. 마이문자 설정 패널
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

        # 4. 메시지 템플릿
        msg_frame = ttk.LabelFrame(self.root, text="3) 자동 발송 메시지 템플릿")
        msg_frame.pack(fill="x", padx=10, pady=5)
        
        self.text_template = tk.Text(msg_frame, height=4, width=80)
        self.text_template.pack(padx=5, pady=5)
        self.text_template.insert("1.0", "안녕하세요 {customer_name}님. '{store_name}' 스토어입니다. 주문해주셔서 감사합니다!")
        ttk.Label(msg_frame, text="태그: {customer_name}, {store_name}, {order_id}").pack(anchor="w", padx=5)

        # 5. 로그 창
        log_frame = ttk.LabelFrame(self.root, text="실행 로그")
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, state='disabled', height=10)
        self.log_area.pack(fill="both", expand=True, padx=5, pady=5)

    # --- [기능 1] 발송 기록 관리 (중복 방지 핵심) ---
    def load_sent_history(self):
        """파일에서 발송된 주문번호 목록을 불러옴"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    return set(json.load(f)) # 빠른 검색을 위해 set으로 변환
            except Exception as e:
                print(f"기록 로드 실패: {e}")
                return set()
        return set()

    def save_sent_history(self):
        """발송된 주문번호 목록을 파일에 저장"""
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(list(self.sent_orders), f) # set은 json 저장 불가하므로 list로 변환
        except Exception as e:
            self.log(f"기록 저장 실패: {e}")

    # --- [기능 2] 기록 초기화 버튼 동작 ---
    def reset_history(self):
        """발송 기록을 모두 삭제"""
        if not self.sent_orders:
            messagebox.showinfo("알림", "초기화할 기록이 없습니다.")
            return

        answer = messagebox.askyesno("경고", "모든 발송 기록을 삭제하시겠습니까?\n\n삭제 후 조회를 시작하면, 이미 문자를 받은 고객에게 또 문자가 발송될 수 있습니다.")
        if answer:
            self.sent_orders.clear()
            self.save_sent_history()
            self.log("!!! 발송 기록이 초기화되었습니다. (중복 발송 주의) !!!")
            messagebox.showinfo("완료", "발송 기록이 초기화되었습니다.")

    # --- UI 로그 출력 ---
    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        with self.log_lock:
            self.log_area.configure(state='normal')
            self.log_area.insert(tk.END, f"[{timestamp}] {message}\n")
            self.log_area.see(tk.END)
            self.log_area.configure(state='disabled')

    # --- 조회 및 실행 로직 ---
    def start_monitoring(self):
        if not self.entry_access_key.get() or not self.entry_secret_key.get():
            messagebox.showerror("오류", "쿠팡 API 키를 입력해주세요.")
            return

        self.is_running = True
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.btn_reset.configure(state="disabled") # 실행 중에는 초기화 금지
        self.lbl_status.configure(text="상태: 실행 중 (자동 조회)", foreground="green")
        
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        self.is_running = False
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.btn_reset.configure(state="normal")
        self.lbl_status.configure(text="상태: 중지됨", foreground="red")
        self.log("모니터링을 중지합니다.")

    def monitor_loop(self):
        while self.is_running:
            try:
                self.log("쿠팡 주문 조회 중...")
                orders = self.get_coupang_orders()
                
                if orders:
                    # 신규 주문 필터링 (이미 보낸 건 제외)
                    new_orders = [o for o in orders if str(o.get('orderId')) not in self.sent_orders]
                    
                    if new_orders:
                        self.log(f"전체 {len(orders)}건 중 신규 주문 {len(new_orders)}건 발견. 발송 시작.")
                        for order in new_orders:
                            if not self.is_running: break
                            self.process_order(order)
                    else:
                        self.log("주문이 있지만 모두 이미 발송된 건입니다.")
                else:
                    self.log("신규 주문(결제완료)이 없습니다.")
                    
            except Exception as e:
                self.log(f"에러 발생: {str(e)}")
            
            # 대기 시간 (60초)
            for _ in range(60):
                if not self.is_running: break
                time.sleep(1)

    # --- 쿠팡 API 연동 (가상) ---
    def generate_coupang_signature(self, method, path, secret_key, access_key):
        date_gmt = datetime.utcnow().strftime('%y%m%dT%H%M%SZ')
        message = date_gmt + method + path
        signature = hmac.new(secret_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).hexdigest()
        return f"CEA algorithm=HmacSHA256, access-key={access_key}, signed-date={date_gmt}, signature={signature}"

    def get_coupang_orders(self):
        # 실제 API 호출을 위한 준비
        # 주의: createdAtFrom/To 등을 현재 날짜 기준으로 동적 생성해야 함
        path = "/v2/providers/openapi/apis/api/v4/vendors/ordersheets"
        method = "GET"
        query = "?status=ACCEPT&maxPerPage=50" # 결제완료 상태만 조회
        
        # [테스트용 더미 데이터] 
        # 실제 사용 시 아래 주석을 풀고 requests 코드를 활성화하세요.
        # return [] 
        
        # 테스트를 위해 가짜 주문 1개를 리턴합니다 (처음 실행 시 발송됨)
        return [{
            'orderId': '1000001', 
            'ordererName': '테스트고객', 
            'ordererSafeNumber': '010-0000-0000'
        }]

    # --- 주문 처리 및 문자 발송 ---
    def process_order(self, order):
        order_id = str(order.get('orderId', ''))
        customer_name = order.get('ordererName', '고객')
        customer_phone = order.get('ordererSafeNumber', '')
        
        # 메시지 내용 생성
        template = self.text_template.get("1.0", tk.END).strip()
        msg_content = template.format(
            customer_name=customer_name,
            store_name="내 스토어", # 실제로는 설정에서 가져오거나 고정값 사용
            order_id=order_id
        )

        # 문자 발송 시도
        if self.send_sms(customer_phone, msg_content):
            # 성공 시 기록 저장
            self.sent_orders.add(order_id)
            self.save_sent_history()
            self.log(f"[발송 성공] {customer_name}님 (주문번호: {order_id})")
        else:
            self.log(f"[발송 실패] {customer_name}님 - 통신 오류")

    def send_sms(self, phone, message):
        """마이문자 API 연동 (가상 구현)"""
        # 실제 구현 시 마이문자 API 스펙에 맞게 requests.post 작성 필요
        # 예: requests.post("https://api.mymunja...", data={...})
        
        # 테스트를 위해 무조건 성공(True) 리턴
        time.sleep(0.5) # 전송 시간 시뮬레이션
        return True

if __name__ == "__main__":
    root = tk.Tk()
    app = CoupangAutoSMSApp(root)
    root.mainloop()