const API_BASE = '/api/admin';
let ADMIN_TOKEN = localStorage.getItem('oclus_admin_token') || 'oclus-admin-secret-123';
let CURRENT_SELECTED_DATE = new Date().toISOString().split('T')[0];

// Inicialização de Elementos
const tokenInput = document.getElementById('admin-token');
if (tokenInput) tokenInput.value = ADMIN_TOKEN;

const calendarPicker = document.getElementById('calendar-picker');
if (calendarPicker) calendarPicker.value = CURRENT_SELECTED_DATE;

function saveToken() {
    ADMIN_TOKEN = document.getElementById('admin-token').value;
    localStorage.setItem('oclus_admin_token', ADMIN_TOKEN);
    alert('🔐 Acesso Premium Validado!');
    location.reload();
}

async function apiFetch(endpoint, method = 'GET', body = null) {
    const headers = { 'X-Admin-Token': ADMIN_TOKEN };
    const config = { method, headers };
    
    if (body && !(body instanceof FormData)) {
        headers['Content-Type'] = 'application/json';
        config.body = JSON.stringify(body);
    } else if (body instanceof FormData) {
        config.body = body;
    }

    try {
        const response = await fetch(endpoint, config);
        if (response.status === 401) { 
            console.error("Token Inválido");
            return null; 
        }
        if (!response.ok) {
            console.error(`Erro na API: ${response.status}`);
            return null;
        }
        return await response.json();
    } catch (error) { 
        console.error("Erro de Rede:", error);
        return null; 
    }
}

// Controle de Data Robusto
function changeAgendaDate(date) {
    if (!date) return;
    CURRENT_SELECTED_DATE = date;
    
    // Formata a exibição da data de forma elegante
    const dateObj = new Date(date + 'T12:00:00');
    const options = { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' };
    document.getElementById('current-agenda-date').innerText = dateObj.toLocaleDateString('pt-BR', options);
    
    loadAgenda();
}

// Navegação entre Abas
function showTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
    const section = document.getElementById(`content-${tabName}`);
    if (section) section.classList.remove('hidden');
    
    // Estilo da sidebar
    document.querySelectorAll('nav button').forEach(el => el.classList.remove('sidebar-item-active'));
    const btn = document.getElementById(`tab-${tabName}`);
    if (btn) btn.classList.add('sidebar-item-active');

    if (tabName === 'agenda') loadAgenda();
    if (tabName === 'soap') loadSOAP();
    if (tabName === 'stats') loadStats();
    if (tabName === 'rag') loadRAGDocs();
}

