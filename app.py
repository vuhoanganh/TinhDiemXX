from flask import Flask, render_template, request, redirect, url_for # type: ignore

app = Flask(__name__)

default_players = ["Alvin", "Ryan", "May", "Cece"]
players = default_players[:]  # Người chơi hiện tại
max_players = 4
min_players = 2

scores = {}
sap_ham_results = []
history = []
player_total_points = {}
conversion_rate = 1000.0
currency = "VND"

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

# Lưu giá trị chi cuối cùng nhập vào
last_chi_dau = ""
last_chi_giua = ""
last_chi_cuoi = ""

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

    # Giá trị mặc định cho "Tỷ lệ quy đổi" và "Đơn vị tiền tệ"
    default_conversion_rate = 0.25
    default_currency = "USD"

    if request.method == "POST":
        if "update_settings" in request.form:
            num_players = int(request.form.get("num_players", len(players)))
            if num_players < min_players:
                num_players = min_players
            if num_players > max_players:
                num_players = max_players

            new_players = []
            for i in range(num_players):
                player_name = request.form.get(f"player_name_{i+1}", f"Player{i+1}").strip()
                new_players.append(player_name if player_name else f"Player{i+1}")

            players = new_players
            history.clear()
            reset_game_state()

            # Reset chi
            last_chi_dau = ""
            last_chi_giua = ""
            last_chi_cuoi = ""

            return redirect(url_for("index"))

        if "update_conversion_rate" in request.form:
            conversion_rate = float(request.form.get("conversion_rate", default_conversion_rate))
            currency = request.form.get("currency", default_currency)
            return redirect(url_for("index"))

        if "clear_history" in request.form:
            history.clear()
            reset_game_state()
            # Reset chi
            last_chi_dau = ""
            last_chi_giua = ""
            last_chi_cuoi = ""
            return redirect(url_for("index"))

        if "delete_round" in request.form:
            round_to_delete = int(request.form["delete_round"])
            round_data = history.pop(round_to_delete - 1)

            for p in players:
                player_total_points[p] -= round_data[p]

            for i, round_entry in enumerate(history):
                round_entry["round"] = i + 1

            return redirect(url_for("index"))

        if "edit_round" in request.form:
            round_to_edit = int(request.form["edit_round"])
            new_scores = {}
            for p in players:
                new_scores[p] = int(request.form[f"edit_{p}"])

            old_scores = history[round_to_edit - 1]
            for p in players:
                player_total_points[p] += new_scores[p] - old_scores[p]

            history[round_to_edit - 1].update(new_scores)
            return redirect(url_for("index"))

        # Tính điểm ván mới
        chi_dau = request.form.get("chi_dau", "").strip().lower()
        chi_giua = request.form.get("chi_giua", "").strip().lower()
        chi_cuoi = request.form.get("chi_cuoi", "").strip().lower()

        # Cập nhật last chi
        last_chi_dau = chi_dau
        last_chi_giua = chi_giua
        last_chi_cuoi = chi_cuoi

        mau_binh_choices = {p: request.form.get(f"mau_binh_{p}", "none") for p in players}
        for p in players:
            scores[p]["mau_binh"] = mau_binh_choices[p]

        mb_players = [p for p in players if scores[p]["mau_binh"] != "none"]
        has_mau_binh = len(mb_players) > 0

        # Reset điểm trước khi tính
        for p in players:
            scores[p]["chi_dau"] = 0
            scores[p]["chi_giua"] = 0
            scores[p]["chi_cuoi"] = 0
            scores[p]["sap_ham"] = 0
            scores[p]["tong"] = 0

        if has_mau_binh:
            # Có Mậu Binh -> không tính chi, không sập hầm
            apply_mau_binh_scoring(mb_players)
        else:
            # Không MB -> tính chi
            if chi_dau:
                calculate_points(chi_dau, "chi_dau")
            if chi_giua:
                calculate_points(chi_giua, "chi_giua")
            if chi_cuoi:
                calculate_points(chi_cuoi, "chi_cuoi")

            for player in players:
                scores[player]["tong"] = (
                    scores[player]["chi_dau"] + scores[player]["chi_giua"] + scores[player]["chi_cuoi"]
                )

            check_sap_ham()

            for player in players:
                scores[player]["tong"] += scores[player]["sap_ham"]

        # Lưu vào history
        round_data = {"round": len(history) + 1}
        for p in players:
            round_data[p] = scores[p]["tong"]
            if scores[p]["mau_binh"] != "none":
                round_data[f"{p}_mau_binh"] = scores[p]["mau_binh"]

        history.append(round_data)

        # Cập nhật tổng điểm
        for p in players:
            player_total_points[p] += scores[p]["tong"]

        # Reset mậu binh về không
        for p in players:
            scores[p]["mau_binh"] = "none"

        return redirect(url_for("index"))

    # Nếu là GET request, reset giá trị mặc định
    conversion_rate = default_conversion_rate
    currency = default_currency

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
        currency=currency,
        max_players=max_players,
        min_players=min_players,
        last_chi_dau=last_chi_dau,
        last_chi_giua=last_chi_giua,
        last_chi_cuoi=last_chi_cuoi
    )


