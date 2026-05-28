const API = "";

const $ = (s, root = document) => root.querySelector(s);
const $$ = (s, root = document) => Array.from(root.querySelectorAll(s));

function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2500);
}

async function api(path, opts = {}) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    toast(data.error || `HTTP ${res.status}`);
    throw new Error(data.error || res.status);
  }
  return data;
}

// ---- Tabs ----
$$("nav button").forEach(b => b.addEventListener("click", () => {
  $$("nav button").forEach(x => x.classList.remove("active"));
  $$(".tab").forEach(x => x.classList.remove("active"));
  b.classList.add("active");
  $("#tab-" + b.dataset.tab).classList.add("active");
  loadTab(b.dataset.tab);
}));

function loadTab(name) {
  if (name === "employees") loadEmployees();
  else if (name === "attendance") loadAttendance();
  else if (name === "stats") loadStats();
  else if (name === "leave") loadLeave();
  else if (name === "holidays") loadHolidays();
}

// ---- Camera ----
let stream = null;
async function startCamera(videoEl) {
  if (stream) return stream;
  stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
  videoEl.srcObject = stream;
  return stream;
}

function snapshot(videoEl) {
  const c = document.createElement("canvas");
  c.width = videoEl.videoWidth;
  c.height = videoEl.videoHeight;
  c.getContext("2d").drawImage(videoEl, 0, 0);
  return c.toDataURL("image/jpeg", 0.85);
}

// ---- Recognize tab ----
$("#startCam").addEventListener("click", () => startCamera($("#video")));

async function recognize() {
  const video = $("#video");
  if (!video.srcObject) await startCamera(video);
  const image = snapshot(video);
  try {
    const data = await api("/api/recognize", { method: "POST", body: JSON.stringify({ image }) });
    const list = $("#recognizeResults");
    list.innerHTML = "";
    (data.results || []).forEach(r => {
      const li = document.createElement("li");
      if (r.matched) {
        li.innerHTML = `<strong>${r.name}</strong> (${r.employee_id}) — ${r.department || ""} · ${r.action} · conf ${(r.confidence*100).toFixed(1)}%`;
      } else {
        li.className = "miss";
        li.textContent = "Unknown face";
      }
      list.appendChild(li);
    });
    drawBoxes(data.results || []);
  } catch (e) { /* toast already shown */ }
}

function drawBoxes(results) {
  const canvas = $("#overlay");
  const video = $("#video");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  results.forEach(r => {
    const b = r.bounding_box;
    if (!b) return;
    ctx.strokeStyle = r.matched ? "#10b981" : "#ef4444";
    ctx.lineWidth = 3;
    ctx.strokeRect(b.left, b.top, b.right - b.left, b.bottom - b.top);
    if (r.matched) {
      ctx.fillStyle = "#10b981";
      ctx.fillRect(b.left, b.top - 20, ctx.measureText(r.name).width + 12, 20);
      ctx.fillStyle = "#fff";
      ctx.font = "14px sans-serif";
      ctx.fillText(r.name, b.left + 6, b.top - 5);
    }
  });
}

$("#capture").addEventListener("click", recognize);

let loopTimer = null;
$("#autoLoop").addEventListener("change", e => {
  if (e.target.checked) {
    loopTimer = setInterval(recognize, 3000);
  } else if (loopTimer) {
    clearInterval(loopTimer);
    loopTimer = null;
  }
});

// ---- Employees ----
async function loadEmployees() {
  const list = await api("/api/employees");
  const tbody = $("#empTable tbody");
  tbody.innerHTML = "";
  list.forEach(e => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${e.name}</td>
      <td>${e.employee_id}</td>
      <td>${e.department || ""}</td>
      <td>${e.role || ""}</td>
      <td>${e.has_face ? "✓" : "—"}</td>
      <td>${e.is_active ? "Yes" : "No"}</td>
      <td>
        <button data-id="${e.id}" class="reg">Register face</button>
        <button data-id="${e.id}" class="del danger">Delete</button>
      </td>`;
    tbody.appendChild(tr);
  });
  $$("#empTable .reg").forEach(b => b.addEventListener("click", () => openRegister(b.dataset.id)));
  $$("#empTable .del").forEach(b => b.addEventListener("click", async () => {
    if (!confirm("Soft delete employee?")) return;
    await api("/api/employees/" + b.dataset.id, { method: "DELETE" });
    loadEmployees();
  }));
}

$("#empForm").addEventListener("submit", async e => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = {};
  fd.forEach((v, k) => body[k] = v);
  await api("/api/employees", { method: "POST", body: JSON.stringify(body) });
  e.target.reset();
  toast("Employee added");
  loadEmployees();
});

let registerTargetId = null;
async function openRegister(id) {
  registerTargetId = id;
  $("#empRegName").textContent = "#" + id;
  $("#empRegisterFace").classList.remove("hidden");
  await startCamera($("#regVideo"));
}

$("#regCancel")?.addEventListener("click", () => {
  $("#empRegisterFace").classList.add("hidden");
  registerTargetId = null;
});

$("#regCapture")?.addEventListener("click", async () => {
  if (!registerTargetId) return;
  const image = snapshot($("#regVideo"));
  try {
    await api("/api/register-face", { method: "POST", body: JSON.stringify({ employee_id: registerTargetId, image }) });
    toast("Face registered");
    $("#empRegisterFace").classList.add("hidden");
    loadEmployees();
  } catch (e) { /* shown */ }
});

// ---- Attendance ----
async function loadAttendance() {
  const params = new URLSearchParams();
  if ($("#attDate").value) params.set("date", $("#attDate").value);
  if ($("#attDept").value) params.set("department", $("#attDept").value);
  if ($("#attStatus").value) params.set("status", $("#attStatus").value);
  const rows = await api("/api/attendance?" + params);
  const tbody = $("#attTable tbody");
  tbody.innerHTML = "";
  rows.forEach(r => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${r.date}</td>
      <td>${r.employee_name || ""}</td>
      <td>${r.department || ""}</td>
      <td>${r.check_in ? r.check_in.slice(11, 16) : ""}</td>
      <td>${r.check_out ? r.check_out.slice(11, 16) : ""}</td>
      <td>${r.working_hours ?? ""}</td>
      <td><span class="badge ${r.status}">${r.status || ""}</span></td>
      <td><button data-id="${r.id}" class="del danger">Delete</button></td>`;
    tbody.appendChild(tr);
  });
  $$("#attTable .del").forEach(b => b.addEventListener("click", async () => {
    if (!confirm("Delete record?")) return;
    await api("/api/attendance/" + b.dataset.id, { method: "DELETE" });
    loadAttendance();
  }));
}
$("#attLoad").addEventListener("click", loadAttendance);
$("#attExportCsv").addEventListener("click", () => {
  const start = $("#attDate").value || new Date().toISOString().slice(0, 10);
  const url = `/api/attendance/export?start=${start}&end=${start}&format=csv`;
  window.open(url, "_blank");
});

