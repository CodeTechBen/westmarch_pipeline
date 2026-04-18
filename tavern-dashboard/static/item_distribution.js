let rewardChart = null;
let itemTypeDonutChart = null;
let itemRarityDonutChart = null;

const tierFilter = document.getElementById("tier-filter");
const dateFromInput = document.getElementById("date-from");
const dateToInput = document.getElementById("date-to");
const rankByFilter = document.getElementById("rank-by-filter");
const valueFilter = document.getElementById("value-filter");

[tierFilter, dateFromInput, dateToInput, rankByFilter, valueFilter].forEach(el => {
    el.addEventListener("change", loadRewardDistribution);
});

loadRewardDistribution();

function loadRewardDistribution() {
    const params = new URLSearchParams({
        tier: tierFilter.value,
        date_from: dateFromInput.value,
        date_to: dateToInput.value,
        rank_by: rankByFilter.value,
        value: valueFilter.value
    });

    fetch(`/api/item-distribution?${params.toString()}`)
        .then(res => {
            if (!res.ok) {
                throw new Error("Failed to load reward distribution data");
            }
            return res.json();
        })
        .then(data => {
            populateRewardTable(data.table, data.filters.rank_by);
            populateRewardChart(data.chart);
            populateItemTypeDonutChart(data.item_type_distribution);
            populateItemRarityDonutChart(data.item_rarity_distribution);
        })
        .catch(error => {
            console.error(error);
            document.getElementById("reward-table-body").innerHTML = `
                <tr>
                    <td colspan="7">Could not load reward distribution data.</td>
                </tr>
            `;
        });
}

function populateRewardTable(rows, rankBy) {
    const tbody = document.getElementById("reward-table-body");
    tbody.innerHTML = "";

    if (!rows.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7">No results found for these filters.</td>
            </tr>
        `;
        return;
    }

    rows.forEach(row => {
        const tr = document.createElement("tr");

        const nameCell = rankBy === "character"
            ? `<a href="/character/${row.id}" class="character-link">${row.name}</a>`
            : `<a href="/player/${row.id}" class="player-link">${row.name}</a>`;

        tr.innerHTML = `
            <td>${row.rank}</td>
            <td>${nameCell}</td>
            <td>${row.tier}</td>
            <td>${row.gold}</td>
            <td>${row.item_count}</td>
            <td>${row.avg_rarity}</td>
            <td>${Math.round(row.both_score)} pts</td>
        `;

        tbody.appendChild(tr);
    });
}

function populateRewardChart(chartData) {
    const title = document.getElementById("reward-chart-title");
    title.textContent = chartData.title;

    const ctx = document.getElementById("rewardDistributionChart");

    if (rewardChart) {
        rewardChart.destroy();
    }

    rewardChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: chartData.labels,
            datasets: [{
                label: chartData.title,
                data: chartData.values,
                borderWidth: 1
            }]
        },
        options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    enabled: true
                }
            },
            scales: {
                x: {
                    beginAtZero: true
                }
            }
        }
    });
}

function populateItemTypeDonutChart(chartData) {
    const ctx = document.getElementById("itemTypeDonutChart");

    if (itemTypeDonutChart) {
        itemTypeDonutChart.destroy();
    }

    itemTypeDonutChart = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: chartData.labels,
            datasets: [{
                data: chartData.values,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "bottom"
                }
            }
        }
    });
}

function populateItemRarityDonutChart(chartData) {
    const ctx = document.getElementById("itemRarityDonutChart");

    if (itemRarityDonutChart) {
        itemRarityDonutChart.destroy();
    }

    itemRarityDonutChart = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: chartData.labels,
            datasets: [{
                data: chartData.values,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "bottom"
                }
            }
        }
    });
}