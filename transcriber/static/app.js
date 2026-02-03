// Video Transcriber Frontend

const API_BASE = '/api';

// Elements
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const youtubeUrl = document.getElementById('youtubeUrl');
const transcribeUrlBtn = document.getElementById('transcribeUrlBtn');
const modelSelect = document.getElementById('modelSelect');
const langSelect = document.getElementById('langSelect');
const timestampsCheck = document.getElementById('timestampsCheck');
const progressSection = document.getElementById('progressSection');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const resultSection = document.getElementById('resultSection');
const resultText = document.getElementById('resultText');
const copyBtn = document.getElementById('copyBtn');
const downloadMdBtn = document.getElementById('downloadMdBtn');
const downloadSrtBtn = document.getElementById('downloadSrtBtn');
const historyList = document.getElementById('historyList');

let currentTranscriptionId = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadHistory();
    setupEventListeners();
});

function setupEventListeners() {
    // Drag and drop
    dropZone.addEventListener('click', () => fileInput.click());
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileUpload(files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });

    // YouTube URL
    transcribeUrlBtn.addEventListener('click', () => {
        const url = youtubeUrl.value.trim();
        if (url) {
            handleYoutubeUrl(url);
        }
    });

    youtubeUrl.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            transcribeUrlBtn.click();
        }
    });

    // Result actions
    copyBtn.addEventListener('click', copyText);
    downloadMdBtn.addEventListener('click', () => downloadFile('md'));
    downloadSrtBtn.addEventListener('click', () => downloadFile('srt'));
}

async function handleFileUpload(file) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('model', modelSelect.value);
    formData.append('language', langSelect.value);
    formData.append('include_timestamps', timestampsCheck.checked);

    await startTranscription(formData);
}

async function handleYoutubeUrl(url) {
    const formData = new FormData();
    formData.append('youtube_url', url);
    formData.append('model', modelSelect.value);
    formData.append('language', langSelect.value);
    formData.append('include_timestamps', timestampsCheck.checked);

    await startTranscription(formData);
}

async function startTranscription(formData) {
    try {
        showProgress();

        const response = await fetch(`${API_BASE}/transcriptions`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to start transcription');
        }

        const data = await response.json();
        currentTranscriptionId = data.id;

        // Start listening for progress
        listenForProgress(data.id);

    } catch (error) {
        showError(error.message);
    }
}

function listenForProgress(transcriptionId) {
    const eventSource = new EventSource(`${API_BASE}/transcriptions/${transcriptionId}/events`);

    eventSource.addEventListener('progress', (e) => {
        const data = JSON.parse(e.data);
        updateProgress(data.progress, data.status);

        if (data.status === 'completed') {
            eventSource.close();
            loadTranscriptionResult(transcriptionId);
        } else if (data.status === 'failed') {
            eventSource.close();
            showError(data.error || 'Transcription failed');
        }
    });

    eventSource.onerror = () => {
        eventSource.close();
        // Fallback: poll for status
        pollTranscriptionStatus(transcriptionId);
    };
}

async function pollTranscriptionStatus(transcriptionId) {
    const interval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE}/transcriptions/${transcriptionId}`);
            const data = await response.json();

            updateProgress(data.progress, data.status);

            if (data.status === 'completed') {
                clearInterval(interval);
                showResult(data.text);
                loadHistory();
            } else if (data.status === 'failed') {
                clearInterval(interval);
                showError(data.error_message || 'Transcription failed');
            }
        } catch (error) {
            clearInterval(interval);
            showError('Failed to get transcription status');
        }
    }, 1000);
}

async function loadTranscriptionResult(transcriptionId) {
    try {
        const response = await fetch(`${API_BASE}/transcriptions/${transcriptionId}`);
        const data = await response.json();
        showResult(data.text);
        loadHistory();
    } catch (error) {
        showError('Failed to load transcription result');
    }
}

function showProgress() {
    progressSection.hidden = false;
    resultSection.hidden = true;
    updateProgress(0, 'pending');
}

function updateProgress(progress, status) {
    progressFill.style.width = `${progress}%`;

    const statusMessages = {
        pending: 'Waiting to start...',
        downloading: 'Downloading video...',
        processing: `Transcribing... ${progress}%`,
        completed: 'Completed!',
        failed: 'Failed',
    };

    progressText.textContent = statusMessages[status] || `Processing... ${progress}%`;
}

function showResult(text) {
    progressSection.hidden = true;
    resultSection.hidden = false;
    resultText.textContent = text;
}

function showError(message) {
    progressSection.hidden = true;
    alert(`Error: ${message}`);
}

async function copyText() {
    try {
        await navigator.clipboard.writeText(resultText.textContent);
        copyBtn.textContent = 'Copied!';
        setTimeout(() => {
            copyBtn.textContent = 'Copy Text';
        }, 2000);
    } catch (error) {
        alert('Failed to copy text');
    }
}

async function downloadFile(format) {
    if (!currentTranscriptionId) return;

    window.location.href = `${API_BASE}/transcriptions/${currentTranscriptionId}/download?format=${format}`;
}

async function loadHistory() {
    try {
        const response = await fetch(`${API_BASE}/transcriptions`);
        const data = await response.json();

        if (data.items.length === 0) {
            historyList.innerHTML = '<p class="empty-history">No transcriptions yet</p>';
            return;
        }

        historyList.innerHTML = data.items.map(item => `
            <div class="history-item" data-id="${item.id}">
                <div class="history-item-info">
                    <div class="history-item-title">${escapeHtml(item.source_name)}</div>
                    <div class="history-item-meta">
                        ${formatDate(item.created_at)} -
                        ${formatDuration(item.duration_seconds)}
                        <span class="status-badge status-${item.status}">${item.status}</span>
                    </div>
                </div>
                <div class="history-item-actions">
                    ${item.status === 'completed' ? `
                        <button onclick="viewTranscription('${item.id}')">View</button>
                        <button onclick="deleteTranscription('${item.id}')">Delete</button>
                    ` : ''}
                </div>
            </div>
        `).join('');

    } catch (error) {
        console.error('Failed to load history:', error);
    }
}

async function viewTranscription(id) {
    try {
        const response = await fetch(`${API_BASE}/transcriptions/${id}`);
        const data = await response.json();
        currentTranscriptionId = id;
        showResult(data.text);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (error) {
        alert('Failed to load transcription');
    }
}

async function deleteTranscription(id) {
    if (!confirm('Delete this transcription?')) return;

    try {
        await fetch(`${API_BASE}/transcriptions/${id}`, { method: 'DELETE' });
        loadHistory();
    } catch (error) {
        alert('Failed to delete transcription');
    }
}

// Utilities
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(isoString) {
    const date = new Date(isoString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatDuration(seconds) {
    if (!seconds) return '';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}
