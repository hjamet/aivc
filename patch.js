let gitLogOffset = 0;
const gitLogLimit = 15;
let isFetchingLog = false;
let hasMoreLog = true;
let currentSidebarMode = 'log'; // 'log', 'search', 'file'

async function loadGitLog(append = false) {
    if (isFetchingLog || (!hasMoreLog && append)) return;
    isFetchingLog = true;
    
    if (!append) {
        gitLogOffset = 0;
        hasMoreLog = true;
        resultsContent.innerHTML = '<div style="text-align:center; padding: 20px;"><div class="spinner" style="display:inline-block;"></div></div>';
    }

    try {
        const res = await fetch(`/api/log?offset=${gitLogOffset}&limit=${gitLogLimit}`);
        const commits = await res.json();
        
        if (commits.length < gitLogLimit) hasMoreLog = false;
        gitLogOffset += commits.length;

        const html = commits.map(c => `
            <div class="commit-card" data-commit-id='${c.id}'>
                <h3 class="commit-title">${c.title}</h3>
                <div class="commit-meta">
                    <span>${c.timestamp.substring(0,10)}</span>
                    <span style="font-family: monospace;">${c.id.substring(0,8)}</span>
                </div>
                <div class="commit-files">${c.file_count} fichier(s) modifié(s)</div>
            </div>
        `).join('');

        if (append) {
            resultsContent.insertAdjacentHTML('beforeend', html);
        } else {
            resultsTitle.innerText = "Git Log";
            resultsContent.innerHTML = html;
        }

        // Bind clicks
        document.querySelectorAll('.commit-card:not(.bound)').forEach(card => {
            card.classList.add('bound');
            card.addEventListener('click', async () => {
                const commitId = card.getAttribute('data-commit-id');
                await showCommitDetail(commitId);
            });
        });

    } catch (err) {
        if (!append) resultsContent.innerHTML = `<p style="color: #ff7b72;">Erreur: ${err.message}</p>`;
    } finally {
        isFetchingLog = false;
    }
}

async function showFileHistory(nodeId) {
    currentSidebarMode = 'file';
    resultsTitle.innerText = 'Historique fichier';
    resultsContent.innerHTML = '<div style="text-align:center; padding: 20px;"><div class="spinner" style="display:inline-block;"></div></div>';
    sidebar.classList.add('open');

    try {
        const res = await fetch(`/api/file-history/${encodeURIComponent(nodeId)}`);
        const history = await res.json();

        if (history.error) {
            resultsContent.innerHTML = `<p style="color: #ff7b72;">${history.error}</p>`;
            return;
        }

        const filename = nodeId.split('/').pop();
        resultsTitle.innerHTML = `<div style="font-size: 14px; word-break: break-all; color: var(--highlight);">${filename}</div>`;
        
        resultsContent.innerHTML = `
            <button class="commit-detail-back" id="backToLog">← Retour au Git Log</button>
            <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 12px;">${history.length} commit(s)</div>
            ${history.map(c => `
                <div class="commit-card" data-commit-id='${c.commit_id}'>
                    <h3 class="commit-title">${c.title}</h3>
                    <div class="commit-meta">
                        <span>${c.timestamp.substring(0,10)}</span>
                        <span style="font-family: monospace;">${c.commit_id.substring(0,8)}</span>
                    </div>
                </div>
            `).join('')}
        `;

        document.getElementById('backToLog').addEventListener('click', () => {
            currentSidebarMode = 'log';
            loadGitLog(false);
        });

        document.querySelectorAll('.commit-card').forEach(card => {
            card.addEventListener('click', async () => {
                const commitId = card.getAttribute('data-commit-id');
                await showCommitDetail(commitId);
            });
        });

    } catch (err) {
        resultsContent.innerHTML = `<p style="color: #ff7b72;">Erreur: ${err.message}</p>`;
    }
}