""" def calculate_points(order, chi):
    code_map = {
        'a': 'Alvin',
        'r': 'Ryan',
        'm': 'May',
        'c': 'Cece'
    }
    num_p = len(players)
    if len(order) != num_p:
        return

    ranked_players = []
    for i, code in enumerate(order):
        if code in code_map and code_map[code] in players:
            ranked_players.append(code_map[code])
        else:
            return

    if num_p == 2:
        # 2 người
        scores[ranked_players[0]][chi] = 3
        scores[ranked_players[1]][chi] = -3
    elif num_p == 3:
        # 3 người: so sánh cặp
        # p[0] vs p[1]
        scores[ranked_players[0]][chi] += 1
        scores[ranked_players[1]][chi] -= 1
        # p[0] vs p[2]
        scores[ranked_players[0]][chi] += 1
        scores[ranked_players[2]][chi] -= 1
        # p[1] vs p[2]
        scores[ranked_players[1]][chi] += 1
        scores[ranked_players[2]][chi] -= 1
    else:
        # 4 người
        point_map = {0:3,1:1,2:-1,3:-3}
        for i, p in enumerate(ranked_players):
            scores[p][chi] = point_map[i] """
def calculate_points(order, chi):
    num_p = len(players)
    if len(order) != num_p:
        return

    # Tạo map ký tự đầu -> player
    first_letters_map = {}
    for p in players:
        first_letter = p[0].lower()
        # Giả sử không có trùng, nếu có thì phải xử lý thêm
        first_letters_map[first_letter] = p

    ranked_players = []
    for code in order:
        if code in first_letters_map:
            p = first_letters_map[code]
            if p in players:
                ranked_players.append(p)
            else:
                return
        else:
            # Ký tự không hợp lệ
            return

    if num_p == 2:
        # 2 người
        scores[ranked_players[0]][chi] = 3
        scores[ranked_players[1]][chi] = -3
    elif num_p == 3:
        # 3 người: so sánh cặp
        scores[ranked_players[0]][chi] += 1
        scores[ranked_players[1]][chi] -= 1

        scores[ranked_players[0]][chi] += 1
        scores[ranked_players[2]][chi] -= 1

        scores[ranked_players[1]][chi] += 1
        scores[ranked_players[2]][chi] -= 1
    else:
        # 4 người
        point_map = {0:3,1:1,2:-1,3:-3}
        for i, p in enumerate(ranked_players):
            scores[p][chi] = point_map[i]


def check_sap_ham():
    global sap_ham_results
    sap_ham_results.clear()
    non_mau_binh_players = [p for p in players if scores[p]["mau_binh"] == "none"]

    for loser in non_mau_binh_players:
        for winner in non_mau_binh_players:
            if winner != loser:
                if (scores[winner]["chi_dau"] > scores[loser]["chi_dau"] and
                    scores[winner]["chi_giua"] > scores[loser]["chi_giua"] and
                    scores[winner]["chi_cuoi"] > scores[loser]["chi_cuoi"]):
                    scores[loser]["sap_ham"] -= 3
                    scores[winner]["sap_ham"] += 3
                    sap_ham_results.append(f"{loser} đã bị Sập Hầm bởi {winner}")

def apply_mau_binh_scoring(mb_players):
    # Mậu Binh logic cũ giữ nguyên
    # 1 MB: MB ăn MB_points từ mỗi non-MB
    # >1 MB: tính chênh lệch giữa MB, non-MB trả cho từng MB
    mb_values = {p: mau_binh_points[scores[p]["mau_binh"]] for p in players}
    non_mb = [p for p in players if p not in mb_players]

    if len(mb_players) == 1:
        mb_player = mb_players[0]
        val = mb_values[mb_player]
        for other in non_mb:
            scores[mb_player]["tong"] += val
            scores[other]["tong"] -= val
    else:
        # Nhiều MB players
        for p1 in mb_players:
            for p2 in mb_players:
                if p1 != p2:
                    diff = mb_values[p1] - mb_values[p2]
                    if diff > 0:
                        scores[p1]["tong"] += diff
                        scores[p2]["tong"] -= diff
        # Non-MB trả cho mỗi MB
        for nm in non_mb:
            for mbp in mb_players:
                val = mb_values[mbp]
                scores[mbp]["tong"] += val
                scores[nm]["tong"] -= val

if __name__ == "__main__":
    app.run(debug=True)
