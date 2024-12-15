// localstore.js
function showNotification(message) {
    const notification = document.getElementById("notification");
    notification.textContent = message;
    notification.style.display = "block";

    // Tự động ẩn sau 3 giây
    setTimeout(() => {
        notification.style.display = "none";
    }, 3000);
}
// Hàm này để lấy history từ localStorage
function getHistoryFromLocalStorage() {
    let savedHistory = localStorage.getItem("xapxam_history");
    if (savedHistory) {
        return JSON.parse(savedHistory);
    }
    return [];
}

// Hàm này để lưu history vào localStorage
function saveHistoryToLocalStorage(newHistory) {
    localStorage.setItem("xapxam_history", JSON.stringify(newHistory));
}

// Hàm ghép history mới nhận từ server vào localStorage
function mergeAndSaveHistory(serverHistory) {
    let current = getHistoryFromLocalStorage();
    // Giả sử serverHistory là một array
    current = current.concat(serverHistory);
    saveHistoryToLocalStorage(current);
    // Hiển thị thông báo
    showNotification("Lịch sử đã được lưu vào LocalStorage!");
}

// Hàm clear history trong localStorage
function clearLocalHistory() {
    localStorage.removeItem("xapxam_history");

}

// Hàm xóa 1 record (theo round) trong localStorage
function deleteRoundFromLocalStorage(roundToDelete) {
    let current = getHistoryFromLocalStorage();
    current = current.filter(r => r.round !== roundToDelete);
    saveHistoryToLocalStorage(current);

}

// Hàm hiển thị history từ localStorage ra giao diện
// (Tuỳ bạn xử lý, ví dụ append vào bảng)
function displayHistoryFromLocalStorage() {
    let historyData = getHistoryFromLocalStorage();
    // Code xử lý historyData để hiển thị
    // ...
}
