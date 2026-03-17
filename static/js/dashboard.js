// ── AI Chatbox Logic ────────────────────────────────────────────
// Deferred initialization until DOM is ready
let chatHistory = [];
let chatInitialized = false;

function initializeChatbox() {
    if (chatInitialized) return;
    const chatForm = document.getElementById("chatForm");
    const chatInput = document.getElementById("chatInput");
    const chatMessages = document.getElementById("chatMessages");
    const closeChatbot = document.getElementById("closeChatbot");
    const chatbotWidget = document.getElementById("chatbotWidget");
    
    if (!chatForm || !chatInput || !chatMessages) {
        console.warn("Chatbox elements not found in DOM");
        return;
    }
    
    // Setup close button
    if (closeChatbot && chatbotWidget) {
        closeChatbot.onclick = function() {
            chatbotWidget.style.display = 'none';
        };
    }
    
    chatForm.onsubmit = async (e) => {
        e.preventDefault();
        const msg = chatInput.value.trim();
        if (!msg) return;
        
        // Show user message
        chatMessages.innerHTML += `<div style='margin-bottom:8px;'><b>You:</b> ${msg}</div>`;
        chatMessages.scrollTop = chatMessages.scrollHeight;
        chatInput.value = "";
        chatInput.disabled = true;
        
        // Call backend
        try {
            const res = await fetch("/api/chat", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({ message: msg, history: chatHistory })
            });
            const data = await res.json();
            if (data.reply) {
                // Add both user message and bot reply to maintain proper conversation history
                chatHistory.push(msg);
                chatHistory.push(data.reply);
                
                chatMessages.innerHTML += `<div style='margin-bottom:8px;'><b>AI Assistant:</b> ${data.reply}</div>`;
            } else if (data.error) {
                chatMessages.innerHTML += `<div style='color:#c00;'>[Error: ${data.error}]</div>`;
            }
        } catch (err) {
            console.error("Chat error:", err);
            chatMessages.innerHTML += `<div style='color:#c00;'>[Network error: ${err.message}]</div>`;
        }
        chatMessages.scrollTop = chatMessages.scrollHeight;
        chatInput.disabled = false;
        chatInput.focus();
    };
    
    chatInitialized = true;
}
/**
 * Automatic Pet Feeder Dashboard — Frontend Logic
 * Handles schedule saving, manual feeding, pet status, AI refresh, and live clock.
 */