// Agenda com Tratamento de Erros de Parsing
async function loadAgenda() {
    const container = document.getElementById('agenda-table-body');
    container.innerHTML = `
        <div class="flex flex-col items-center justify-center p-32">
            <div class="w-16 h-16 border-t-2 border-amber-500 rounded-full animate-spin mb-6"></div>
            <p class="text-[10px] font-black uppercase tracking-[0.4em] text-amber-500/50">Consultando Registros Nobres...</p>
        </div>`;
    
    try {
        const data = await apiFetch(`${API_BASE}/appointments?date=${CURRENT_SELECTED_DATE}`);
        
        if (!data || !data.data || data.data.length === 0) {
            container.innerHTML = `
                <div class="flex flex-col items-center justify-center p-32 glass rounded-[4rem] border-dashed border-2 border-white/5 opacity-40">
                    <i class="fas fa-calendar-minus text-4xl text-amber-900 mb-6"></i>
                    <p class="text-amber-500/40 font-black uppercase tracking-[0.3em] text-[10px]">Silêncio na Agenda para este Ciclo</p>
                </div>`;
            return;
        }

        container.innerHTML = data.data.map(appt => {
            // Tratamento seguro de data/hora
            let timeStr = "00:00";
            try {
                // Suporta "YYYY-MM-DD HH:MM:SS" ou formato ISO
                const dt = appt.appointment_datetime;
                timeStr = dt.includes(' ') ? dt.split(' ')[1].substring(0, 5) : dt.substring(11, 16);
            } catch (e) { console.warn("Erro ao processar hora:", e); }

            return `
                <div class="glass p-8 rounded-[2.5rem] flex items-center justify-between gold-glow border-white/5 transition-all group">
                    <div class="flex items-center gap-10">
                        <div class="text-3xl font-bold gold-text bg-amber-500/5 w-24 h-24 rounded-3xl flex items-center justify-center border border-amber-500/10 shadow-inner group-hover:scale-105 transition-transform">
                            ${timeStr}
                        </div>
                        <div>
                            <h4 class="text-2xl font-bold text-white mb-2 italic tracking-tight">${appt.patients?.name || 'Membro não identificado'}</h4>
                            <p class="text-[10px] text-amber-500/50 font-black uppercase tracking-widest flex items-center gap-2">
                                <i class="fab fa-whatsapp text-emerald-500"></i> ${appt.patients?.phone || 'N/A'}
                            </p>
                        </div>
                    </div>
                    <div class="flex items-center gap-12">
                        <div class="text-right hidden lg:block">
                            <p class="text-[9px] font-black text-amber-500/30 uppercase tracking-[0.2em] mb-1">Especialista Designado</p>
                            <p class="text-sm font-bold text-amber-100 italic">Dr(a). ${appt.doctor_name}</p>
                        </div>
                        <div class="px-6 py-3 rounded-2xl text-[9px] font-black tracking-[0.2em] shadow-2xl ${getStatusClass(appt.status)}">
                            ${appt.status.toUpperCase()}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    } catch (err) {
        container.innerHTML = `<p class="text-center p-20 text-red-500 font-bold uppercase text-xs">Erro Crítico ao Sincronizar Agenda: ${err.message}</p>`;
    }
}

function getStatusClass(status) {
    const classes = {
        'scheduled': 'text-amber-500 bg-amber-500/5 border border-amber-500/20',
        'confirmed': 'text-emerald-400 bg-emerald-500/10 border border-emerald-500/20',
        'cancelled': 'text-red-400 bg-red-400/10 border border-red-400/20',
        'completed': 'text-slate-500 bg-white/5 border border-white/10'
    };
    return classes[status] || 'text-slate-600 bg-slate-900';
}

// SOAP: Visualização Premium
async function loadSOAP() {
    const container = document.getElementById('soap-list');
    container.innerHTML = '<div class="col-span-full p-20 text-center animate-pulse text-amber-500/50 italic">Compilando Prontuários Elite...</div>';
    
    const data = await apiFetch(`${API_BASE}/soap_notes`);
    if (!data?.data?.length) {
        container.innerHTML = '<p class="col-span-full text-center p-20 text-slate-700 italic uppercase text-[10px] tracking-widest">Sem registros médicos ativos</p>';
        return;
    }

    container.innerHTML = data.data.map(note => `
        <div class="glass p-10 rounded-[3rem] gold-border gold-glow cursor-pointer group relative overflow-hidden" onclick="openSOAPModal(${JSON.stringify(note).replace(/"/g, '&quot;')})">
            <div class="flex justify-between items-start mb-8">
                <div class="w-14 h-14 bg-amber-500/5 rounded-2xl flex items-center justify-center text-amber-500 border border-amber-500/10">
                    <i class="fas fa-file-invoice-dollar"></i>
                </div>
                ${note.signed ? 
                    '<span class="text-[8px] font-black bg-emerald-600 text-white px-3 py-1 rounded-full shadow-lg">ASSINADO</span>' : 
                    '<span class="text-[8px] font-black bg-amber-500 text-black px-3 py-1 rounded-full shadow-lg">PENDENTE</span>'}
            </div>
            <h3 class="text-2xl font-bold text-white mb-2 italic tracking-tight">${note.patients?.name || 'Paciente'}</h3>
            <p class="text-[9px] text-amber-500/40 font-black mb-6 uppercase tracking-widest">${new Date(note.created_at).toLocaleDateString('pt-BR')} • Dr. ${note.doctor_name}</p>
            <div class="h-px w-full bg-white/5 mb-6"></div>
            <p class="text-sm text-slate-400 line-clamp-2 italic opacity-60 font-medium">"${note.assessment}"</p>
        </div>
    `).join('');
}

function openSOAPModal(note) {
    const content = document.getElementById('modal-content');
    content.innerHTML = `
        <div class="grid grid-cols-2 gap-12 bg-white/5 p-12 rounded-[3rem] border border-white/5 shadow-inner">
            <div><p class="text-[9px] font-black text-amber-500/40 uppercase tracking-[0.3em] mb-2">Membro Responsável</p><p class="text-2xl font-bold text-white italic">${note.patients?.name}</p></div>
            <div><p class="text-[9px] font-black text-amber-500/40 uppercase tracking-[0.3em] mb-2">Especialista Atendente</p><p class="text-2xl font-bold text-white italic">Dr. ${note.doctor_name}</p></div>
        </div>
        <div class="space-y-10">
            ${['S - Subjetivo', 'O - Objetivo', 'A - Avaliação', 'P - Plano'].map((label, i) => `
                <div class="group">
                    <p class="text-[10px] font-black text-amber-500 uppercase tracking-[0.2em] mb-4 flex items-center gap-3">
                        <span class="w-1.5 h-1.5 gold-gradient rounded-full shadow-[0_0_8px_#bf953f]"></span> ${label}
                    </p>
                    <div class="p-8 glass rounded-[2rem] border-white/5 text-slate-300 leading-relaxed text-base italic font-light shadow-2xl">
                        ${[note.subjective, note.objective, note.assessment, note.plan][i] || 'Nenhuma informação registrada.'}
                    </div>
                </div>
            `).join('')}
        </div>
    `;
    
    const btn = document.getElementById('btn-sign-confirm');
    btn.style.display = note.signed ? 'none' : 'block';
    btn.onclick = () => signSOAP(note.id);
    document.getElementById('soap-modal').classList.remove('hidden');
}

function closeModal() { document.getElementById('soap-modal').classList.add('hidden'); }

async function signSOAP(id) {
    if (!confirm('Deseja autenticar digitalmente este registro?')) return;
    const result = await apiFetch(`${API_BASE}/soap_notes/${id}/sign`, 'POST');
    if (result?.success) { closeModal(); loadSOAP(); }
}

// RAG: Indexação com Estética Premium
async function uploadFile(event) {
    event.preventDefault();
    const fileInput = document.getElementById('document-file');
    const statusDiv = document.getElementById('upload-status');
    const submitBtn = event.target.querySelector('button');
    
    if (!fileInput.files[0]) return;

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);

    statusDiv.classList.remove('hidden');
    statusDiv.classList.add('text-amber-500');
    submitBtn.disabled = true;

    const xhr = new XMLHttpRequest();
    xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
            const percent = Math.round((e.loaded / e.total) * 100);
            statusDiv.innerHTML = `<i class="fas fa-sync fa-spin mr-3"></i> Expandindo Inteligência: ${percent}%`;
        }
    };

    xhr.onload = function() {
        submitBtn.disabled = false;
        if (xhr.status >= 200 && xhr.status < 300) {
            const result = JSON.parse(xhr.responseText);
            statusDiv.innerHTML = `<i class="fas fa-check-circle mr-3"></i> ${result.message}`;
            statusDiv.classList.replace('text-amber-500', 'text-emerald-500');
            fileInput.value = '';
            loadRAGDocs();
        } else {
            statusDiv.innerHTML = `❌ Erro na Sincronização (${xhr.status})`;
            statusDiv.classList.replace('text-amber-500', 'text-red-500');
        }
    };

    xhr.open("POST", `${API_BASE}/documents`);
    xhr.setRequestHeader("X-Admin-Token", ADMIN_TOKEN);
    xhr.send(formData);
}

async function loadRAGDocs() {
    const container = document.getElementById('rag-documents-list');
    const data = await apiFetch(`${API_BASE}/documents_list`);
    
    if (!data?.data?.length) {
        container.innerHTML = '<p class="text-slate-800 italic text-[10px] font-black uppercase tracking-[0.4em] text-center py-20">Arquivos de saber ausentes</p>';
        return;
    }

    container.innerHTML = data.data.map(doc => `
        <div class="glass p-6 rounded-3xl flex justify-between items-center group gold-glow transition-all">
            <div class="flex items-center gap-6">
                <div class="w-12 h-12 bg-amber-500/5 rounded-2xl flex items-center justify-center border border-amber-500/10">
                    <i class="fas ${doc.filename.endsWith('.pdf') ? 'fa-file-pdf text-red-400' : 'fa-file-alt text-amber-500'}"></i>
                </div>
                <span class="text-base font-bold text-white italic tracking-tight">${doc.filename}</span>
            </div>
            <div class="flex items-center gap-4">
                 <span class="text-[8px] font-black text-amber-500/40 uppercase tracking-widest">${new Date(doc.uploaded_at).toLocaleDateString('pt-BR')}</span>
                 <i class="fas fa-check-double text-[10px] text-emerald-500 opacity-20 group-hover:opacity-100 transition-opacity"></i>
            </div>
        </div>
    `).join('');
}

async function loadStats() {
    const data = await apiFetch(`${API_BASE}/stats`);
    if (!data?.data) return;
    document.getElementById('stat-avg').innerText = data.data.average;
    document.getElementById('stat-nps').innerText = data.data.nps;
    document.getElementById('stat-total').innerText = data.data.total;
    
    const starsDiv = document.getElementById('stat-stars');
    starsDiv.innerHTML = '<i class="fas fa-star text-amber-500 text-xs"></i>'.repeat(Math.floor(data.data.average)) + 
                         (data.data.average % 1 >= 0.5 ? '<i class="fas fa-star-half-alt text-amber-500 text-xs"></i>' : '');
}

async function checkHealth() {
    try {
        const response = await fetch('/api/health');
        const data = await response.json();
        const setStatus = (id, status) => {
            const el = document.getElementById(id);
            if (!el) return;
            const dot = el.querySelector('span');
            dot.className = `w-1.5 h-1.5 rounded-full transition-all duration-1000 ${status === 'online' ? 'bg-emerald-500 shadow-[0_0_12px_#10b981]' : 'bg-red-900 shadow-[0_0_12px_#7f1d1d]'}`;
        };
        setStatus('status-db', data.services.database.status);
        setStatus('status-openai', data.services.openai.status);
        setStatus('status-waha', data.services.waha.status);
    } catch (e) {}
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    showTab('agenda');
    checkHealth();
    setInterval(checkHealth, 15000);
    const form = document.getElementById('upload-form');
    if (form) form.addEventListener('submit', uploadFile);
    
    // Set initial date display
    changeAgendaDate(CURRENT_SELECTED_DATE);
});
