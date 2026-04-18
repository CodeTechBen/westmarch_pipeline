let classDistributionChart = null;

const tierFilter = document.getElementById("tier-filter");
const activeOnlyFilter = document.getElementById("active-only-filter");

const multiclassTableBtn = document.getElementById("multiclass-table-btn");
const multiclassSankeyBtn = document.getElementById("multiclass-sankey-btn");
const multiclassTableView = document.getElementById("multiclass-table-view");
const multiclassSankeyView = document.getElementById("multiclass-sankey-view");

tierFilter.addEventListener("change", loadClassStats);
activeOnlyFilter.addEventListener("change", loadClassStats);

multiclassTableBtn.addEventListener("click", () => {
    multiclassTableView.style.display = "block";
    multiclassSankeyView.style.display = "none";
    multiclassTableBtn.classList.add("active");
    multiclassSankeyBtn.classList.remove("active");
});

multiclassSankeyBtn.addEventListener("click", () => {
    multiclassTableView.style.display = "none";
    multiclassSankeyView.style.display = "block";
    multiclassSankeyBtn.classList.add("active");
    multiclassTableBtn.classList.remove("active");
});

loadClassStats();

function loadClassStats() {
    const params = new URLSearchParams({
        tier: tierFilter.value,
        active_only: activeOnlyFilter.checked
    });

    fetch(`/api/class-stats?${params.toString()}`)
        .then(res => {
            if (!res.ok) {
                throw new Error("Failed to load class stats");
            }
            return res.json();
        })
        .then(data => {
            populateClassDistributionChart(data.classes);
            populateSubclassBreakdown(data.subclass_breakdown);
            populateMulticlassTable(data.multiclass_combinations);
            populateMulticlassSankey(data.multiclass_combinations);
        })
        .catch(error => {
            console.error(error);
        });
}

function populateClassDistributionChart(classes) {
    const ctx = document.getElementById("classDistributionChart");

    const labels = classes.map(c => c.class_name);
    const values = classes.map(c => c.count);

    if (classDistributionChart) {
        classDistributionChart.destroy();
    }

    classDistributionChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels,
            datasets: [{
                label: "Characters",
                data: values,
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
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });
}

function populateSubclassBreakdown(subclassBreakdown) {
    const container = document.getElementById("subclass-breakdown-container");
    container.innerHTML = "";

    if (!subclassBreakdown.length) {
        container.innerHTML = `<div class="empty-state">No subclass data found.</div>`;
        return;
    }

    subclassBreakdown.forEach(group => {
        const total = group.subclasses.reduce((sum, s) => sum + s.count, 0);

        const block = document.createElement("div");
        block.className = "subclass-group";

        const header = document.createElement("button");
        header.className = "subclass-group-header";
        header.type = "button";
        header.innerHTML = `
            <span class="subclass-toggle-icon">▶</span>
            <span>${group.class_name} (${total})</span>
        `;

        const body = document.createElement("div");
        body.className = "subclass-group-body";
        body.style.display = "none";

        group.subclasses.forEach(subclass => {
            const row = document.createElement("div");
            row.className = "subclass-row";

            row.innerHTML = `
                <span class="subclass-name">${subclass.subclass_name}</span>
                <span class="subclass-count">${subclass.count}</span>
            `;

            body.appendChild(row);
        });

        header.addEventListener("click", () => {
            const isHidden = body.style.display === "none";
            body.style.display = isHidden ? "block" : "none";
            header.querySelector(".subclass-toggle-icon").textContent = isHidden ? "▼" : "▶";
        });

        block.appendChild(header);
        block.appendChild(body);
        container.appendChild(block);
    });
}

function populateMulticlassTable(combinations) {
    const tbody = document.getElementById("multiclass-table-body");
    tbody.innerHTML = "";

    if (!combinations.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="3">No multiclass combinations found.</td>
            </tr>
        `;
        return;
    }

    combinations.forEach(combo => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${combo.class_a}</td>
            <td>${combo.class_b}</td>
            <td>${combo.count}</td>
        `;
        tbody.appendChild(tr);
    });
}

function populateMulticlassSankey(combinations) {
    const container = document.getElementById("multiclass-sankey-container");
    container.innerHTML = "";

    if (!combinations.length) {
        container.innerHTML = `<div class="empty-state">No multiclass combinations found.</div>`;
        return;
    }

    const maxCount = Math.max(...combinations.map(c => c.count), 1);

    combinations.forEach(combo => {
        const row = document.createElement("div");
        row.className = "sankey-row";

        const widthPercent = Math.max(10, (combo.count / maxCount) * 100);

        row.innerHTML = `
            <div class="sankey-labels">
                <span class="sankey-class">${combo.class_a}</span>
                <span class="sankey-arrow">→</span>
                <span class="sankey-class">${combo.class_b}</span>
            </div>
            <div class="sankey-bar-wrap">
                <div class="sankey-bar" style="width: ${widthPercent}%"></div>
                <span class="sankey-count">${combo.count}</span>
            </div>
        `;

        container.appendChild(row);
    });
}