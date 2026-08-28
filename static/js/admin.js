const statsGrid = document.getElementById("stats-grid");
const userMgmtList = document.getElementById("user-mgmt-list");
const broadcastForm = document.getElementById("broadcast-form");
const broadcastFeed = document.getElementById("broadcast-feed");
const logoutBtn = document.getElementById("admin-logout-btn");

let allUsersAdmin = [];
let bannedUserIds = new Set();

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function formatTime(isoString) {
  const date = new Date(isoString);
  return date.toLocaleString([], { hour: "2-digit", minute: "2-digit", month: "short", day: "numeric" });
}

function renderStats(stats) {
  const items = [
    { label: "Total Users", value: stats.total_users },
    { label: "Online Now", value: stats.online_users },
    { label: "Groups", value: stats.total_groups },
    { label: "DM Messages", value: stats.total_dm_messages },
    { label: "Group Messages", value: stats.total_group_messages },
    { label: "Global Messages", value: stats.total_global_messages },
    { label: "Broadcasts", value: stats.total_broadcasts },
    { label: "Active Bans", value: stats.active_bans },
  ];
  statsGrid.innerHTML = items
    .map(
      (i) => `
      <div class="stat-card">
        <div class="stat-value">${i.value}</div>
        <div class="stat-label">${i.label}</div>
      </div>
    `
    )
    .join("");
}

function renderUserManagement() {
  if (allUsersAdmin.length === 0) {
    userMgmtList.innerHTML = `<div class="empty-state">No other users</div>`;
    return;
  }

  userMgmtList.innerHTML = allUsersAdmin
    .map((u) => {
      const isBanned = bannedUserIds.has(u.id);
      return `
        <div class="admin-user-row">
          <div class="admin-user-info">
            <div class="user-avatar small">
              ${u.profile_pic ? `<img src="${u.profile_pic}" alt="">` : `<i class="fa-solid fa-user"></i>`}
              ${u.is_online ? `<span class="status-dot online"></span>` : ""}
            </div>
            <span>${escapeHtml(u.username)}</span>
            ${isBanned ? `<span class="ban-tag">Banned</span>` : ""}
          </div>
          <div class="admin-user-actions">
            ${
              isBanned
                ? `<button class="admin-btn unban" data-action="unban" data-user-id="${u.id}">Unban</button>`
                : `
                  <button class="admin-btn kick" data-action="kick" data-user-id="${u.id}">Kick</button>
                  <button class="admin-btn ban" data-action="ban" data-user-id="${u.id}">Ban</button>
                `
            }
          </div>
        </div>
      `;
    })
    .join("");
}

userMgmtList.addEventListener("click", (e) => {
  const btn = e.target.closest(".admin-btn");
  if (!btn) return;
  const userId = parseInt(btn.dataset.userId, 10);
  const action = btn.dataset.action;

  if (action === "kick") {
    socket.emit("kick_user", { user_id: userId });
  } else if (action === "ban") {
    const reason = prompt("Reason for ban (optional):") || "";
    socket.emit("ban_user", { user_id: userId, reason });
  } else if (action === "unban") {
    socket.emit("unban_user", { user_id: userId });
  }
});

broadcastForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const input = document.getElementById("broadcast-input");
  const content = input.value.trim();
  if (!content) return;
  socket.emit("send_broadcast", { content });
  input.value = "";
});

function renderBroadcastFeed(broadcasts) {
  if (broadcasts.length === 0) {
    broadcastFeed.innerHTML = `<div class="empty-state">No broadcasts yet</div>`;
    return;
  }
  broadcastFeed.innerHTML = broadcasts
    .map(
      (b) => `
      <div class="broadcast-item">
        <div class="broadcast-meta">
          <strong>${escapeHtml(b.admin_username || "Admin")}</strong>
          <span>${formatTime(b.timestamp)}</span>
        </div>
        <div class="broadcast-content">${escapeHtml(b.content)}</div>
      </div>
    `
    )
    .join("");
}

logoutBtn.addEventListener("click", async () => {
  await fetch("/auth/logout", { method: "POST" });
  window.location.href = "/login";
});

socket.on("admin_stats", renderStats);

socket.on("all_users", (data) => {
  allUsersAdmin = data.users;
  renderUserManagement();
});

socket.on("banned_users", (data) => {
  bannedUserIds = new Set(data.bans.map((b) => b.user_id));
  renderUserManagement();
});

socket.on("broadcast_history", (data) => {
  renderBroadcastFeed(data.broadcasts);
});

socket.on("new_broadcast", (broadcast) => {
  const emptyState = broadcastFeed.querySelector(".empty-state");
  if (emptyState) broadcastFeed.innerHTML = "";
  broadcastFeed.insertAdjacentHTML(
    "afterbegin",
    `
      <div class="broadcast-item">
        <div class="broadcast-meta">
          <strong>${escapeHtml(broadcast.admin_username || "Admin")}</strong>
          <span>${formatTime(broadcast.timestamp)}</span>
        </div>
        <div class="broadcast-content">${escapeHtml(broadcast.content)}</div>
      </div>
    `
  );
});

socket.on("admin_action", () => {
  socket.emit("get_all_users");
  socket.emit("get_banned_users");
  socket.emit("get_admin_stats");
});

socket.on("error", (data) => {
  alert(data.message);
});

// Initial load
socket.emit("get_admin_stats");
socket.emit("get_all_users");
socket.emit("get_banned_users");
socket.emit("get_broadcast_history", { limit: 20 });