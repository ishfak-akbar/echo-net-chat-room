const tabs = document.querySelectorAll(".auth-tab");
const forms = {
  login: document.getElementById("login-form"),
  register: document.getElementById("register-form"),
};
const errorBox = document.getElementById("auth-error");

tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    tabs.forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    const target = tab.dataset.target;
    Object.entries(forms).forEach(([key, form]) => {
      form.classList.toggle("hidden", key !== target);
    });
    errorBox.textContent = "";
  });
});

async function submitAuth(endpoint, payload) {
  errorBox.textContent = "";
  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (!data.success) {
      errorBox.textContent = data.message || "Something went wrong.";
      return;
    }

    window.location.href = "/chat";
  } catch (err) {
    errorBox.textContent = "Could not reach the server. Please try again.";
  }
}

forms.login.addEventListener("submit", (e) => {
  e.preventDefault();
  submitAuth("/auth/login", {
    username: document.getElementById("login-username").value.trim(),
    password: document.getElementById("login-password").value,
  });
});

forms.register.addEventListener("submit", (e) => {
  e.preventDefault();
  submitAuth("/auth/register", {
    username: document.getElementById("register-username").value.trim(),
    password: document.getElementById("register-password").value,
  });
});