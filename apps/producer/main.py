import json
import time
import pandas as pd
import pyarrow.parquet as pq
from confluent_kafka import Producer
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_PATH = BASE_DIR / "data/processed/events"

producer = Producer({
    'bootstrap.servers': 'localhost:9092',
    'client.id': 'ecommerce-producer',
    'acks': '1', # Tối ưu tốc độ gửi cho tập dữ liệu quá lớn
    'linger.ms': 50, 
    'batch.size': 65536
})

def run():
    print(f"Đang quét dữ liệu từ: {DATA_PATH}")

    if not DATA_PATH.exists():
        print("Lỗi: Không tìm thấy thư mục data.")
        return

    parquet_files = list(DATA_PATH.rglob("*.parquet"))
    parquet_files.sort() 

    if not parquet_files:
        print("Không có file parquet nào để đọc.")
        return

    total_files = len(parquet_files)
    print(f"Tìm thấy {total_files} file phân vùng.")

    for i, file_path in enumerate(parquet_files, 1):
        print(f"\nBắt đầu xử lý file {i}/{total_files}: {file_path.name}")
        
        # 1. Dùng PyArrow mở file (Chưa load vào RAM)
        parquet_file = pq.ParquetFile(file_path)
        
        # 2. Xúc từng gầu nhỏ (Batch) - 10,000 dòng mỗi lần
        batch_size = 10000 
        
        for batch_idx, batch in enumerate(parquet_file.iter_batches(batch_size=batch_size)):
            # Chỉ chuyển 10k dòng này thành Pandas DataFrame
            df_batch = batch.to_pandas()
            
            if "event_time" in df_batch.columns:
                df_batch = df_batch.sort_values(by="event_time")
                
            # Chuyển thành Dictionary (Nhanh hơn iterrows() 100 lần)
            records = df_batch.to_dict(orient="records")
            
            print(f"   -> Bơm batch {batch_idx + 1} ({len(records)} sự kiện)...")
            
            for row in records:
                payload = {
                    "event_id": str(row.get("event_id", "")),
                    "event_time": str(row.get("event_time", "")),
                    "user_id": int(row.get("user_id", 0)) if pd.notna(row.get("user_id")) else 0,
                    "event_type": str(row.get("event_type", "")),
                    "product_id": int(row.get("product_id", 0)) if pd.notna(row.get("product_id")) else 0,
                    "price": float(row.get("price", 0.0)) if pd.notna(row.get("price")) else 0.0,
                    "features": {
                        "hour": int(row.get("hour", -1)) if pd.notna(row.get("hour")) else -1,
                        "weekday": str(row.get("weekday", "Unknown"))
                    }
                }
                
                producer.produce(
                    topic="ecommerce_events",
                    key=str(row.get("user_id", "unknown")),
                    value=json.dumps(payload)
                )
                
                # Gọi poll liên tục để Kafka giải phóng bộ nhớ đệm
                producer.poll(0)
            
            # Xong 1 batch (10,000 dòng), ép gửi đi ngay
            producer.flush()

        print(f"Đã stream xong toàn bộ dữ liệu của file {i}.")

    print("\n Hoàn thành stream toàn bộ hệ thống!")

if __name__ == "__main__":
    run()