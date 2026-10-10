(function () {
  // Mobile navigation toggle
  var btn = document.getElementById("navToggle");
  var nav = document.getElementById("mainNav");
  if (btn && nav) btn.addEventListener("click", function () { nav.classList.toggle("open"); });

  // Auto-dismiss flash messages (except ones that contain a generated password)
  document.querySelectorAll(".alert").forEach(function (el) {
    if (/password/i.test(el.textContent)) return;
    setTimeout(function () { el.style.display = "none"; }, 8000);
  });

  // Scroll chat threads to the newest message
  var thread = document.getElementById("thread");
  if (thread) thread.scrollTop = thread.scrollHeight;

  // Confirm dangerous actions: <form data-confirm="Are you sure?">
  document.querySelectorAll("form[data-confirm]").forEach(function (f) {
    f.addEventListener("submit", function (e) {
      if (!window.confirm(f.getAttribute("data-confirm"))) e.preventDefault();
    });
  });
})();
