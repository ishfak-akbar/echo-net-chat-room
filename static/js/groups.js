let myGroups = [];
let allUsers = [];

const groupListEl = document.getElementById("group-list");
const newGroupBtn = document.getElementById("new-group-btn");
const groupModal = document.getElementById("group-modal");
const groupModalClose = document.getElementById("group-modal-close");
const groupForm = document.getElementById("group-form");
const groupMembersEl = document.getElementById("group-members-list");

function renderGroupList() {
  if (myGroups.length === 0) {
    groupListEl.innerHTML = `<div class="empty-state">No groups yet</div>`;
    return;
  }
  groupListEl.innerHTML = myGroups
    .map(
      (g) => `
      <div class="user-item group-item" data-group-id="${g.id}">
        <div class="user-avatar"><i class="fa-solid fa-users"></i></div>
        <div class="user-name">${escapeHtml(g.name)}</div>
        ${g.unread_count > 0 ? `<span class="unread-badge">${g.unread_count}</span>` : ""}
      </div>
    `
    )
    .join("");
}

function renderMemberCheckboxes() {
  if (allUsers.length === 0) {
    groupMembersEl.innerHTML = `<div class="empty-state">No other users to add</div>`;
    return;
  }
  groupMembersEl.innerHTML = allUsers
    .map(
      (u) => `
      <label class="member-checkbox">
        <input type="checkbox" value="${u.id}">
        <span>${escapeHtml(u.username)}</span>
      </label>
    `
    )
    .join("");
}

newGroupBtn.addEventListener("click", () => {
  groupModal.classList.remove("hidden");
  socket.emit("get_all_users");
});

groupModalClose.addEventListener("click", () => {
  groupModal.classList.add("hidden");
});

groupForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const name = document.getElementById("group-name-input").value.trim();
  const checked = Array.from(
    groupMembersEl.querySelectorAll("input[type=checkbox]:checked")
  ).map((cb) => parseInt(cb.value, 10));

  if (!name || checked.length === 0) {
    alert("Enter a group name and select at least one member.");
    return;
  }

  socket.emit("create_group", { name, member_ids: checked });
});

groupListEl.addEventListener("click", (e) => {
  const item = e.target.closest(".group-item");
  if (!item) return;
  const groupId = parseInt(item.dataset.groupId, 10);
  const group = myGroups.find((g) => g.id === groupId);
  if (group) openGroup(group.id, group.name);
});

socket.on("my_groups", (data) => {
  myGroups = data.groups;
  renderGroupList();
});

socket.on("group_created", () => {
  groupModal.classList.add("hidden");
  groupForm.reset();
  socket.emit("get_my_groups");
});

socket.on("all_users", (data) => {
  allUsers = data.users;
  renderMemberCheckboxes();
});

//Initial load of the user's groups on page load
socket.emit("get_my_groups");