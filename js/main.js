// Smooth scrolling for navigation links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Leaderboard filter functionality
const filterButtons = document.querySelectorAll('.filter-btn');
const leaderboardTable = document.querySelector('.leaderboard-table-full tbody');

// Sample data for different tasks (you can replace this with actual data)
const leaderboardData = {
    all: [
        { rank: 1, model: 'NMRMind +Formula', avg: 0.712, task1: 0.755, task2: '-', task3: '-', task4: '-', date: '2025-12' },
        { rank: 2, model: 'NMR2Struct', avg: 0.634, task1: 0.620, task2: 0.612, task3: '-', task4: '-', date: '2025-11' },
        { rank: 3, model: 'NMRNet', avg: 0.879, task1: '-', task2: '-', task3: '-', task4: 0.879, date: '2025-10' }
    ],
    task1: [
        { rank: 1, model: 'NMRMind +Formula', score: 0.755, metric: 'Top-1: 15.49%', date: '2025-12' },
        { rank: 2, model: 'NMR-Solver +Formula', score: 0.683, metric: 'Top-1: 12.41%', date: '2025-11' },
        { rank: 3, model: 'NMRMind', score: 0.651, metric: 'Top-1: 11.75%', date: '2025-11' }
    ],
    task2: [
        { rank: 1, model: 'NMR2Struct', score: 0.612, metric: 'Macro F1: 55.44%', date: '2025-11' },
        { rank: 2, model: 'XGBoost', score: 0.555, metric: 'Macro F1: 55.47%', date: '2025-10' },
        { rank: 3, model: 'Random Forest', score: 0.486, metric: 'Macro F1: 48.64%', date: '2025-10' }
    ],
    task3: [
        { rank: 1, model: 'CNN', score: 0.206, metric: 'Macro F1: 20.58%', date: '2025-10' },
        { rank: 2, model: 'MLP', score: 0.188, metric: 'Macro F1: 18.76%', date: '2025-10' },
        { rank: 3, model: 'XGBoost', score: 0.077, metric: 'Macro F1: 7.68%', date: '2025-10' }
    ],
    task4: [
        { rank: 1, model: 'NMRNet (¹³C)', score: 0.908, metric: 'Set Sim: 0.908', date: '2025-10' },
        { rank: 2, model: 'NMRNet (¹H)', score: 0.705, metric: 'Set Sim: 0.705', date: '2025-10' },
        { rank: 3, model: 'Cascade (¹³C)-DFTNN', score: 0.445, metric: 'Set Sim: 0.445', date: '2025-09' }
    ]
};

// Function to update leaderboard table
function updateLeaderboard(filter) {
    if (!leaderboardTable) return;

    const data = leaderboardData[filter] || leaderboardData.all;

    if (filter === 'all') {
        leaderboardTable.innerHTML = data.map(row => `
            <tr>
                <td>${row.rank}</td>
                <td>${row.model}</td>
                <td>${row.avg.toFixed(3)}</td>
                <td>${row.task1 === '-' ? '-' : row.task1.toFixed(3)}</td>
                <td>${row.task2 === '-' ? '-' : row.task2.toFixed(3)}</td>
                <td>${row.task3 === '-' ? '-' : row.task3.toFixed(3)}</td>
                <td>${row.task4 === '-' ? '-' : row.task4.toFixed(3)}</td>
                <td>${row.date}</td>
            </tr>
        `).join('');
    } else {
        // For individual tasks, show simplified table
        leaderboardTable.innerHTML = data.map(row => `
            <tr>
                <td>${row.rank}</td>
                <td>${row.model}</td>
                <td>${row.score.toFixed(3)}</td>
                <td colspan="3">${row.metric}</td>
                <td>${row.date}</td>
            </tr>
        `).join('');
    }
}

