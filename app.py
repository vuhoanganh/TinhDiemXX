
import sqlite3
from datetime import datetime
import os

from flask import Flask, render_template, request, redirect, url_for # type: ignore

app = Flask(__name__)
import tempfile

DATABASE = os.path.join(tempfile.gettempdir(), "database.db")

# # Đường dẫn file database SQLite
# DATABASE = os.path.join(os.getcwd(), "database.db")

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


# Tạo bảng nếu chưa tồn tại
def create_table():
    with sqlite3.connect(DATABASE) as conn:
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
        print("Database created successfully!")  # Xác nhận bảng được khởi tạo
        conn.commit()
""" if __name__ == "__main__":
    create_table()  # Đảm bảo database được khởi tạo
    app.run(debug=True) """

# Hàm lưu dữ liệu vào database
def save_game_to_db(round_number, scores, description):
    # Giải nén điểm số từng người chơi từ scores dictionary
    player1_score = scores.get(players[0], {}).get("tong", 0)
    player2_score = scores.get(players[1], {}).get("tong", 0)
    player3_score = scores.get(players[2], {}).get("tong", 0) if len(players) > 2 else None
    player4_score = scores.get(players[3], {}).get("tong", 0) if len(players) > 3 else None

    # Lưu vào SQLite
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO game_history (round, player1, player2, player3, player4, played_at, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            round_number,         # round
            player1_score,        # player1
            player2_score,        # player2
            player3_score,        # player3 (None nếu không có)
            player4_score,        # player4 (None nếu không có)
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # played_at
            description           # description
        ))

        conn.commit()


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


@app.route("/", methods=["GET", "POST"])
def index():
    global scores, sap_ham_results, history, player_total_points, conversion_rate, currency, players
    global last_chi_dau, last_chi_giua, last_chi_cuoi

    default_conversion_rate = 0.25
    default_currency = "USD"

    # Tải lịch sử từ SQLite khi trang được tải
    history.clear()
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM game_history ORDER BY round ASC")
        rows = cursor.fetchall()
        for row in rows:
            round_entry = {}
            try:
                round_entry["round"] = row[0]
                round_entry[players[0]] = row[1] if len(players) > 0 else 0
                round_entry[players[1]] = row[2] if len(players) > 1 else 0
                round_entry[players[2]] = row[3] if len(players) > 2 else 0
                round_entry[players[3]] = row[4] if len(players) > 3 else 0
                round_entry["played_at"] = row[5] if row[5] else "N/A"
                round_entry["description"] = row[6] if row[6] else "Không"
                history.append(round_entry)
            except IndexError as e:
                print(f"Error processing row: {row}, Error: {e}")

    if request.method == "POST":
        if "update_settings" in request.form:
            num_players = int(request.form.get("num_players", len(players)))
            num_players = max(min_players, min(max_players, num_players))
            players = [request.form.get(f"player_name_{i+1}", f"Player{i+1}").strip() or f"Player{i+1}" for i in range(num_players)]
            history.clear()
            reset_game_state()
            last_chi_dau = last_chi_giua = last_chi_cuoi = ""
            return redirect(url_for("index"))

        if "update_conversion_rate" in request.form:
            conversion_rate = float(request.form.get("conversion_rate", default_conversion_rate))
            currency = request.form.get("currency", default_currency)
            return redirect(url_for("index"))

        if "clear_history" in request.form:
            history.clear()
            reset_game_state()
            with sqlite3.connect(DATABASE) as conn:
                conn.execute("DELETE FROM game_history")
            return redirect(url_for("index"))

        if "delete_round" in request.form:
            round_to_delete = int(request.form["delete_round"])
            with sqlite3.connect(DATABASE) as conn:
                conn.execute("DELETE FROM game_history WHERE round = ?", (round_to_delete,))
            history[:] = [r for r in history if r["round"] != round_to_delete]
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
            "player1": scores[players[0]]["tong"],
            "player2": scores[players[1]]["tong"],
            "player3": scores[players[2]]["tong"] if len(players) > 2 else None,
            "player4": scores[players[3]]["tong"] if len(players) > 3 else None,
            "played_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "description": " - ".join([
            f"{p}: {scores[p]['mau_binh'].replace('_', ' ') if scores[p]['mau_binh'] != 'none' else ''}"
            for p in players if scores[p].get('mau_binh', 'none') != 'none'
            ]).strip()

        }
        # round_data = {
        #     "round": len(history) + 1,
        #     "player1": scores[players[0]]["tong"] if len(players) > 0 else 0,
        #     "player2": scores[players[1]]["tong"] if len(players) > 1 else 0,
        #     "player3": scores[players[2]]["tong"] if len(players) > 2 else 0,
        #     "player4": scores[players[3]]["tong"] if len(players) > 3 else 0,
        #     "played_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        #     "description": ""
        # }

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
                entry["player1"] = entry["player2"] = entry["player3"] = entry["player4"] = 0


                # Thêm thông tin Mậu Binh vào round_data
                if "round_data" in locals():
                    for p in players:
                        if scores[p]["mau_binh"] != "none":
                            round_data[f"{p}_mau_binh"] = scores[p]["mau_binh"]


        # Thêm vào history
        history.append(round_data)

        # Lưu vào database
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO game_history (round, player1, player2, player3, player4, played_at, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                round_data["round"],
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

    return render_template(
        "index.html",
        scores=scores,
        players=players,
        sap_ham_results=sap_ham_results,
        history=history,
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


create_table()
if __name__ == "__main__":
    app.run(debug=True)