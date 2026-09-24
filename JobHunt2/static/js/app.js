document.addEventListener('DOMContentLoaded', () => {
    fetchJobs();
    fetchCVs();

    // Setup polling every 30 seconds
    setInterval(() => {
        fetchJobs();
        fetchCVs();
    }, 30000);

    // Event Listeners
    document.getElementById('run-pipeline-btn').addEventListener('click', triggerPipeline);
    
    // CV Upload Logic
    document.getElementById('upload-cv-btn').addEventListener('click', () => {
        document.getElementById('cv-upload-input').click();
    });
    document.getElementById('cv-upload-input').addEventListener('change', handleCVUpload);
    
    document.getElementById('close-modal').addEventListener('click', closeModal);
    document.getElementById('draft-modal').addEventListener('click', (e) => {
        if (e.target === document.getElementById('draft-modal')) {
            closeModal();
        }
    });
});

async function fetchCVs() {
    try {
        const response = await fetch('/api/cvs');
        const data = await response.json();
        
        const container = document.getElementById('active-cvs-container');
        const list = document.getElementById('active-cvs-list');
        
        if (data.cvs && data.cvs.length > 0) {
            container.style.display = 'block';
            list.innerHTML = data.cvs.map(cv => `
                <div style="background: rgba(96, 165, 250, 0.1); border: 1px solid rgba(96, 165, 250, 0.3); color: #60a5fa; padding: 5px 12px; border-radius: 20px; font-size: 0.85rem; display: flex; align-items: center; gap: 6px;">
                    📄 ${cv.filename}
                </div>
            `).join('');
        } else {
            container.style.display = 'none';
        }
    } catch (error) {
        console.error("Error fetching CVs:", error);
    }
}

async function fetchJobs() {
    try {
        const response = await fetch('/api/jobs');
        const data = await response.json();
        renderBoard(data.jobs || []);
        updateStats(data.jobs || []);
    } catch (error) {
        console.error("Error fetching jobs:", error);
    }
}

function renderBoard(jobs) {
    const cols = {
        'DISCOVERED': document.getElementById('col-discovered'),
        'SCREENED': document.getElementById('col-screened'),
        'HIGH MATCH AWAITING RESEARCH': document.getElementById('col-highmatch'),
        'HIGH MATCH': document.getElementById('col-highmatch'),
        'APPLICATION READY (AWAITING APPROVAL)': document.getElementById('col-ready')
    };

    // Clear all columns
    Object.values(cols).forEach(col => {
        if(col) col.innerHTML = '';
    });

    // Sort jobs by Match Score (descending)
    jobs.sort((a, b) => (b['Match Score'] || 0) - (a['Match Score'] || 0));

    jobs.forEach(job => {
        const card = createJobCard(job);
        
        let targetCol = cols[job.Status];
        // If status doesn't exactly match, try to guess or put in discovered
        if (!targetCol) {
             if (job.Status.includes('READY')) targetCol = cols['APPLICATION READY (AWAITING APPROVAL)'];
             else if (job.Status.includes('SCREENED')) targetCol = cols['SCREENED'];
             else targetCol = cols['DISCOVERED'];
        }

        if (targetCol) {
            targetCol.appendChild(card);
        }
    });
}

function createJobCard(job) {
    const div = document.createElement('div');
    div.className = 'job-card';
    
    let matchTag = '';
    if (job.Match === 'HIGH MATCH') matchTag = '<span class="tag high-match">High Match</span>';
    else if (job.Match === 'POSSIBLE MATCH') matchTag = '<span class="tag possible-match">Possible</span>';
    else if (job.Match === 'REJECT') matchTag = '<span class="tag reject">Reject</span>';

    div.innerHTML = `
        <div class="company">${job.Company || 'Unknown Company'}</div>
        <div class="position">${job.Position || 'Unknown Role'}</div>
        <div class="meta">
            <span>${job.Location || 'Remote'}</span>
            ${matchTag}
        </div>
        ${job['Match Score'] ? `<div style="font-size: 0.75rem; color: #60a5fa; margin-top: 5px;">⭐ Match Score: ${job['Match Score']}/100</div>` : ''}
    `;

    // Allow clicking on ALL cards to view details
    div.style.cursor = 'pointer';
    div.addEventListener('click', () => openJobDetails(job));

    return div;
}

