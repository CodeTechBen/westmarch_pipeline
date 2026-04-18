fetch(`/api/item/${itemId}`)
    .then(res => {
        if (!res.ok) {
            throw new Error("Failed to load item data");
        }
        return res.json();
    })
    .then(data => {
        populateItemHeader(data.item);
        populateTags(data.tags);
        populateDescription(data.item.description);
        populateOwners(data.owners);
        populateRarityChart(data.rarity_distribution);
    })
    .catch(error => {
        console.error(error);
        document.getElementById("item-title").textContent = "Could not load item";
    });

function populateItemHeader(item) {
    document.getElementById("item-title").textContent = item.name.toUpperCase();
    document.getElementById("item-subtitle").textContent =
        `${item.type} | Rarity: ${item.rarity}`;

    const magicalBadge = document.getElementById("item-magical-badge");
    if (item.is_magical) {
        magicalBadge.style.display = "inline-flex";
    } else {
        magicalBadge.style.display = "none";
    }
}

function populateTags(tags) {
    const container = document.getElementById("item-tags");
    container.innerHTML = "";

    if (!tags.length) {
        container.innerHTML = "<p>No tags found for this item.</p>";
        return;
    }

    tags.forEach(tag => {
        const span = document.createElement("span");
        span.className = "item-tag-pill";
        span.textContent = tag;
        container.appendChild(span);
    });
}

function populateDescription(description) {
    document.getElementById("item-description").textContent = description || "";
}

function populateOwners(owners) {
    const tbody = document.getElementById("item-owners-body");
    const count = document.getElementById("owner-count");

    tbody.innerHTML = "";
    count.textContent = `(${owners.length})`;

    if (!owners.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5">No characters found for this item.</td>
            </tr>
        `;
        return;
    }

    owners.forEach(owner => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><a class="character-link" href="/character/${owner.character_id}">${owner.character_name}</a></td>
            <td><a class="player-link" href="/player/${owner.player_id}">${owner.player_name}</a></td>
            <td>${owner.class_display}</td>
            <td>${owner.quantity}</td>
            <td>${owner.is_active ? "✓" : "✗"}</td>
        `;
        tbody.appendChild(tr);
    });
}

function populateRarityChart(rarityDistribution) {
    const canvas = document.getElementById("rarityDistributionChart");

    if (!rarityDistribution.labels.length) {
        canvas.parentElement.innerHTML = "<p>No rarity data found.</p>";
        return;
    }

    new Chart(canvas, {
        type: "pie",
        data: {
            labels: rarityDistribution.labels,
            datasets: [{
                data: rarityDistribution.values,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: "bottom"
                }
            }
        }
    });
}