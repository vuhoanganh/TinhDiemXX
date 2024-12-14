from flask import Flask, render_template, request, redirect, url_for # type: ignore

app = Flask(__name__)

# Danh sách người chơi
players = ["Alvin", "Ryan", "May", "Cece"]

# Biến toàn cục
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
history = []  # Lịch sử các ván đấu
player_total_points = {p: 0 for p in players}  # Tổng điểm qua các ván
conversion_rate = 1000  # Tỷ lệ quy đổi điểm -> tiền

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

@app.route("/", methods=["GET", "POST"])
def index():
    global scores, sap_ham_results, history, player_total_points, conversion_rate

    if request.method == "POST":
        if "update_conversion_rate" in request.form:
            # Cập nhật tỷ lệ quy đổi tiền
            conversion_rate = int(request.form["conversion_rate"])
            return redirect(url_for("index"))

        if "clear_history" in request.form:
            # Nếu nhấn nút Clear, xóa toàn bộ lịch sử và reset điểm
            history.clear()
            player_total_points = {p: 0 for p in players}
            # Reset kết quả hiển thị
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
            return redirect(url_for("index"))

        if "delete_round" in request.form:
            # Nếu nhấn nút Xóa, xóa một ván đấu khỏi lịch sử
            round_to_delete = int(request.form["delete_round"])
            round_data = history.pop(round_to_delete - 1)

            # Cập nhật lại tổng điểm của người chơi
            for p in players:
                player_total_points[p] -= round_data[p]

            # Cập nhật số thứ tự ván đấu
            for i, round_entry in enumerate(history):
                round_entry["round"] = i + 1

            return redirect(url_for("index"))

        if "edit_round" in request.form:
            # Nếu nhấn nút Sửa, cập nhật điểm của ván đấu
            round_to_edit = int(request.form["edit_round"])
            new_scores = {
                "Alvin": int(request.form["edit_Alvin"]),
                "Ryan": int(request.form["edit_Ryan"]),
                "May": int(request.form["edit_May"]),
                "Cece": int(request.form["edit_Cece"]),
            }

            # Cập nhật lại tổng điểm
            old_scores = history[round_to_edit - 1]
            for p in players:
                player_total_points[p] += new_scores[p] - old_scores[p]

            # Cập nhật lịch sử
            history[round_to_edit - 1].update(new_scores)

            return redirect(url_for("index"))

        # Xử lý tính điểm thông thường
        mau_binh_choices = {p: request.form.get(f"mau_binh_{p}", "none") for p in players}
        for p in players:
            scores[p]["mau_binh"] = mau_binh_choices[p]

        # Kiểm tra có người Mậu Binh không
        mau_binh_players = [p for p in players if scores[p]["mau_binh"] != "none"]

        # Nếu có Mậu Binh thì không tính chi và sập hầm, chỉ tính Mậu Binh
        has_mau_binh = len(mau_binh_players) > 0

        if has_mau_binh:
            # Reset điểm chi, sap_ham
            for p in players:
                scores[p]["chi_dau"] = 0
                scores[p]["chi_giua"] = 0
                scores[p]["chi_cuoi"] = 0
                scores[p]["sap_ham"] = 0
                scores[p]["tong"] = 0
            apply_mau_binh_difference()
        else:
            # Lấy thứ tự thắng từ form
            chi_dau = request.form.get("chi_dau", "").strip().lower()
            chi_giua = request.form.get("chi_giua", "").strip().lower()
            chi_cuoi = request.form.get("chi_cuoi", "").strip().lower()

            calculate_points(chi_dau, "chi_dau")
            calculate_points(chi_giua, "chi_giua")
            calculate_points(chi_cuoi, "chi_cuoi")

            # Tính tổng điểm trước khi xử lý sập hầm
            for player in players:
                scores[player]["tong"] = (
                    scores[player]["chi_dau"]
                    + scores[player]["chi_giua"]
                    + scores[player]["chi_cuoi"]
                )

            # Xử lý sập hầm
            check_sap_ham()

            # Cộng điểm sập hầm vào tổng
            for player in players:
                scores[player]["tong"] += scores[player]["sap_ham"]

        # Lưu kết quả vào lịch sử
        history.append({
            "round": len(history) + 1,
            **{p: scores[p]["tong"] for p in players}
        })

        # Cập nhật tổng điểm qua các ván
        for p in players:
            player_total_points[p] += scores[p]["tong"]

        return redirect(url_for("index"))

    # GET request: Không reset scores, sap_ham_results ở đây
    has_mau_binh = any(scores[player]["mau_binh"] != "none" for player in players)
    return render_template(
        "index.html",
        scores=scores,
        players=players,
        sap_ham_results=sap_ham_results,
        has_mau_binh=has_mau_binh,
        history=history,
        player_total_points=player_total_points,
        conversion_rate=conversion_rate,
    )

def calculate_points(order, chi):
    """Tính điểm cho từng chi"""
    point_map = {0: 3, 1: 1, 2: -1, 3: -3}
    if len(order) == 4:
        for i, player_code in enumerate(order):
            if player_code == "a":
                player = "Alvin"
            elif player_code == "r":
                player = "Ryan"
            elif player_code == "m":
                player = "May"
            elif player_code == "c":
                player = "Cece"
            else:
                continue
            scores[player][chi] = point_map[i]

def check_sap_ham():
    """Xử lý sập hầm"""
    global sap_ham_results
    sap_ham_results.clear()  # Xóa kết quả sập hầm cũ
    non_mau_binh_players = [p for p in players if scores[p]["mau_binh"] == "none"]

    for loser in non_mau_binh_players:
        for winner in non_mau_binh_players:
            if winner != loser:
                # Kiểm tra nếu winner thắng loser ở tất cả 3 chi
                if (scores[winner]["chi_dau"] > scores[loser]["chi_dau"] and
                    scores[winner]["chi_giua"] > scores[loser]["chi_giua"] and
                    scores[winner]["chi_cuoi"] > scores[loser]["chi_cuoi"]):
                    # Cập nhật điểm sập hầm
                    scores[loser]["sap_ham"] -= 3
                    scores[winner]["sap_ham"] += 3
                    sap_ham_results.append(f"{loser} đã bị Sập Hầm bởi {winner}")

def apply_mau_binh_difference():
    """Tính điểm khi có Mậu Binh, chỉ tính chênh lệch MB và MB - NonMB"""
    mb_values = {p: mau_binh_points[scores[p]["mau_binh"]] for p in players}

    for p1 in players:
        for p2 in players:
            if p1 != p2:
                if mb_values[p1] > 0 and mb_values[p2] == 0:
                    scores[p1]["tong"] += mb_values[p1]
                    scores[p2]["tong"] -= mb_values[p1]
                elif mb_values[p1] == 0 and mb_values[p2] > 0:
                    scores[p2]["tong"] += mb_values[p2]
                    scores[p1]["tong"] -= mb_values[p2]
                elif mb_values[p1] > 0 and mb_values[p2] > 0:
                    diff = mb_values[p1] - mb_values[p2]
                    if diff > 0:
                        scores[p1]["tong"] += diff
                        scores[p2]["tong"] -= diff
                    elif diff < 0:
                        diff = abs(diff)
                        scores[p2]["tong"] += diff
                        scores[p1]["tong"] -= diff
                    # diff = 0 => không thay đổi

if __name__ == "__main__":
    app.run(debug=True)
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Lấy PORT từ môi trường hoặc dùng 5000
    app.run(host="0.0.0.0", port=port)