document.addEventListener("DOMContentLoaded", () => {
    // Initialize chatbox early
    initializeChatbox();
    
    // ── Helpers ──────────────────────────────────────────────────────────
    function toast(msg, type = "success") {
        const el = document.createElement("div");
        el.className = `toast ${type}`;
        el.textContent = msg;
        document.body.appendChild(el);
        setTimeout(() => el.remove(), 3500);
    }

    async function api(url, options = {}) {
        options.headers = { "Content-Type": "application/json", ...options.headers };
        const res = await fetch(url, options);
        const data = await res.json();
        if (!res.ok) {
            toast(data.error || "Something went wrong", "error");
            return null;
        }
        return data;
    }

    // ── Live clock (update every second) ────────────────────────────────
    function updateClock() {
        const now = new Date();
        let h = now.getHours();
        const m = now.getMinutes().toString().padStart(2, "0");
        const ampm = h >= 12 ? "PM" : "AM";
        h = h % 12 || 12;
        const el = document.getElementById("liveClock");
        if (el) el.textContent = `${h}:${m} ${ampm}`;
    }
    setInterval(updateClock, 1000);
    updateClock();

    // ── Save Schedule ───────────────────────────────────────────────────
    const saveScheduleBtn = document.getElementById("saveScheduleBtn");
    if (saveScheduleBtn) {
        saveScheduleBtn.addEventListener("click", async () => {
            let hour = parseInt(document.getElementById("schedHour").value, 10);
            const min = parseInt(document.getElementById("schedMin").value, 10);
            const ampm = document.getElementById("schedAmPm").value;

            // Convert to 24h
            if (ampm === "PM" && hour !== 12) hour += 12;
            if (ampm === "AM" && hour === 12) hour = 0;

            const feedTime = `${hour.toString().padStart(2, "0")}:${min.toString().padStart(2, "0")}`;
            const data = await api("/api/schedule", {
                method: "POST",
                body: JSON.stringify({ feed_time: feedTime, portion_size: 1.0 }),
            });
            if (data) {
                toast("Schedule saved!");
                // Add to list
                const list = document.getElementById("schedulesList");
                const item = document.createElement("div");
                item.className = "schedule-item";
                item.dataset.id = data.schedule.id;
                item.innerHTML = `<span>${data.schedule.display_time}</span>
                    <button class="btn-remove" data-id="${data.schedule.id}" title="Remove">&times;</button>`;
                list.appendChild(item);
                attachRemoveHandlers();

                // Update next feed time display
                document.getElementById("nextFeedTime").textContent = data.schedule.display_time;
            }
        });
    }

    // ── Remove schedule ─────────────────────────────────────────────────
    function attachRemoveHandlers() {
        document.querySelectorAll(".btn-remove").forEach(btn => {
            btn.onclick = async () => {
                const id = btn.dataset.id;
                const data = await api(`/api/schedule/${id}`, { method: "DELETE" });
                if (data) {
                    btn.closest(".schedule-item").remove();
                    toast("Schedule removed");
                }
            };
        });
    }
    attachRemoveHandlers();

    // ── Feed Now ────────────────────────────────────────────────────────
    const feedNowBtn = document.getElementById("feedNowBtn");
    if (feedNowBtn) {
        feedNowBtn.addEventListener("click", async () => {
            feedNowBtn.disabled = true;
            feedNowBtn.textContent = "Dispensing...";
            const data = await api("/api/feed-now", { method: "POST" });
            if (data) {
                toast(data.message);
                // Update food level
                document.getElementById("foodLabel").textContent = data.food_label;
                document.getElementById("foodPct").textContent = data.food_level + "%";
                // Add to logs
                const logsList = document.getElementById("logsList");
                const emptyState = logsList.querySelector(".empty-state");
                if (emptyState) emptyState.remove();
                const now = new Date();
                const timeStr = now.toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit", hour12: true });
                const li = document.createElement("li");
                li.innerHTML = `<strong>${timeStr.split(",")[0]}</strong> – ${timeStr.split(",")[1]?.trim() || ""} – <em>Manual</em>`;
                logsList.prepend(li);
            }
            feedNowBtn.disabled = false;
            feedNowBtn.textContent = "Feed Now";
        });
    }

    // ── Pet Status ──────────────────────────────────────────────────────
    const statusForm = document.getElementById("statusDetailForm");
    const statusTypeInput = document.getElementById("statusType");
    const severitySlider = document.getElementById("statusSeverity");
    const severityLabel = document.getElementById("severityLabel");

    document.querySelectorAll(".status-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            statusTypeInput.value = btn.dataset.status;
            statusForm.style.display = "block";
            statusForm.querySelector("h4").textContent = `Status: ${btn.textContent.trim()}`;
        });
    });

    if (severitySlider) {
        severitySlider.addEventListener("input", () => {
            severityLabel.textContent = severitySlider.value;
        });
    }

    const cancelStatusBtn = document.getElementById("cancelStatusBtn");
    if (cancelStatusBtn) {
        cancelStatusBtn.addEventListener("click", () => {
            statusForm.style.display = "none";
        });
    }

    const submitStatusBtn = document.getElementById("submitStatusBtn");
    if (submitStatusBtn) {
        submitStatusBtn.addEventListener("click", async () => {
            const data = await api("/api/pet-status", {
                method: "POST",
                body: JSON.stringify({
                    status_type: statusTypeInput.value,
                    severity: parseInt(severitySlider.value, 10),
                    description: document.getElementById("statusDescription").value,
                }),
            });
            if (data) {
                toast("Status recorded! AI suggestions updated.");
                statusForm.style.display = "none";
                document.getElementById("statusDescription").value = "";

                // Refresh active statuses
                const container = document.getElementById("activeStatuses");
                let html = "<h4>Active Statuses</h4>";
                if (data.active_statuses.length) {
                    data.active_statuses.forEach(s => {
                        const dots = "●".repeat(s.severity) + "○".repeat(5 - s.severity);
                        const tag = s.type.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
                        html += `<div class="active-status-item" data-id="${s.id}">
                            <span class="status-tag ${s.type}">${tag}</span>
                            <span class="severity-dots">${dots}</span>
                            <button class="btn-resolve" data-id="${s.id}" title="Resolve">✓</button>
                        </div>`;
                    });
                } else {
                    html += '<p class="empty-state">No active concerns!</p>';
                }
                container.innerHTML = html;
                attachResolveHandlers();

                // Update AI card
                updateAiCard(data.ai_suggestions);
            }
        });
    }

    // ── Resolve status ──────────────────────────────────────────────────
    function attachResolveHandlers() {
        document.querySelectorAll(".btn-resolve").forEach(btn => {
            btn.onclick = async () => {
                const id = btn.dataset.id;
                const data = await api(`/api/pet-status/${id}/resolve`, { method: "POST" });
                if (data) {
                    btn.closest(".active-status-item").remove();
                    toast("Status resolved");
                }
            };
        });
    }
    attachResolveHandlers();

    // ── Refresh AI suggestions ──────────────────────────────────────────
    function updateAiCard(ai) {
        if (!ai) return;
        const badge = document.getElementById("aiOverallStatus");
        if (badge) {
            badge.className = `ai-status-badge ${ai.overall_status}`;
            badge.textContent = ai.overall_status.toUpperCase();
        }
        const portion = document.getElementById("aiPortion");
        if (portion) portion.querySelector("p").textContent = ai.portion_advice;
        const vet = document.getElementById("aiVet");
        if (vet) vet.querySelector("p").textContent = ai.vet_recommendation;
        const warnings = document.getElementById("aiWarnings");
        if (warnings && ai.warnings && ai.warnings.length) {
            let whtml = "<strong>⚠️ Warnings:</strong><ul>";
            ai.warnings.forEach(w => whtml += `<li>${w}</li>`);
            whtml += "</ul>";
            warnings.innerHTML = whtml;
            warnings.style.display = "block";
        } else if (warnings) {
            warnings.style.display = "none";
        }
    }

    const refreshAiBtn = document.getElementById("refreshAiBtn");
    if (refreshAiBtn) {
        refreshAiBtn.addEventListener("click", async () => {
            const data = await api("/api/ai-suggestions");
            if (data) {
                updateAiCard(data);
                toast("AI suggestions refreshed", "info");
            }
        });
    }

    // ── Apply AI Recommendation to Schedule ───────────────────────────────
    const applyAiBtn = document.getElementById("applyAiBtn");
    if (applyAiBtn) {
        applyAiBtn.addEventListener("click", async () => {
            applyAiBtn.disabled = true;
            applyAiBtn.textContent = "Applying...";
            
            const data = await api("/api/apply-ai-recommendation", { method: "POST" });
            
            applyAiBtn.disabled = false;
            applyAiBtn.textContent = "Apply to Schedule";
            
            if (data) {
                toast(`✅ ${data.message}`, "success");
                toast(`Portion multiplier set to ${data.multiplier}x`, "info");
                console.log("Updated schedules:", data.schedules);
                
                // Optionally refresh the page or update UI
                setTimeout(() => location.reload(), 1500);
            }
        });
    }

    // ── Periodic food level update (every 30s) ──────────────────────────
    setInterval(async () => {
        try {
            const res = await fetch("/api/food-level");
            if (res.ok) {
                const data = await res.json();
                const label = document.getElementById("foodLabel");
                const pct = document.getElementById("foodPct");
                if (label) label.textContent = data.label;
                if (pct) pct.textContent = data.level + "%";
            }
        } catch { /* ignore network errors */ }
    }, 30000);

    // ── Edit Pet Modal ──────────────────────────────────────────────────
    const editPetBtn = document.getElementById("editPetBtn");
    const editPetModal = document.getElementById("editPetModal");
    const closeEditModal = document.getElementById("closeEditModal");

    if (editPetBtn) {
        editPetBtn.addEventListener("click", () => {
            editPetModal.style.display = "flex";
        });
    }
    if (closeEditModal) {
        closeEditModal.addEventListener("click", () => {
            editPetModal.style.display = "none";
        });
    }
    if (editPetModal) {
        editPetModal.addEventListener("click", (e) => {
            if (e.target === editPetModal) editPetModal.style.display = "none";
        });
    }

    // ── View More Logs ──────────────────────────────────────────────────
    const viewMoreLogs = document.getElementById("viewMoreLogs");
    let logsPage = 1;
    if (viewMoreLogs) {
        viewMoreLogs.addEventListener("click", async (e) => {
            e.preventDefault();
            logsPage++;
            const data = await api(`/api/feeding-logs?page=${logsPage}&per_page=10`);
            if (data && data.logs.length) {
                const list = document.getElementById("logsList");
                data.logs.forEach(log => {
                    const li = document.createElement("li");
                    li.innerHTML = `<strong>${log.time.split(",")[0] || log.time}</strong> – ${log.time.split(",")[1]?.trim() || ""} – <em>${log.type}</em>`;
                    list.appendChild(li);
                });
                if (logsPage >= data.pages) viewMoreLogs.style.display = "none";
            } else {
                viewMoreLogs.style.display = "none";
            }
        });
    }
});
