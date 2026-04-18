let offset = 0;
const limit = 10;

const sessionsContainer = document.getElementById("sessions-container");
const dmFilter = document.getElementById("dm-filter");
const loadMoreButton = document.getElementById("load-more");

document.addEventListener("DOMContentLoaded", () => {
    loadDMs();
    loadSessions();
    wireEvents();
});

function wireEvents() {
    if (dmFilter) {
        dmFilter.addEventListener("change", () => {
            resetSessions();
            loadSessions();
        });
    }

    if (loadMoreButton) {
        loadMoreButton.addEventListener("click", loadSessions);
    }
}

function resetSessions() {
    offset = 0;
    sessionsContainer.innerHTML = "";

    if (loadMoreButton) {
        loadMoreButton.style.display = "inline-block";
        loadMoreButton.disabled = false;
        loadMoreButton.textContent = "Load More Sessions";
    }
}

function loadDMs() {
    fetch("/api/dms")
        .then(res => {
            if (!res.ok) {
                throw new Error("Failed to load DMs");
            }
            return res.json();
        })
        .then(dms => {
            if (!dmFilter) return;

            dmFilter.innerHTML = `<option value="">Filter by DM</option>`;

            dms.forEach(dm => {
                const option = document.createElement("option");
                option.value = dm;
                option.textContent = dm;
                dmFilter.appendChild(option);
            });
        })
        .catch(error => {
            console.error("Error loading DMs:", error);
        });
}

function loadSessions() {
    const selectedDM = dmFilter ? dmFilter.value : "";

    let url = `/api/sessions/list?offset=${offset}&limit=${limit}`;
    if (selectedDM) {
        url += `&dm=${encodeURIComponent(selectedDM)}`;
    }

    if (loadMoreButton) {
        loadMoreButton.disabled = true;
        loadMoreButton.textContent = "Loading...";
    }

    fetch(url)
        .then(res => {
            if (!res.ok) {
                throw new Error("Failed to load sessions");
            }
            return res.json();
        })
        .then(data => {
            if (!Array.isArray(data)) {
                throw new Error("Invalid session response");
            }

            if (data.length === 0 && offset === 0) {
                sessionsContainer.innerHTML = `
                    <div class="empty-state">
                        No sessions found${selectedDM ? ` for DM: ${selectedDM}` : ""}.
                    </div>
                `;
                if (loadMoreButton) {
                    loadMoreButton.style.display = "none";
                }
                return;
            }

            data.forEach(session => {
                sessionsContainer.appendChild(createSessionCard(session));
            });

            offset += data.length;

            if (loadMoreButton) {
                if (data.length < limit) {
                    loadMoreButton.style.display = "none";
                } else {
                    loadMoreButton.style.display = "inline-block";
                    loadMoreButton.disabled = false;
                    loadMoreButton.textContent = "Load More Sessions";
                }
            }
        })
        .catch(error => {
            console.error("Error loading sessions:", error);

            if (offset === 0) {
                sessionsContainer.innerHTML = `
                    <div class="empty-state">
                        Could not load sessions.
                    </div>
                `;
            }

            if (loadMoreButton) {
                loadMoreButton.disabled = false;
                loadMoreButton.textContent = "Load More Sessions";
            }
        });
}

function createSessionCard(session) {
    const card = document.createElement("div");
    card.className = "session-card";

    card.innerHTML = `
        <div class="session-title">
            ${escapeHtml(session.name)}
        </div>
        <div class="session-meta">
            Date: ${escapeHtml(session.date)} |
            DM: ${escapeHtml(session.dm || "Unknown")} |
            Players: ${escapeHtml(String(session.players ?? 0))} |
            ${escapeHtml(session.tier || "Unknown")}
        </div>
    `;

    card.addEventListener("click", () => {
        window.location.href = `/session/${session.id}`;
    });

    return card;
}

function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value;
    return div.innerHTML;
}