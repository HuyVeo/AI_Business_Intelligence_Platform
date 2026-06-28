import logging
from pathlib import Path
import polars as pl

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

RAW_DATA = Path("D:\\Project\\AI_Data_Intelligence_Platform\\data\\raw\\2019-Oct.csv")
OUTPUT_DIR = Path("D:\\Project\\AI_Data_Intelligence_Platform\\data\\sample")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def generate_deterministic_samples():
    if not RAW_DATA.exists():
        logger.error(f"Không tìm thấy file dữ liệu gốc tại: {RAW_DATA}")
        return

    logger.info("Đang quét cấu trúc file dữ liệu lớn (Lazy Mode)...")
    # Sử dụng Scan CSV để không nạp file 5.6GB vào RAM
    lazy_df = pl.scan_csv(RAW_DATA, low_memory=True)
    
    # Sử dụng hàm băm (Hash) trên user_id để chọn ra một nhóm user cố định (Giữ toàn vẹn Session)
    # Lấy ngẫu nhiên khoảng 5% lượng user làm Pool trung gian
    sampled_pool = lazy_df.filter((pl.col("user_id").hash() % 100).abs() < 5)

    sizes = [1000, 10000, 100000]
    for size in sizes:
        sample_path = OUTPUT_DIR / f"sample_{size}.csv"
        logger.info(f"Đang trích xuất và tối ưu tập mẫu {size} dòng...")
        
        # Thực thi đồ thị tính toán và ép chạy bằng chế độ Streaming an toàn cho RAM
        df_sample = sampled_pool.limit(size).collect(streaming=True)
        
        # Sắp xếp tuyến tính theo chuỗi thời gian của sự kiện
        df_sample = df_sample.sort("event_time")
        
        df_sample.write_csv(sample_path)
        logger.info(f"Đã tạo thành công: {sample_path}")

if __name__ == "__main__":
    generate_deterministic_samples()