// Add click event listeners to filter buttons
filterButtons.forEach(button => {
    button.addEventListener('click', function() {
        // Remove active class from all buttons
        filterButtons.forEach(btn => btn.classList.remove('active'));

        // Add active class to clicked button
        this.classList.add('active');

        // Get filter value
        const filter = this.getAttribute('data-filter');

        // Update leaderboard
        updateLeaderboard(filter);
    });
});

// Scroll animations
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver(function(entries) {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, observerOptions);

// Observe elements for animation
document.addEventListener('DOMContentLoaded', function() {
    const animatedElements = document.querySelectorAll('.benchmark-card, .stat-item, .step, .task-detail');

    animatedElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
});

// Active navigation highlighting
window.addEventListener('scroll', function() {
    const sections = document.querySelectorAll('section[id]');
    const navLinks = document.querySelectorAll('.nav a[href^="#"]');

    let current = '';

    sections.forEach(section => {
        const sectionTop = section.offsetTop;
        const sectionHeight = section.clientHeight;

        if (window.pageYOffset >= sectionTop - 100) {
            current = section.getAttribute('id');
        }
    });

    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === '#' + current) {
            link.classList.add('active');
        }
    });
});

// Mobile menu toggle (for responsive design)
function createMobileMenu() {
    const header = document.querySelector('.header .container');
    const nav = document.querySelector('.nav');

    // Create hamburger button
    const menuBtn = document.createElement('button');
    menuBtn.className = 'mobile-menu-btn';
    menuBtn.innerHTML = '☰';
    menuBtn.style.display = 'none';
    menuBtn.style.fontSize = '1.5rem';
    menuBtn.style.background = 'none';
    menuBtn.style.border = 'none';
    menuBtn.style.cursor = 'pointer';
    menuBtn.style.color = 'var(--primary-color)';

    menuBtn.addEventListener('click', function() {
        nav.classList.toggle('mobile-active');
    });

    header.insertBefore(menuBtn, nav);

    // Add responsive styles
    const mediaQuery = window.matchMedia('(max-width: 768px)');

    function handleMobileMenu(e) {
        if (e.matches) {
            menuBtn.style.display = 'block';
            nav.style.display = 'none';
        } else {
            menuBtn.style.display = 'none';
            nav.style.display = 'flex';
            nav.classList.remove('mobile-active');
        }
    }

    mediaQuery.addListener(handleMobileMenu);
    handleMobileMenu(mediaQuery);
}

// Initialize mobile menu
document.addEventListener('DOMContentLoaded', createMobileMenu);

// Add dynamic table sorting (optional enhancement)
function makeSortable(table) {
    const headers = table.querySelectorAll('th');

    headers.forEach((header, index) => {
        header.style.cursor = 'pointer';
        header.addEventListener('click', function() {
            sortTable(table, index);
        });
    });
}

function sortTable(table, column) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));

    const sorted = rows.sort((a, b) => {
        const aValue = a.children[column].textContent;
        const bValue = b.children[column].textContent;

        // Try to parse as number
        const aNum = parseFloat(aValue);
        const bNum = parseFloat(bValue);

        if (!isNaN(aNum) && !isNaN(bNum)) {
            return bNum - aNum; // Descending for numbers
        }

        return aValue.localeCompare(bValue);
    });

    tbody.innerHTML = '';
    sorted.forEach(row => tbody.appendChild(row));
}

// Initialize sortable tables
document.addEventListener('DOMContentLoaded', function() {
    const tables = document.querySelectorAll('.leaderboard-table, .leaderboard-table-full');
    tables.forEach(makeSortable);
});

// Console welcome message
console.log('%c🧲 NMR Prediction Benchmark', 'color: #2563eb; font-size: 20px; font-weight: bold;');
console.log('%cWelcome to the NMR Prediction Benchmark suite!', 'color: #6b7280; font-size: 14px;');
console.log('%cFor more information, visit our GitHub repository.', 'color: #6b7280; font-size: 14px;');
