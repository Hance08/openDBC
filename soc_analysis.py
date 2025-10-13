import cantools
import datetime

# 載入 Tesla DBC
db = cantools.database.load_file("Model3CAN.dbc")

# SOC 相關訊號
soc_signals = ["SOCave292", "SOCmax292", "SOCmin292", "SOCUI292"]

log_file = "simulated_can(1).log"

# 存儲所有 SOC 數據用於分析
soc_data = []
timestamps = []

print("=== SOC 數據分析 ===\n")

with open(log_file, "r") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        try:
            timestamp_part, iface, msg_part = line.split()
            timestamp = float(timestamp_part.strip("()"))
            
            arb_str, data_str = msg_part.split("#")
            arbitration_id = int(arb_str, 16)
            data = bytes.fromhex(data_str)
            
        except ValueError:
            continue

        try:
            msg = db.get_message_by_frame_id(arbitration_id)
            decoded = msg.decode(data)
        except (KeyError, Exception):
            continue

        # 只處理包含 SOC 訊號的訊息
        soc_found = {sig: decoded.get(sig) for sig in soc_signals if sig in decoded}
        
        if soc_found:
            timestamps.append(timestamp)
            soc_data.append(soc_found)
            print(f"{timestamp}: {soc_found}")

# 分析結果
if soc_data:
    print(f"\n=== 分析結果 ===")
    
    # 時間範圍
    start_time = timestamps[0]
    end_time = timestamps[-1]
    duration = end_time - start_time
    
    print(f"時間範圍: {duration:.1f} 秒 ({duration/60:.1f} 分鐘)")
    print(f"開始時間: {datetime.datetime.fromtimestamp(start_time)}")
    print(f"結束時間: {datetime.datetime.fromtimestamp(end_time)}")
    print(f"數據點數量: {len(soc_data)}")
    
    # SOC 變化分析
    first_data = soc_data[0]
    last_data = soc_data[-1]
    
    print(f"\n=== SOC 變化 ===")
    for signal in soc_signals:
        if signal in first_data and signal in last_data:
            start_val = first_data[signal]
            end_val = last_data[signal]
            change = end_val - start_val
            print(f"{signal}:")
            print(f"  開始: {start_val:.1f}%")
            print(f"  結束: {end_val:.1f}%")
            print(f"  變化: {change:+.1f}%")
            if duration > 0:
                rate_per_hour = change / (duration / 3600)
                print(f"  變化率: {rate_per_hour:+.3f}% per hour")
    
    # 檢查數據合理性
    print(f"\n=== 數據合理性檢查 ===")
    for i, data in enumerate(soc_data):
        timestamp = timestamps[i]
        if 'SOCave292' in data and 'SOCmax292' in data and 'SOCmin292' in data:
            soc_ave = data['SOCave292']
            soc_max = data['SOCmax292'] 
            soc_min = data['SOCmin292']
            
            # 檢查邏輯錯誤
            if soc_max < soc_ave or soc_ave < soc_min:
                print(f"⚠️  異常數據 @ {timestamp}:")
                print(f"   SOCmax({soc_max:.1f}) < SOCave({soc_ave:.1f}) < SOCmin({soc_min:.1f})")
                print(f"   這違反了 max ≥ ave ≥ min 的邏輯")
else:
    print("未找到 SOC 數據")