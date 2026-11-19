import time
import database

# RDS에 연결하는 데만 걸리는 시간을 잽니다.
# main.py가 요청마다 이걸 새로 하고 있어서, 여기가 느리면 그게 원인입니다.
for i in range(3):
    t0 = time.perf_counter()
    conn = database.get_connection()
    ms = (time.perf_counter() - t0) * 1000
    conn.close()
    print(f"{i+1}회차 연결: {ms:.0f}ms")
