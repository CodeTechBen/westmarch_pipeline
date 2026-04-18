fetch(`/api/player/${playerId}`)
    .then(res => {
        if (!res.ok) {
            throw new Error("Failed to load player data");
        }
        return res.json();
    })
    .then(data => {
        populatePlayerHeader(data.player, data.characters.length);
        populateCharacters(data.characters);
        populateActivityChart(data.activity);
        populateRecentSessions(data.recent_sessions);
    })
    .catch(error => {
        console.error(error);
        document.getElementById("player-title").textContent = "Could not load player";
    });

function populatePlayerHeader(player, characterCount) {
    document.getElementById("player-title").textContent = `PLAYER: ${player.name}`;
    document.getElementById("player-discord").textContent = `Discord: ${player.discord_name || "-"}`;
    document.getElementById("player-beyond").textContent = `D&D Beyond: ${player.dnd_beyond_name || "-"}`;
    document.getElementById("player-joined").textContent = `Joined: ${player.join_date}`;
    document.getElementById("player-sessions-played").textContent = `Sessions Played: ${player.sessions_played}`;
    document.getElementById("character-count").textContent = `(${characterCount})`;
}

function populateCharacters(characters) {
    const container = document.getElementById("player-characters");
    container.innerHTML = "";

    if (!characters.length) {
        container.innerHTML = "<p>No characters found for this player.</p>";
        return;
    }

    characters.forEach(character => {
        const card = document.createElement("div");
        card.className = "player-character-card";

        card.innerHTML = `
            <img
                src="${character.avatar || '/static/default-avatar.svg'}"
                alt="${character.name}"
                class="player-character-avatar"
                onerror="this.src='/static/default-avatar.svg'"
            >

            <div class="player-character-main">
                <div class="player-character-top">
                    <div class="player-character-name">${character.name}</div>
                    <div class="character-status-badge ${character.is_active ? 'character-status-active' : 'character-status-retired'}">
                        ${character.status}
                    </div>
                </div>

                <div class="player-character-subtitle">${character.subtitle}</div>

                <div class="player-character-meta">
                    ${character.tier} | ${character.sessions} sessions
                    ${character.is_active ? ` | HP: ${character.hp ?? '-'} | Gold: ${character.gold ?? '-'}` : ''}
                </div>
            </div>
        `;

        card.onclick = () => {
            window.location.href = `/character/${character.id}`;
        };

        container.appendChild(card);
    });
}

function populateActivityChart(activity) {
    const canvas = document.getElementById("sessionsPerMonthChart");

    if (!activity.labels.length) {
        const parent = canvas.parentElement;
        parent.innerHTML = "<p>No session activity found for this player.</p>";
        return;
    }

    new Chart(canvas, {
        type: "bar",
        data: {
            labels: activity.labels,
            datasets: [{
                label: "Sessions per Month",
                data: activity.values,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });
}

function populateRecentSessions(sessions) {
    const tbody = document.getElementById("recent-sessions-body");
    tbody.innerHTML = "";

    if (!sessions.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4">No recent sessions found.</td>
            </tr>
        `;
        return;
    }

    sessions.forEach(session => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td><a class="session-link" href="/session/${session.session_id}">${session.session_name}</a></td>
            <td>${session.date}</td>
            <td><a class="character-link" href="/character/${session.character_id}">${session.character_name}</a></td>
            <td>${session.dm_name}</td>
        `;
        tbody.appendChild(row);
    });
}