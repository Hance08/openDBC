import cantools
import csv
import datetime

# 載入 Tesla DBC
db = cantools.database.load_file("Model3CAN.dbc")

# 定義要解析的訊號
signals_of_interest = [
    "SOCave292", "SOCmax292", "SOCmin292", "SOCUI292",  # BMS SOC 相關
    "ChargeLinePower264", "ChargeLineVoltage264", "ChargeLineCurrent264",  # 充電資訊
    "PCS_hvChargeStatus",        # 充電狀態
    "BMS_maxDischargePower", "BMS_maxRegenPower"  # BMS 功率
]

csv_file = "ColdBattCharge.csv"

print("=== 開始解析 CSV 檔案 ===")
print(f"目標訊號: {signals_of_interest}")
print()

# 存儲解析後的數據
parsed_data = []

try:
    with open(csv_file, "r", encoding='utf-8') as f:
        # 跳過檔案頭部的註釋行
        lines = f.readlines()
        
        # 找到真正的 CSV 標頭行
        header_line_index = -1
        for i, line in enumerate(lines):
            if line.startswith('"Message Number"'):
                header_line_index = i
                break
        
        if header_line_index == -1:
            print("找不到 CSV 標頭行")
            exit(1)
        
        # 從標頭行開始讀取 CSV
        csv_data = lines[header_line_index:]
        
        # 使用 csv.reader 解析
        reader = csv.DictReader(csv_data)
        
        print("CSV 欄位:", reader.fieldnames)
        print()
        
        for row_num, row in enumerate(reader):
            try:
                # 提取需要的欄位
                time_ms = float(row.get("Time (ms)", 0))
                can_id_hex = row.get("ID", "").strip()
                data_hex = row.get("Data (Hex)", "").strip()
                
                if not can_id_hex or not data_hex:
                    continue
                
                # 解析 CAN ID (移除 0x 前綴如果有的話)
                if can_id_hex.startswith("0x"):
                    can_id = int(can_id_hex, 16)
                else:
                    can_id = int(can_id_hex, 16)
                
                # 解析資料 (移除空格)
                data_hex_clean = data_hex.replace(" ", "")
                if len(data_hex_clean) % 2 != 0:
                    continue  # 資料長度必須是偶數
                
                data = bytes.fromhex(data_hex_clean)
                
                # 用 DBC 解碼
                try:
                    msg = db.get_message_by_frame_id(can_id)
                    decoded = msg.decode(data)
                    
                    # 篩選我們要的訊號
                    filtered = {sig: decoded.get(sig) for sig in signals_of_interest if sig in decoded}
                    
                    # 只輸出包含我們關心訊號的訊息
                    if filtered:
                        timestamp_sec = time_ms / 1000.0  # 轉換為秒
                        parsed_data.append({
                            'timestamp': timestamp_sec,
                            'can_id': hex(can_id),
                            'message_name': msg.name,
                            'signals': filtered
                        })
                        print(f"{timestamp_sec:.3f}s: {filtered}")
                
                except (KeyError, Exception) as e:
                    # 跳過無法解碼的訊息
                    continue
            
            except (ValueError, Exception) as e:
                print(f"解析第 {row_num} 行時發生錯誤: {e}")
                continue

except FileNotFoundError:
    print(f"找不到檔案: {csv_file}")
except Exception as e:
    print(f"讀取檔案時發生錯誤: {e}")

# 顯示統計資訊
if parsed_data:
    print(f"\n=== 解析統計 ===")
    print(f"成功解析的訊息數量: {len(parsed_data)}")
    
    # 時間範圍
    start_time = parsed_data[0]['timestamp']
    end_time = parsed_data[-1]['timestamp']
    duration = end_time - start_time
    
    print(f"時間範圍: {duration:.1f} 秒 ({duration/60:.1f} 分鐘)")
    print(f"開始時間: {datetime.datetime.fromtimestamp(start_time)}")
    print(f"結束時間: {datetime.datetime.fromtimestamp(end_time)}")
    
    # SOCave292 變化分析
    soc_ave_data = []
    for entry in parsed_data:
        if 'SOCave292' in entry['signals']:
            soc_ave_data.append({
                'timestamp': entry['timestamp'],
                'soc_value': entry['signals']['SOCave292']
            })
    
    if soc_ave_data:
        print(f"\n=== SOCave292 變化分析 ===")
        start_soc = soc_ave_data[0]['soc_value']
        end_soc = soc_ave_data[-1]['soc_value']
        soc_change = end_soc - start_soc
        
        print(f"起始 SOCave292: {start_soc:.2f}%")
        print(f"結束 SOCave292: {end_soc:.2f}%")
        print(f"SOC 變化: {soc_change:+.2f}%")
        
        if duration > 0:
            soc_rate_per_hour = soc_change / (duration / 3600)
            print(f"變化率: {soc_rate_per_hour:+.3f}% per hour")
        
        print(f"SOCave292 資料點數量: {len(soc_ave_data)}")
    
    # 訊號統計
    signal_counts = {}
    for entry in parsed_data:
        for signal_name in entry['signals'].keys():
            signal_counts[signal_name] = signal_counts.get(signal_name, 0) + 1
    
    print(f"\n=== 訊號統計 ===")
    for signal_name, count in signal_counts.items():
        print(f"{signal_name}: {count} 個資料點")

else:
    print("沒有找到相符的訊號資料")