const currentUserId = window.ECHO_USER.id;

const userListEl = document.getElementById("user-list");
const searchInput = document.getElementById("user-search");
const logoutBtn = document.getElementById("logout-btn");

let onlineUsers = [];

function renderUserList() {
  const query = searchInput.value.trim().toLowerCase();
  const filtered = onlineUsers.filter(
    (u) => u.id !== currentUserId && u.username.toLowerCase().includes(query)
  );

  if (filtered.length === 0) {
    userListEl.innerHTML = `<div class="empty-state">No other users online</div>`;
    return;
  }

  userListEl.innerHTML = filtered
    .map(
      (user) => `
      <div class="user-item" data-user-id="${user.id}">
        <div class="user-avatar">
          ${
            user.profile_pic
              ? `<img src="${user.profile_pic}" alt="">`
              : `<i class="fa-solid fa-user"></i>`
          }
          <span class="status-dot online"></span>
        </div>
        <div class="user-name">${user.username}</div>
      </div>
    `
    )
    .join("");
}

searchInput.addEventListener("input", renderUserList);

logoutBtn.addEventListener("click", async () => {
  await fetch("/auth/logout", { method: "POST" });
  window.location.href = "/login";
});

socket.on("online_users_snapshot", (data) => {
  onlineUsers = data.users;
  renderUserList();
});

socket.on("presence_update", (data) => {
  const idx = onlineUsers.findIndex((u) => u.id === data.user_id);
  if (data.is_online) {
    if (idx === -1) {
      onlineUsers.push({
        id: data.user_id,
        username: data.username,
        profile_pic: null,
        is_online: true,
      });
    }
  } else if (idx !== -1) {
    onlineUsers.splice(idx, 1);
  }
  renderUserList();
});

socket.on("error", (data) => {
  console.error("Socket error:", data.message);
});