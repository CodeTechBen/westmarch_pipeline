
let offset = 0;
const limit = 10;

function loadSessions() {
    fetch(`/api/sessions/list?offset=${offset}`)
    .then(res => res.json())
    .then(data => {

        const container = document.getElementById('sessions-container');

        data.forEach(s => {
            const card = document.createElement('div');
            card.className = "session-card";

            card.innerHTML = `
                <div class="session-title">
                    ${s.name}
                </div>
                <div class="session-meta">
                    Date: ${s.date} |
                    DM: ${s.dm} |
                    Players: ${s.players} |
                    ${s.tier}
                </div>
            `;

            card.onclick = () => {
                window.location.href = `/session/${s.id}`;
            };

            container.appendChild(card);
        });

        offset += limit;
    });
}

// initial load
loadSessions();

// load more button
document.getElementById("load-more").addEventListener("click", loadSessions);