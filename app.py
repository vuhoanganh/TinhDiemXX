
import sqlite3
from datetime import datetime
import os
from sqlitecloud import connect # type: ignore
from flask import Flask, render_template, request, redirect, url_for # type: ignore
import ssl
app = Flask(__name__)
import tempfile


# kết nối db
DATABASE_URI = "sqlitecloud://ced9kbtsnk.sqlite.cloud:8860/chinook.sqlite?apikey=KlqfrCYVzONDCDjq3I2alMoqd5WNCd82AyEzAjKs1yY"

# Kiểm tra kết nốiex
try:
    conn = connect(DATABASE_URI)
    conn.execute("USE DATABASE chinook.sqlite;")  # Thay your_database_name bằng tên cơ sở dữ liệu của bạn
    print("Kết nối thành công!")
    conn.close()
except Exception as e:
    print(f"Lỗi kết nối: {e}")


# Hàm kết nối đến SQLite Cloud
def get_connection():
  try:  
    conn= connect(DATABASE_URI)
    conn.execute("USE DATABASE chinook.sqlite;")
    return conn
  except Exception as e:
        print(f"Lỗi khi kết nối: {e}")
        return None

# Cấu hình mặc định
default_players = ["Alvin", "Ryan", "May", "Cece"]
players = default_players[:]
max_players = 4
min_players = 2
if not players or len(players) < min_players:
    players = default_players[:min_players]
elif len(players) > max_players:
    players = players[:max_players]


scores = {}
sap_ham_results = []
history = []
player_total_points = {}
conversion_rate = 0.25
currency = "USD"

mau_binh_points = {
    "none": 0,
    "rong_dong_hoa": 24,
    "sanh_rong": 12,
    "3_thung_pha_sanh": 12,
    "dong_chat_12_la": 6,
    "6_doi": 6,
    "5_doi_1_xam_chi": 2,
    "3_xam_chi": 2
}

last_chi_dau = ""
last_chi_giua = ""
last_chi_cuoi = ""