function updateStats(jobs) {
    document.getElementById('stat-total').textContent = jobs.length;
    const highMatches = jobs.filter(j => j.Match === 'HIGH MATCH').length;
    document.getElementById('stat-high').textContent = highMatches;
}

async function triggerPipeline() {
    const btn = document.getElementById('run-pipeline-btn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '⚡ Running...';
    btn.disabled = true;

    try {
        await fetch('/api/trigger', { method: 'POST' });
        // Poll quickly for a few seconds to see immediate updates
        let polls = 0;
        const interval = setInterval(() => {
            fetchJobs();
            polls++;
            if (polls > 10) clearInterval(interval); // Poll for ~20 seconds
        }, 2000);
    } catch (error) {
        console.error("Error triggering pipeline:", error);
    } finally {
        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }, 3000);
    }
}

async function openJobDetails(job) {
    const modal = document.getElementById('draft-modal');
    const title = document.getElementById('modal-title');
    const content = document.getElementById('modal-draft-content');

    title.textContent = `${job.Position} at ${job.Company}`;
    
    let html = `
        <div style="margin-bottom: 20px;">
            <strong>Location:</strong> ${job.Location}<br>
            <strong>Salary:</strong> ${job.Salary || 'Not Specified'}<br>
            <strong>Match Score:</strong> ${job['Match Score'] || 0}/100<br>
            <strong>Link:</strong> <a href="${job.URL}" target="_blank" style="color: #60a5fa;">View Original Job Post</a>
        </div>
        <div style="margin-bottom: 20px; background: rgba(0,0,0,0.2); padding: 15px; border-radius: 8px;">
            <h4 style="margin-top: 0;">Job Description / Requirements</h4>
            <p style="white-space: pre-wrap; font-size: 0.9rem;">${job['Experience Required'] || 'No description available.'}</p>
        </div>
    `;
    
    content.innerHTML = html;
    modal.classList.add('active');
    
    if (job.Status === 'APPLICATION READY (AWAITING APPROVAL)' || job.Status === 'HIGH MATCH AWAITING RESEARCH') {
        content.innerHTML += `<div id="draft-loading" style="margin-top:20px;"><em>Loading AI Drafts...</em></div>`;
        try {
            const response = await fetch(`/api/job/${job.id}/draft`);
            const data = await response.json();
            const loading = document.getElementById('draft-loading');
            if (loading) loading.remove();
            
            if (data.status === 'success') {
                content.innerHTML += `
                    <div style="margin-bottom: 20px;">
                        <h4>AI Drafted Cover Letter</h4>
                        <pre style="white-space: pre-wrap; font-family: inherit; font-size: 0.85rem; background: rgba(0,0,0,0.2); padding: 15px; border-radius: 8px;">${data.cover_letter}</pre>
                    </div>
                    <div>
                        <h4>AI Tailored CV</h4>
                        <pre style="white-space: pre-wrap; font-family: inherit; font-size: 0.85rem; background: rgba(0,0,0,0.2); padding: 15px; border-radius: 8px;">${data.cv}</pre>
                    </div>
                `;
            }
        } catch (error) {
            console.error("Error loading drafts", error);
        }
    }
}

function closeModal() {
    document.getElementById('draft-modal').classList.remove('active');
}

async function handleCVUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const btn = document.getElementById('upload-cv-btn');
    const originalText = btn.innerHTML;
    btn.innerHTML = 'Uploading...';

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/upload_cv', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        
        if (result.status === 'success') {
            btn.innerHTML = '<span class="btn-icon">✅</span> Uploaded';
            fetchCVs(); // Refresh the CV list immediately
        } else {
            btn.innerHTML = '❌ Error';
            console.error(result.message);
        }
    } catch (error) {
        console.error("Upload failed", error);
        btn.innerHTML = '❌ Error';
    } finally {
        setTimeout(() => {
            btn.innerHTML = originalText;
            event.target.value = ''; // Reset input
        }, 3000);
    }
}
