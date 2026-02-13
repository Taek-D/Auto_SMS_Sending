import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import csv
import requests
import time
import hmac
import hashlib
import json
import os
import threading
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
import pystray
from PIL import Image, ImageDraw

class CoupangAutoSMSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("쿠팡 주문 자동 SMS 발송기 v2.0 (연결진단 포함)")
        self.root.geometry("850x850") # 높이를 조금 늘림

        self.is_running = False
        self.log_lock = threading.Lock()

        # 설정 파일
        self.config_file = "config.json"

        # 발송 기록 파일 설정
        self.history_file = "sent_orders.json"
        self.sent_orders = self.load_sent_history()

        # 발송 상세 로그 (CSV 내보내기용)
        self.send_log = []

        # 트레이 아이콘
        self.tray_icon = None

        # UI 구성
        self.create_widgets()

        # 저장된 설정 불러오기
        self.load_config()

        # X 버튼 클릭 시 트레이로 최소화
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)

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

        self.btn_save = ttk.Button(control_frame, text="설정 저장", command=self.save_config)
        self.btn_save.pack(side="left", padx=5, pady=10)

        self.btn_export = ttk.Button(control_frame, text="로그 내보내기", command=self.export_log)
        self.btn_export.pack(side="left", padx=5, pady=10)

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

        # 4-1. 조회 설정 패널
        interval_frame = ttk.LabelFrame(self.root, text="조회 설정")
        interval_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(interval_frame, text="조회 간격(초):").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.entry_interval = ttk.Entry(interval_frame, width=10)
        self.entry_interval.insert(0, "60")
        self.entry_interval.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        ttk.Label(interval_frame, text="(최소 10초)").grid(row=0, column=2, sticky="w", padx=5, pady=5)

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

    # --- [기능] 시스템 트레이 ---
    def _create_tray_icon_image(self):
        img = Image.new("RGB", (64, 64), (0, 120, 215))
        draw = ImageDraw.Draw(img)
        draw.rectangle([16, 16, 48, 48], fill=(255, 255, 255))
        draw.text((22, 20), "SMS", fill=(0, 120, 215))
        return img

    def minimize_to_tray(self):
        self.root.withdraw()
        if self.tray_icon is None:
            menu = pystray.Menu(
                pystray.MenuItem("열기", self.restore_from_tray, default=True),
                pystray.MenuItem("종료", self.quit_app)
            )
            self.tray_icon = pystray.Icon(
                "coupang_sms",
                self._create_tray_icon_image(),
                "쿠팡 SMS 발송기",
                menu
            )
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        else:
            self.tray_icon.visible = True
        self.log("트레이로 최소화되었습니다.")

    def restore_from_tray(self):
        self.root.after(0, self.root.deiconify)

    def quit_app(self):
        self.is_running = False
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.after(0, self.root.destroy)

    # --- [기능] 설정 저장/불러오기 ---
    def save_config(self):
        config = {
            "vendor_id": self.entry_vendor_id.get(),
            "access_key": self.entry_access_key.get(),
            "secret_key": self.entry_secret_key.get(),
            "sms_id": self.entry_sms_id.get(),
            "sms_pw": self.entry_sms_pw.get(),
            "sender_phone": self.entry_sender_phone.get(),
            "interval": self.entry_interval.get(),
            "template": self.text_template.get("1.0", tk.END).strip()
        }
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            self.log("설정이 저장되었습니다.")
            messagebox.showinfo("완료", "설정이 저장되었습니다.")
        except Exception as e:
            self.log(f"설정 저장 실패: {e}")
            messagebox.showerror("오류", f"설정 저장 실패: {e}")

    def load_config(self):
        if not os.path.exists(self.config_file):
            return
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            self.entry_vendor_id.insert(0, config.get("vendor_id", ""))
            self.entry_access_key.insert(0, config.get("access_key", ""))
            self.entry_secret_key.insert(0, config.get("secret_key", ""))
            self.entry_sms_id.insert(0, config.get("sms_id", ""))
            self.entry_sms_pw.insert(0, config.get("sms_pw", ""))
            self.entry_sender_phone.insert(0, config.get("sender_phone", ""))
            interval = config.get("interval", "60")
            self.entry_interval.delete(0, tk.END)
            self.entry_interval.insert(0, interval)
            template = config.get("template", "")
            if template:
                self.text_template.delete("1.0", tk.END)
                self.text_template.insert("1.0", template)
            self.log("저장된 설정을 불러왔습니다.")
        except Exception as e:
            self.log(f"설정 불러오기 실패: {e}")

    # --- [기능] 로그 내보내기 ---
    def export_log(self):
        if not self.send_log:
            messagebox.showinfo("알림", "내보낼 발송 기록이 없습니다.")
            return

        default_name = f"발송로그_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV 파일", "*.csv")],
            initialfile=default_name
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=["시간", "주문번호", "고객명", "수신번호", "결과"])
                writer.writeheader()
                writer.writerows(self.send_log)
            self.log(f"발송 로그 내보내기 완료: {file_path} ({len(self.send_log)}건)")
            messagebox.showinfo("완료", f"{len(self.send_log)}건의 기록을 저장했습니다.")
        except Exception as e:
            self.log(f"로그 내보내기 실패: {e}")
            messagebox.showerror("오류", f"내보내기 실패: {e}")

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

        # 2. 쿠팡 API 연결 확인 (실제 호출)
        if self.entry_access_key.get() and self.entry_secret_key.get() and self.entry_vendor_id.get():
            try:
                orders = self.get_coupang_orders()
                self.root.after(0, lambda: self.lbl_coupang_status.configure(
                    text=f"● 쿠팡 API 상태 : 정상 (최근 주문 {len(orders)}건)", foreground="green"))
                self.log("쿠팡 API 연결 확인 완료.")
            except Exception as e:
                self.root.after(0, lambda: self.lbl_coupang_status.configure(
                    text="● 쿠팡 API 상태 : 연결 실패", foreground="red"))
                self.log(f"쿠팡 API 연결 실패: {e}")
        else:
            self.root.after(0, lambda: self.lbl_coupang_status.configure(
                text="● 쿠팡 API 상태 : 키 정보 누락", foreground="red"))
            self.log("쿠팡 API 키가 입력되지 않았습니다.")

        # 3. 마이문자 연결 확인 (잔여 건수 조회)
        if self.entry_sms_id.get() and self.entry_sms_pw.get():
            try:
                url = "https://www.mymessage.co.kr/api/getBalance"
                payload = {
                    "userId": self.entry_sms_id.get(),
                    "userPw": self.entry_sms_pw.get()
                }
                resp = requests.post(url, data=payload, timeout=10)
                result = resp.json()
                if result.get("result") == "success":
                    balance = result.get("balance", "?")
                    self.root.after(0, lambda: self.lbl_sms_status.configure(
                        text=f"● 마이문자 상태 : 정상 (잔여: {balance}건)", foreground="green"))
                    self.log(f"마이문자 연결 확인 완료. 잔여: {balance}건")
                else:
                    raise Exception(result.get("message", "인증 실패"))
            except Exception as e:
                self.root.after(0, lambda: self.lbl_sms_status.configure(
                    text="● 마이문자 상태 : 연결 실패", foreground="red"))
                self.log(f"마이문자 연결 실패: {e}")
        else:
            self.root.after(0, lambda: self.lbl_sms_status.configure(
                text="● 마이문자 상태 : 계정 정보 누락", foreground="red"))
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
            
            try:
                interval = max(10, int(self.entry_interval.get()))
            except ValueError:
                interval = 60
            for _ in range(interval):
                if not self.is_running: break
                time.sleep(1)

    def _coupang_signature(self, method, path, query=""):
        secret_key = self.entry_secret_key.get()
        datetime_now = datetime.now(timezone.utc).strftime('%y%m%dT%H%M%SZ')
        message = datetime_now + method + path + query
        signature = hmac.new(
            secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return (
            f"CEA algorithm=HmacSHA256, "
            f"access-key={self.entry_access_key.get()}, "
            f"signed-date={datetime_now}, "
            f"signature={signature}"
        )

    def get_coupang_orders(self):
        vendor_id = self.entry_vendor_id.get()
        path = f"/v2/providers/openapi/apis/api/v4/vendors/{vendor_id}/ordersheets"

        # 최근 1시간 주문 조회
        now = datetime.now(timezone.utc)
        created_from = (now - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')
        created_to = now.strftime('%Y-%m-%dT%H:%M')

        params = {
            "createdAtFrom": created_from,
            "createdAtTo": created_to,
            "status": "ACCEPT"
        }
        query_string = urlencode(params)
        authorization = self._coupang_signature("GET", path, query_string)

        url = f"https://api-gateway.coupang.com{path}?{query_string}"
        headers = {"Authorization": authorization}

        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            self.log(f"쿠팡 API 오류 (HTTP {response.status_code}): {response.text[:200]}")
            return []

        data = response.json()
        orders = data.get("data", [])
        self.log(f"쿠팡 API 응답: 주문 {len(orders)}건 조회됨.")
        return orders

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

        success = self.send_sms(customer_phone, msg_content)
        status = "성공" if success else "실패"

        self.send_log.append({
            "시간": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "주문번호": order_id,
            "고객명": customer_name,
            "수신번호": customer_phone,
            "결과": status
        })

        if success:
            self.sent_orders.add(order_id)
            self.save_sent_history()
            self.log(f"[발송 성공] {customer_name}님")
        else:
            self.log(f"[발송 실패] {customer_name}님")

    def send_sms(self, phone, message):
        sms_id = self.entry_sms_id.get()
        sms_pw = self.entry_sms_pw.get()
        sender = self.entry_sender_phone.get()

        url = "https://www.mymessage.co.kr/api/sendSMS"
        payload = {
            "userId": sms_id,
            "userPw": sms_pw,
            "sender": sender,
            "receiver": phone,
            "msg": message
        }

        try:
            response = requests.post(url, data=payload, timeout=10)
            result = response.json()
            if result.get("result") == "success":
                return True
            else:
                self.log(f"마이문자 발송 실패: {result.get('message', '알 수 없는 오류')}")
                return False
        except Exception as e:
            self.log(f"마이문자 API 통신 실패: {e}")
            return False

if __name__ == "__main__":
    root = tk.Tk()
    app = CoupangAutoSMSApp(root)
    root.mainloop()