def create_table():
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS game_history (
                    round INTEGER PRIMARY KEY AUTOINCREMENT,
                    player1 INTEGER,
                    player2 INTEGER,
                    player3 INTEGER,
                    player4 INTEGER,
                    played_at TEXT,
                    description TEXT
                )
            ''')
            print("Database created successfully!")
        except Exception as e:
            print(f"Lỗi khi tạo bảng: {e}")
        finally:
            conn.close()  # Đóng kết nối sau khi hoàn thành
    else:
        print("Không thể kết nối tới cơ sở dữ liệu.")


# Hàm lưu dữ liệu vào database
def save_game_to_db(round_number, scores, description):
    player_scores = [
        scores.get(players[i], {}).get("tong", 0) if i < len(players) else None
        for i in range(4)
    ]
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO game_history (round, player1, player2, player3, player4, played_at, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            round_number,
            player_scores[0],
            player_scores[1],
            player_scores[2],
            player_scores[3],
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            description
        ))


# Hàm reset game
def reset_game_state():
    global scores, sap_ham_results, player_total_points
    scores = {
        p: {
            "chi_dau": 0,
            "chi_giua": 0,
            "chi_cuoi": 0,
            "sap_ham": 0,
            "mau_binh": "none",
            "tong": 0
        } for p in players
    }
    sap_ham_results = []
    player_total_points = {p: 0 for p in players}



reset_game_state()

def fetch_data_from_game_history():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM game_history")
            rows = cursor.fetchall()
            for row in rows:
                print(row)  # Hoặc xử lý dữ liệu theo ý bạn
    except Exception as e:
        print(f"Lỗi khi truy vấn dữ liệu: {e}")

# Gọi hàm fetch_data_from_game_history() để kiểm tra
fetch_data_from_game_history()

# Lấy lịch sử ván đấu
def fetch_game_history():
    with get_connection() as conn:
        result = conn.execute("SELECT * FROM game_history ORDER BY round ASC").fetchall()
        return result
    

@app.route("/", methods=["GET", "POST"])
def index():
    global scores, sap_ham_results, history, player_total_points, conversion_rate, currency, players
    global last_chi_dau, last_chi_giua, last_chi_cuoi
    global history, players
    
    default_conversion_rate = 0.25
    default_currency = "USD"

     # Lấy dữ liệu lịch sử
    history.clear()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM game_history ORDER BY round ASC")
        rows = cursor.fetchall()
        for row in rows:
            if isinstance(row, tuple):
                entry = {
                    "round": row[0],
                    "player1": row[1],
                    "player2": row[2],
                    "player3": row[3],
                    "player4": row[4],
                    "played_at": row[5],
                    "description": row[6],
                }
                history.append(entry)
            else:
                print(f"Lỗi: Dữ liệu không phải là tuple. row={row}, loại: {type(row)}")

    if request.method == "POST":
        print(f"Dữ liệu nhận được từ form: {request.form}")


    if request.method == "POST":
        if "update_settings" in request.form:
            num_players = int(request.form.get("num_players", len(players)))
            num_players = max(min_players, min(max_players, num_players))
            players = [request.form.get(f"player_name_{i+1}", f"Player{i+1}").strip() or f"Player{i+1}" for i in range(num_players)]

            # history.clear()
            reset_game_state()
             # Cắt giảm các giá trị không cần thiết nếu số người chơi giảm
            for entry in history:
                for i in range(num_players, max_players):
                    entry[f"player{i+1}"] = None

            # Xóa các người chơi dư thừa trong `scores` nếu số lượng giảm
            for p in list(scores.keys()):
                if p not in players:
                    del scores[p]        
            last_chi_dau = last_chi_giua = last_chi_cuoi = ""
            return redirect(url_for("index"))

        if "update_conversion_rate" in request.form:
            conversion_rate = float(request.form.get("conversion_rate", default_conversion_rate))
            currency = request.form.get("currency", default_currency)
            return redirect(url_for("index"))

        if "clear_history" in request.form:
            history.clear()
            reset_game_state()
            with get_connection() as conn:
                conn.execute("DELETE FROM game_history")  # Xóa toàn bộ dữ liệu
            return redirect(url_for("index"))


        if "delete_round" in request.form:
            round_to_delete = request.form.get("delete_round", "").strip()
            
            if not round_to_delete:
                print("Lỗi: Giá trị round_to_delete không được gửi.")
            elif round_to_delete.isdigit():
                round_to_delete = int(round_to_delete)
                with get_connection() as conn:
                    conn.execute("DELETE FROM game_history WHERE round = ?", (round_to_delete,))
                history[:] = [r for r in history if r["round"] != round_to_delete]
                print(f"Xoá thành công round: {round_to_delete}")
            else:
                print(f"Lỗi: Giá trị round_to_delete không hợp lệ: {round_to_delete}")
            
            return redirect(url_for("index"))


        
        # Sửa ván đấu
        if "edit_round" in request.form:
            edit_round = int(request.form["edit_round"])
            edited_scores = {}

            # Lấy điểm số mới từ form
            for player in players:
                edited_scores[player] = int(request.form.get(f"edit_{player}", 0))

            # Cập nhật vào database
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE game_history
                    SET player1 = ?, player2 = ?, player3 = ?, player4 = ?
                    WHERE round = ?
                """, (
                    edited_scores.get(players[0], 0),
                    edited_scores.get(players[1], 0),
                    edited_scores.get(players[2], 0),
                    edited_scores.get(players[3], 0),
                    edit_round
                ))
                conn.commit()
            return redirect(url_for("index"))

        # Tính điểm mới
        chi_dau = request.form.get("chi_dau", "").strip().lower()
        chi_giua = request.form.get("chi_giua", "").strip().lower()
        chi_cuoi = request.form.get("chi_cuoi", "").strip().lower()

        last_chi_dau, last_chi_giua, last_chi_cuoi = chi_dau, chi_giua, chi_cuoi

        # Chọn Mậu Binh
        mau_binh_choices = {p: request.form.get(f"mau_binh_{p}", "none") for p in players}
        for p in players:
            scores[p]["mau_binh"] = mau_binh_choices[p]

        mb_players = [p for p in players if scores[p]["mau_binh"] != "none"]
        has_mau_binh = len(mb_players) > 0

        # Reset điểm
        for p in players:
            scores[p]["chi_dau"] = scores[p]["chi_giua"] = scores[p]["chi_cuoi"] = scores[p]["sap_ham"] = scores[p]["tong"] = 0

        if has_mau_binh:
            apply_mau_binh_scoring(mb_players)
        else:
            calculate_points(chi_dau, "chi_dau")
            calculate_points(chi_giua, "chi_giua")
            calculate_points(chi_cuoi, "chi_cuoi")
            check_sap_ham()
            for player in players:
                scores[player]["tong"] = scores[player]["chi_dau"] + scores[player]["chi_giua"] + scores[player]["chi_cuoi"] + scores[player]["sap_ham"]

        # Lưu dữ liệu vào database
        mau_binh_description = " | ".join([f"{p}: {scores[p]['mau_binh']}" for p in players if scores[p]['mau_binh'] != "none"])
        description = f"{last_chi_dau}-{last_chi_giua}-{last_chi_cuoi}"
        if mau_binh_description:
            description += f"{mau_binh_description}"   
        round_data = {
            "round": len(history) + 1,
            "player1": scores[players[0]]["tong"] if len(players) > 0 else None,
            "player2": scores[players[1]]["tong"] if len(players) > 1 else None,
            "player3": scores[players[2]]["tong"] if len(players) > 2 else None,
            "player4": scores[players[3]]["tong"] if len(players) > 3 else None,
            "played_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "description": " | ".join([
                f"{p}: {scores[p]['mau_binh'].replace('_', ' ') if scores[p]['mau_binh'] != 'none' else ''}"
                for p in players if scores[p]["mau_binh"] != "none"
            ])
        }
        
        # Thêm thông tin Mậu Binh vào description
        mau_binh_description = " | ".join([
            f"{p}: {scores[p]['mau_binh'].replace('_', ' ') if scores[p]['mau_binh'] != 'none' else ''}"
            for p in players if scores[p]['mau_binh'] != 'none'
        ])
        if mau_binh_description:
            round_data["description"] = mau_binh_description

        # Xử lý lịch sử ván đấu
        for entry in history:
            if "player1" not in entry or "player2" not in entry:
                if isinstance(entry, dict):
                    entry["player1"] = 0
                    entry["player2"] = 0
                    entry["player3"] = 0
                    entry["player4"] = 0
                else:
                    print(f"Lỗi: entry không phải là dict. entry={entry}, loại: {type(entry)}")

                # Thêm thông tin Mậu Binh vào round_data
                if "round_data" in locals():
                    for p in players:
                        if scores[p]["mau_binh"] != "none":
                            round_data[f"{p}_mau_binh"] = scores[p]["mau_binh"]


        # Thêm vào history
        history.append(round_data)

        # Lưu vào SQLite
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO game_history (player1, player2, player3, player4, played_at, description)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                round_data["player1"],
                round_data["player2"],
                round_data["player3"],
                round_data["player4"],
                round_data["played_at"],
                round_data["description"]
            ))

            conn.commit()

        # Cập nhật tổng điểm
        for p in players:
            player_total_points[p] += scores[p]["tong"]

        # Reset Mậu Binh
        for p in players:
            scores[p]["mau_binh"] = "none"

        return redirect(url_for("index"))

    print("Dữ liệu lịch sử: ", history)

    return render_template(
    "index.html",
    scores=scores,
    players=players,
    sap_ham_results=sap_ham_results,
    history=history,  # Đảm bảo history được truyền đúng
    player_total_points=player_total_points,
    conversion_rate=conversion_rate,
    currency=currency,
    last_chi_dau=last_chi_dau,
    last_chi_giua=last_chi_giua,
    last_chi_cuoi=last_chi_cuoi,
    max_players=max_players,
    min_players=min_players
)



def calculate_points(order, chi):
    first_letters_map = {p[0].lower(): p for p in players}
    ranked_players = [first_letters_map.get(code, None) for code in order if code in first_letters_map]
    if len(ranked_players) != len(players):
        return
    point_map = {0: 3, 1: 1, 2: -1, 3: -3}
    for i, p in enumerate(ranked_players):
        scores[p][chi] = point_map[i]


def check_sap_ham():
    global sap_ham_results
    sap_ham_results.clear()
    for loser in players:
        for winner in players:
            if winner != loser and all(scores[winner][chi] > scores[loser][chi] for chi in ["chi_dau", "chi_giua", "chi_cuoi"]):
                scores[loser]["sap_ham"] -= 3
                scores[winner]["sap_ham"] += 3
                sap_ham_results.append(f"{loser} bị Sập Hầm bởi {winner}")


def apply_mau_binh_scoring(mb_players):
    """
    Hàm tính điểm cho người chơi có Mậu Binh:
    - Người có Mậu Binh nhận điểm tương ứng từ những người không có Mậu Binh.
    - Nếu nhiều người có Mậu Binh, so sánh chênh lệch điểm.
    """
    mb_values = {p: mau_binh_points[scores[p]["mau_binh"]] for p in mb_players}
    non_mb_players = [p for p in players if p not in mb_players]

    if len(mb_players) == 1:
        # Một người có Mậu Binh, ăn điểm từ tất cả người khác
        mb_player = mb_players[0]
        for other in non_mb_players:
            scores[mb_player]["tong"] += mb_values[mb_player]
            scores[other]["tong"] -= mb_values[mb_player]
    else:
        # Nhiều người có Mậu Binh, tính chênh lệch
        for p1 in mb_players:
            for p2 in mb_players:
                if p1 != p2:
                    diff = mb_values[p1] - mb_values[p2]
                    if diff > 0:
                        scores[p1]["tong"] += diff
                        scores[p2]["tong"] -= diff

        # Người không có Mậu Binh trả cho từng người có Mậu Binh
        for p in non_mb_players:
            for mb_player in mb_players:
                scores[mb_player]["tong"] += mb_values[mb_player]
                scores[p]["tong"] -= mb_values[mb_player]


if __name__ == "__main__":
    create_table()  # Đảm bảo bảng được khởi tạo
    app.run(debug=True)
