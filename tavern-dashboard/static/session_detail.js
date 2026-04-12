console.log("session_detail.js loaded");
console.log("sessionId =", sessionId);

fetch(`/api/session/${sessionId}`)
    .then(res => {
        console.log("API response status:", res.status);
        if (!res.ok) {
            throw new Error("Failed to load session data");
        }
        return res.json();
    })
    .then(data => {
        console.log("Session API data:", data);

        console.log("title element:", document.getElementById("session-title"));
        console.log("character container:", document.getElementById("character-container"));
        console.log("item body:", document.getElementById("item-body"));
        console.log("recommendation element:", document.getElementById("recommendation"));

        populateHeader(data.session);
        populateCharacters(data.characters);
        populateItems(data.items, data.recommendation);
    })
    .catch(error => {
        console.error("Session page error:", error);
        const title = document.getElementById("session-title");
        if (title) {
            title.textContent = "Could not load session";
        }
    });

function populateHeader(session) {
    document.getElementById("session-title").textContent = session.name;
    document.getElementById("session-date").textContent = `📅 ${session.date}`;
    document.getElementById("session-dm").textContent = `🎲 DM: ${session.dm || "Unknown"}`;
    document.getElementById("session-tier").textContent = `⚔️ ${session.tier}`;
}

function populateCharacters(characters) {
    const container = document.getElementById("character-container");
    container.innerHTML = "";

    if (!characters.length) {
        container.innerHTML = "<p>No characters found for this session.</p>";
        return;
    }

    characters.forEach(c => {
        const card = document.createElement("div");
        card.className = "character-card";

        card.innerHTML = `
            <div class="card-header">
                <img 
                    src="${c.avatar || '/static/default-avatar.svg'}" 
                    alt="${c.name}" 
                    class="avatar"
                    onerror="this.src='/static/default-avatar.svg'"
                >
                <div>
                    <div class="player">player: <a href="/player/${c.player_id}">${c.player}</a></div>
                    <div class="name">${c.name}</div>
                </div>
            </div>

            <div class="divider"></div>

            <div class="stats-row">
                <span>HP: ${c.hp}</span>
                <span>AC: ${c.ac}</span>
                <span>PP: ${c.pp}</span>
                <span>Lvl: ${c.level}</span>
            </div>

            <div class="divider"></div>

            <div class="attributes">
                STR ${c.stats.STR} |
                DEX ${c.stats.DEX} |
                CON ${c.stats.CON} |
                INT ${c.stats.INT} |
                WIS ${c.stats.WIS} |
                CHA ${c.stats.CHA}
            </div>
        `;

        container.appendChild(card);
    });
}

function populateItems(items, recommendation) {
    const tbody = document.getElementById("item-body");
    const recommendationBox = document.getElementById("recommendation");

    tbody.innerHTML = "";

    const entries = Object.entries(items);

    if (!entries.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7">No item data found for this session.</td>
            </tr>
        `;
        recommendationBox.textContent = "";
        return;
    }

    entries.forEach(([characterName, itemData]) => {
        const row = document.createElement("tr");

        if (characterName === recommendation) {
            row.classList.add("highlight");
        }

        row.innerHTML = `
            <td>${characterName}</td>
            <td>${itemData.gold}</td>
            <td>${itemData["Common"] || 0}</td>
            <td>${itemData["Uncommon"] || 0}</td>
            <td>${itemData["Rare"] || 0}</td>
            <td>${itemData["Very Rare"] || 0}</td>
            <td>${itemData["Legendary"] || 0}</td>
        `;

        tbody.appendChild(row);
    });

    if (recommendation) {
        recommendationBox.textContent = `💡 Recommendation: ${recommendation} has very few items. Could benefit from rewards.`;
    } else {
        recommendationBox.textContent = "";
    }
}