// ---- Stats ----
async function loadStats() {
  const d = $("#statsDate").value || new Date().toISOString().slice(0, 10);
  const s = await api("/api/stats?date=" + d);
  $("#statsBox").innerHTML = `
    <div class="card"><h4>Total</h4><div class="v">${s.total_employees}</div></div>
    <div class="card"><h4>Present</h4><div class="v">${s.present}</div></div>
    <div class="card"><h4>Late</h4><div class="v">${s.late}</div></div>
    <div class="card"><h4>Absent</h4><div class="v">${s.absent}</div></div>
    <div class="card"><h4>On Leave</h4><div class="v">${s.on_leave}</div></div>
    <div class="card"><h4>Avg Hours</h4><div class="v">${s.avg_working_hours}</div></div>`;
}
$("#statsLoad").addEventListener("click", loadStats);

$("#statsMonthLoad").addEventListener("click", async () => {
  const y = $("#statsYear").value || new Date().getFullYear();
  const m = $("#statsMonth").value || (new Date().getMonth() + 1);
  const d = await api(`/api/stats/monthly?year=${y}&month=${m}`);
  const tbody = $("#monthTable tbody");
  tbody.innerHTML = "";
  d.days.forEach(row => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${row.date}</td><td>${row.present}</td><td>${row.late}</td><td>${row.absent}</td>`;
    tbody.appendChild(tr);
  });
});

// ---- Leave ----
async function loadLeave() {
  const rows = await api("/api/leave");
  const tbody = $("#leaveTable tbody");
  tbody.innerHTML = "";
  rows.forEach(r => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${r.employee_name || r.employee_id}</td>
      <td>${r.leave_type}</td>
      <td>${r.start_date}</td>
      <td>${r.end_date}</td>
      <td>${r.reason || ""}</td>
      <td><span class="badge ${r.status}">${r.status}</span></td>
      <td>
        ${r.status === "pending" ? `<button data-id="${r.id}" data-s="approved">Approve</button>
        <button data-id="${r.id}" data-s="rejected" class="danger">Reject</button>` : ""}
      </td>`;
    tbody.appendChild(tr);
  });
  $$("#leaveTable button[data-s]").forEach(b => b.addEventListener("click", async () => {
    await api("/api/leave/" + b.dataset.id, { method: "PUT", body: JSON.stringify({ status: b.dataset.s }) });
    loadLeave();
  }));
}

$("#leaveForm").addEventListener("submit", async e => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = {};
  fd.forEach((v, k) => body[k] = v);
  body.employee_id = parseInt(body.employee_id);
  await api("/api/leave", { method: "POST", body: JSON.stringify(body) });
  e.target.reset();
  toast("Leave submitted");
  loadLeave();
});

// ---- Holidays ----
async function loadHolidays() {
  const rows = await api("/api/holidays");
  const tbody = $("#holTable tbody");
  tbody.innerHTML = "";
  rows.forEach(h => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${h.date}</td><td>${h.name}</td><td>${h.description || ""}</td>
      <td><button data-id="${h.id}" class="del danger">Delete</button></td>`;
    tbody.appendChild(tr);
  });
  $$("#holTable .del").forEach(b => b.addEventListener("click", async () => {
    await api("/api/holidays/" + b.dataset.id, { method: "DELETE" });
    loadHolidays();
  }));
}

$("#holForm").addEventListener("submit", async e => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = {};
  fd.forEach((v, k) => body[k] = v);
  await api("/api/holidays", { method: "POST", body: JSON.stringify(body) });
  e.target.reset();
  loadHolidays();
});

// Default dates
$("#attDate").value = new Date().toISOString().slice(0, 10);
$("#statsDate").value = new Date().toISOString().slice(0, 10);
