// Load stats
fetch('/api/stats')
.then(res => res.json())
.then(data => {
    document.getElementById('characters').innerText = `${data.characters} Characters`;
    document.getElementById('players').innerText = `${data.players} Players`;
    document.getElementById('classes').innerText = `${data.classes} Classes`;
});

// Load sessions
fetch('/api/sessions')
.then(res => res.json())
.then(data => {
    const ul = document.getElementById('sessions');
    ul.innerHTML = "";

    data.forEach(s => {
        let li = document.createElement('li');

        let a = document.createElement('a');
        a.href = `/session/${s.id}`;
        a.innerText = s.name;

        li.appendChild(a);
        ul.appendChild(li);
    });
});

// Search
document.getElementById('search').addEventListener('input', function() {
    let q = this.value.trim();
    let container = document.getElementById('search-results');

    if (q.length < 2) {
        container.innerHTML = "";
        return;
    }

    fetch(`/api/search?q=${encodeURIComponent(q)}`)
    .then(res => res.json())
    .then(data => {
        container.innerHTML = "";

        if (!data.length) {
            container.innerHTML = `<div class="result">No results found</div>`;
            return;
        }

        data.forEach(r => {
            let a = document.createElement('a');
            a.className = "result result-link";
            a.href = r.url;
            a.innerText = `${r.name} [${r.type}]`;

            container.appendChild(a);
        });
    });
});

document.addEventListener("click", function(event) {
    const searchBox = document.getElementById("search");
    const resultsBox = document.getElementById("search-results");

    if (!searchBox.contains(event.target) && !resultsBox.contains(event.target)) {
        resultsBox.innerHTML = "";
    }
});

fetch('/api/class-distribution')
.then(res => res.json())
.then(data => {

    const ctx = document.getElementById('classChart');

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Characters per Class',
                data: data.values,
                backgroundColor: '#66bb6a',
                borderColor: '#2e7d32',
                borderWidth: 2,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    labels: {
                        color: '#333'
                    }
                }
            },
            scales: {
                x: {
                    ticks: { color: '#333' }
                },
                y: {
                    ticks: { color: '#333' },
                    beginAtZero: true
                }
            }
        }
    });

});
