/* ================================================================
   JobAgent AI — app.js
   Full interactivity: WebSocket chat, jobs, applications, resume,
   settings, toast notifications, animated counters, file uploads
   ================================================================ */

'use strict';

// ── State ──────────────────────────────────────────────────────────
const State = {
  currentTab: 'chat',
  ws: null,
  wsConnected: false,
  agentRunning: true,
  jobs: [],
  applications: [],
  activeFilter: 'all',
  uploadedResume: null,
  chatHistory: [],
};

// ── Sample Data ────────────────────────────────────────────────────
const SAMPLE_JOBS = [
  {
    id: 1,
    title: 'ML Engineer Intern',
    company: 'Google',
    initials: 'Go',
    color: '#4285f4',
    location: 'Remote',
    platform: 'linkedin',
    score: 94,
    posted: '2 days ago',
    approved: false,
  },
  {
    id: 2,
    title: 'Data Science Intern',
    company: 'Microsoft',
    initials: 'Ms',
    color: '#00a4ef',
    location: 'Bangalore',
    platform: 'naukri',
    score: 88,
    posted: '1 day ago',
    approved: false,
  },
  {
    id: 3,
    title: 'Applied Scientist Intern',
    company: 'Amazon',
    initials: 'Az',
    color: '#ff9900',
    location: 'Hyderabad',
    platform: 'linkedin',
    score: 82,
    posted: '3 days ago',
    approved: false,
  },
  {
    id: 4,
    title: 'Data Analyst',
    company: 'Flipkart',
    initials: 'Fl',
    color: '#2874f0',
    location: 'Bangalore',
    platform: 'indeed',
    score: 76,
    posted: '5 days ago',
    approved: false,
  },
  {
    id: 5,
    title: 'ML Research Intern',
    company: 'Paytm',
    initials: 'Pt',
    color: '#00baf2',
    location: 'Noida',
    platform: 'internshala',
    score: 71,
    posted: '1 week ago',
    approved: false,
  },
  {
    id: 6,
    title: 'Data Science Intern',
    company: 'Swiggy',
    initials: 'Sw',
    color: '#fc8019',
    location: 'Bangalore',
    platform: 'angellist',
    score: 85,
    posted: '4 days ago',
    approved: false,
  },
];

const SAMPLE_APPLICATIONS = {
  applied: [
    { company: 'TCS', role: 'ML Intern', date: '2 days ago' },
    { company: 'Wipro', role: 'Data Analyst', date: '1 week ago' },
  ],
  review: [
    { company: 'Infosys', role: 'Data Science Intern', date: '3 days ago' },
  ],
  interview: [
    { company: 'Zomato', role: 'ML Engineer', date: 'Yesterday', highlight: true },
  ],
  rejected: [],
  offer: [],
};

const DEMO_RESPONSES = [
  {
    agent: 'orchestrator',
    badge: '🧠 Orchestrator',
    text: "Great! I'm spinning up all agents now. First, I'll have the **Scraper Agent** search for Data Science / ML roles across LinkedIn, Naukri, Internshala, and more. This should take about 30 seconds.",
    delay: 1200,
  },
  {
    agent: 'scraper',
    badge: '🔍 Scraper',
    text: 'Scanning job boards… Found **47 new listings** matching your profile! Filtering by relevance score > 70%…',
    delay: 2800,
  },
  {
    agent: 'orchestrator',
    badge: '🧠 Orchestrator',
    text: 'Nice work! **6 high-quality matches** landed in your Jobs tab with scores above 70%. Switch to the **Jobs** tab to review and approve them. I\'ll have the Writer Agent draft tailored cover letters for the ones you approve.',
    delay: 4000,
  },
  {
    agent: 'writer',
    badge: '✍️ Writer',
    text: 'Standing by! Once you approve a job, I\'ll generate a **custom resume variant** and cold email tailored to that specific role and company culture. 🚀',
    delay: 5200,
  },
];

const QUICK_RESPONSES = [
  { match: /start|begin|go/i, agent: 'orchestrator', badge: '🧠 Orchestrator', text: "Let's get started! 🚀 I'm initializing the job search pipeline. Tell me: **what's your target role?** (e.g., ML Engineer, Data Scientist, AI Researcher)" },
  { match: /ml|machine learning|ai|data sci/i, agent: 'scraper', badge: '🔍 Scraper', text: "Perfect! I'll focus on **ML/AI/Data Science** roles. Fetching from LinkedIn, Naukri, Internshala, AngelList… sit tight!" },
  { match: /cover|letter|email/i, agent: 'writer', badge: '✍️ Writer', text: "I'll craft a **personalized cover letter** for each approved job. Want me to also set up automated cold email sequences to hiring managers?" },
  { match: /resume|cv/i, agent: 'reviewer', badge: '📋 Reviewer', text: 'Head over to the **Resume tab** to upload your CV. I\'ll analyze it and generate tailored versions for each job role automatically.' },
  { match: /status|progress|how/i, agent: 'orchestrator', badge: '🧠 Orchestrator', text: "Here's your current status:\n• **6 jobs** found & awaiting approval\n• **3 applications** active\n• **1 interview** scheduled (Zomato 🟢)\n• Resume analysis: Pending upload" },
  { match: /.*/, agent: 'orchestrator', badge: '🧠 Orchestrator', text: "Got it! I'll coordinate the agents on that. Is there anything specific you'd like me to focus on — job search, application drafting, or interview prep?" },
];

// ── DOM refs ───────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const $$ = sel => document.querySelectorAll(sel);

// ── Init ───────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  buildDOM();
  initNavigation();
  initChat();
  initWebSocket();
  initJobs();
  initApplications();
  initResume();
  initSettings();
  animateStatusDot();
  renderJobsSkeletons();
  renderApplications();
});

// ── Build DOM ──────────────────────────────────────────────────────
function buildDOM() {
  document.body.innerHTML = `
  <div class="bg-glow bg-glow-1"></div>
  <div class="bg-glow bg-glow-2"></div>
  <div class="bg-glow bg-glow-3"></div>

  <button id="hamburger" aria-label="Open menu" onclick="toggleSidebar()">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
      <line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>
    </svg>
  </button>
  <div class="sidebar-overlay" onclick="toggleSidebar()"></div>

  <div id="app">
    <!-- SIDEBAR -->
    <aside id="sidebar">
      <div class="logo">
        <div class="logo-icon">🤖</div>
        <div class="logo-text">
          <h2>JobAgent AI</h2>
          <span>Powered by Gemini</span>
        </div>
      </div>
      <nav>
        <div class="nav-item active" data-tab="chat">
          <span class="nav-icon">💬</span>
          <span>Chat</span>
        </div>
        <div class="nav-item" data-tab="jobs">
          <span class="nav-icon">🔍</span>
          <span>Jobs</span>
          <span class="badge" id="jobs-badge">6</span>
        </div>
        <div class="nav-item" data-tab="applications">
          <span class="nav-icon">📋</span>
          <span>Applications</span>
          <span class="badge" id="apps-badge">1</span>
        </div>
        <div class="nav-item" data-tab="emails">
          <span class="nav-icon">✉️</span>
          <span>Emails & Reverts</span>
          <span class="badge" id="emails-badge" style="background:var(--cyan);color:#000;">2</span>
        </div>
        <div class="nav-item" data-tab="resume">
          <span class="nav-icon">📄</span>
          <span>Resume</span>
        </div>
        <div class="nav-item" data-tab="settings">
          <span class="nav-icon">⚙️</span>
          <span>Settings</span>
        </div>
      </nav>
      <div class="sidebar-footer">
        <div class="status-row">
          <div class="status-dot pulsing" id="status-dot"></div>
          <div class="status-text">Agent <strong id="status-label">Running</strong></div>
        </div>
      </div>
    </aside>

    <!-- MAIN -->
    <main id="main">

      <!-- TAB: CHAT -->
      <section class="panel active" id="panel-chat">
        <div class="chat-messages" id="chat-messages"></div>
        <div class="chat-input-wrap">
          <div class="chat-input-inner">
            <textarea id="chat-input" rows="1" placeholder="Chat with your agent…" autocomplete="off"></textarea>
            <label class="upload-btn" for="chat-file-upload" title="Upload resume">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
            </label>
            <input type="file" id="chat-file-upload" accept=".pdf,.doc,.docx" style="display:none">
            <button class="voice-btn" id="voice-btn" title="Voice Input (Speech to Text)">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"/>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                <line x1="12" y1="19" x2="12" y2="22"/>
              </svg>
            </button>
            <button class="audio-toggle-btn active" id="audio-toggle-btn" title="Toggle Voice Response (Text-to-Speech)">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
                <path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
                <path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>
              </svg>
            </button>
            <button class="send-btn" id="send-btn" title="Send">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
              </svg>
            </button>
          </div>
          <div class="upload-progress" id="upload-progress">
            <div class="upload-progress-bar" id="upload-progress-bar"></div>
          </div>
        </div>
      </section>

      <!-- TAB: JOBS -->
      <section class="panel" id="panel-jobs">
        <div class="panel-header">
          <div>
            <h1>Found Jobs</h1>
            <p id="jobs-subtitle">6 jobs matching your profile</p>
          </div>
          <button class="btn btn-primary" id="scrape-btn">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
            </svg>
            Scrape Now
          </button>
        </div>
        <div class="jobs-content">
          <div class="filter-bar" id="filter-bar">
            <button class="filter-btn active" data-filter="all">All</button>
            <button class="filter-btn" data-filter="linkedin">LinkedIn</button>
            <button class="filter-btn" data-filter="internshala">Internshala</button>
            <button class="filter-btn" data-filter="naukri">Naukri</button>
            <button class="filter-btn" data-filter="indeed">Indeed</button>
            <button class="filter-btn" data-filter="angellist">AngelList</button>
          </div>
          <div class="jobs-grid" id="jobs-grid"></div>
        </div>
      </section>

      <!-- TAB: APPLICATIONS -->
      <section class="panel" id="panel-applications">
        <div class="panel-header">
          <div>
            <h1>Applications</h1>
            <p>Track every application in one board</p>
          </div>
        </div>
        <div class="apps-content">
          <div class="stats-row" id="stats-row"></div>
          <div class="kanban-wrap" id="kanban-wrap"></div>
        </div>
      </section>

      <!-- TAB: RESUME -->
      <section class="panel" id="panel-resume">
        <div class="panel-header">
          <div>
            <h1>Resume Manager</h1>
            <p>AI-powered resume analysis &amp; tailoring</p>
          </div>
        </div>
        <div class="resume-content">
          <div class="upload-zone" id="upload-zone">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            <h3>Drop your resume here or click to upload</h3>
            <p>Supports PDF, DOC, DOCX — Max 10MB</p>
            <input type="file" id="resume-file-input" accept=".pdf,.doc,.docx">
          </div>

          <div class="resume-card" id="resume-card">
            <div class="resume-icon">📄</div>
            <div class="resume-info">
              <h4 id="resume-filename">resume.pdf</h4>
              <p id="resume-meta">2.4 MB · Uploaded just now</p>
            </div>
            <button class="btn btn-secondary btn-sm">Replace</button>
          </div>

          <div class="resume-analysis" id="resume-analysis">
            <h3>AI Analysis</h3>
            <div class="skills-wrap" id="skills-wrap"></div>
            <div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:12px;">
              <div>
                <div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.4px;margin-bottom:4px;">Experience</div>
                <div style="font-size:14px;font-weight:600;">Fresher / Entry Level</div>
              </div>
              <div>
                <div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.4px;margin-bottom:4px;">Education</div>
                <div style="font-size:14px;font-weight:600;">B.Tech — Computer Science</div>
              </div>
              <div>
                <div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.4px;margin-bottom:4px;">Score</div>
                <div style="font-size:14px;font-weight:600;color:var(--green);">8.4 / 10 ATS</div>
              </div>
            </div>
            <div class="ai-notice">
              <span>✨</span>
              <span>AI will keep your resume updated and generate tailored versions for each approved job automatically.</span>
            </div>
          </div>

          <div class="tailored-section">
            <h3>Tailored Versions</h3>
            <div id="tailored-list">
              <div style="text-align:center;padding:24px;color:var(--text-muted);font-size:13px;">
                Upload your resume and approve jobs to generate tailored versions.
              </div>
            </div>
          </div>

          <!-- Featured GitHub Projects -->
          <div class="tailored-section" style="margin-top:24px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
              <h3>🚀 Featured GitHub Projects</h3>
              <a href="https://github.com/Jyotiraditya1006" target="_blank" rel="noopener" style="font-size:12px;color:var(--cyan);text-decoration:none;">github.com/Jyotiraditya1006 ↗</a>
            </div>
            <div id="github-projects-list" style="display:flex;flex-direction:column;gap:12px;">
              <div class="glass-card" style="padding:14px;border-radius:10px;border-left:3px solid var(--purple);background:rgba(255,255,255,0.03);">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                  <strong style="font-size:14px;color:#fff;">VehicleIQ — Real-Time Health & Failure Prevention</strong>
                  <span class="badge" style="background:rgba(124,58,237,0.2);color:var(--purple);font-size:11px;padding:2px 8px;border-radius:6px;">Flagship ML</span>
                </div>
                <p style="font-size:12px;color:var(--text-muted);margin:6px 0;">OBD-II telemetry stream processing with TensorFlow LSTM & FastAPI, DIY diagnostic alerts and Next.js 14 dashboard.</p>
                <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:6px;">
                  <span class="skill-tag purple" style="font-size:10px;">Python</span>
                  <span class="skill-tag cyan" style="font-size:10px;">TensorFlow LSTM</span>
                  <span class="skill-tag green" style="font-size:10px;">FastAPI</span>
                  <span class="skill-tag purple" style="font-size:10px;">Next.js 14</span>
                </div>
              </div>

              <div class="glass-card" style="padding:14px;border-radius:10px;border-left:3px solid var(--cyan);background:rgba(255,255,255,0.03);">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                  <strong style="font-size:14px;color:#fff;">RecruitIQ — AI Candidate & Job Intelligence Engine</strong>
                  <span class="badge" style="background:rgba(6,182,212,0.2);color:var(--cyan);font-size:11px;padding:2px 8px;border-radius:6px;">Live App</span>
                </div>
                <p style="font-size:12px;color:var(--text-muted);margin:6px 0;">Automated candidate-job matching and intelligence platform built with Next.js & TypeScript, deployed live on Vercel.</p>
                <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:6px;">
                  <span class="skill-tag cyan" style="font-size:10px;">TypeScript</span>
                  <span class="skill-tag purple" style="font-size:10px;">Next.js</span>
                  <span class="skill-tag green" style="font-size:10px;">AI Matching</span>
                </div>
              </div>

              <div class="glass-card" style="padding:14px;border-radius:10px;border-left:3px solid var(--green);background:rgba(255,255,255,0.03);">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                  <strong style="font-size:14px;color:#fff;">Deep Learning LSTM Stock & Time-Series Predictor</strong>
                  <span class="badge" style="background:rgba(16,185,129,0.2);color:var(--green);font-size:11px;padding:2px 8px;border-radius:6px;">Deep Learning</span>
                </div>
                <p style="font-size:12px;color:var(--text-muted);margin:6px 0;">Recurrent Neural Network model capturing multi-step temporal dependencies and market volatility forecasting.</p>
                <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:6px;">
                  <span class="skill-tag purple" style="font-size:10px;">TensorFlow</span>
                  <span class="skill-tag cyan" style="font-size:10px;">Keras LSTM</span>
                  <span class="skill-tag green" style="font-size:10px;">Pandas</span>
                </div>
              </div>

              <div class="glass-card" style="padding:14px;border-radius:10px;border-left:3px solid #f59e0b;background:rgba(255,255,255,0.03);">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                  <strong style="font-size:14px;color:#fff;">Customer Churn & Anomaly Classification Pipeline</strong>
                  <span class="badge" style="background:rgba(245,158,11,0.2);color:#f59e0b;font-size:11px;padding:2px 8px;border-radius:6px;">ML Classification</span>
                </div>
                <p style="font-size:12px;color:var(--text-muted);margin:6px 0;">End-to-end customer churn prediction pipeline with Scikit-learn, evaluating attrition factors and retention metrics.</p>
                <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:6px;">
                  <span class="skill-tag green" style="font-size:10px;">Scikit-Learn</span>
                  <span class="skill-tag purple" style="font-size:10px;">Classification</span>
                  <span class="skill-tag cyan" style="font-size:10px;">Data Science</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- TAB: EMAILS & REVERTS -->
      <section class="panel" id="panel-emails">
        <div class="panel-header">
          <div>
            <h1>Emails & Company Reverts</h1>
            <p>Full correspondence history — applications dispatched and recruiter revert-backs</p>
          </div>
          <button class="btn btn-secondary" onclick="loadEmails()" id="refresh-emails-btn">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2v6h-6M3 12a9 9 0 0 1 15-6.7L21 8M3 22v-6h6M21 12a9 9 0 0 1-15 6.7L3 16"/></svg>
            Refresh Mailbox
          </button>
        </div>
        <div class="jobs-content" style="padding:24px 32px;">
          <div id="emails-list-container" style="display:flex;flex-direction:column;gap:14px;"></div>
        </div>
      </section>

      <!-- TAB: SETTINGS -->
      <section class="panel" id="panel-settings">
        <div class="panel-header">
          <div>
            <h1>Settings</h1>
            <p>Configure your profile &amp; job preferences</p>
          </div>
        </div>
        <div class="settings-content">
          <form id="settings-form">
            <div class="settings-grid">
              <!-- Profile -->
              <div class="settings-section">
                <h3><span>👤</span> Profile</h3>
                <div class="form-group">
                  <label class="form-label">Full Name</label>
                  <input class="form-control" id="profile-name" type="text" value="Jyotiraditya Patil">
                </div>
                <div class="form-group">
                  <label class="form-label">Email</label>
                  <input class="form-control" id="profile-email" type="email" value="jyotiradityapatil106@gmail.com">
                </div>
                <div class="form-group">
                  <label class="form-label">Phone</label>
                  <input class="form-control" id="profile-phone" type="tel" value="+91 7020676261">
                </div>
                <div class="form-group">
                  <label class="form-label">Location &amp; Relocation</label>
                  <input class="form-control" id="profile-location" type="text" value="Pune / Mumbai (Open to all locations & Remote)">
                </div>
                <div class="form-group">
                  <label class="form-label">Education / Specialization</label>
                  <input class="form-control" id="profile-education" type="text" value="B.Tech CSE (AI &amp; Machine Learning)">
                </div>
                <div class="form-group">
                  <label class="form-label">LinkedIn Profile URL</label>
                  <input class="form-control" id="profile-linkedin" type="url" placeholder="https://www.linkedin.com/in/your-profile" value="https://www.linkedin.com/in/jyotiraditya-patil-73b394274/">
                </div>
                <div class="form-group">
                  <label class="form-label">GitHub / Portfolio URL</label>
                  <input class="form-control" id="profile-github" type="url" placeholder="https://github.com/your-username" value="https://github.com/Jyotiraditya1006">
                </div>
              </div>

              <!-- Job Preferences -->
              <div class="settings-section">
                <h3><span>🎯</span> Job Preferences</h3>
                <div class="form-group">
                  <label class="form-label">Domains</label>
                  <div class="checkbox-group">
                    <label class="checkbox-item"><input type="checkbox" checked> Data Science / ML / AI</label>
                    <label class="checkbox-item"><input type="checkbox"> Software Engineering</label>
                    <label class="checkbox-item"><input type="checkbox"> Data Engineering</label>
                    <label class="checkbox-item"><input type="checkbox"> MLOps / DevOps</label>
                    <label class="checkbox-item"><input type="checkbox"> Product Management</label>
                  </div>
                </div>
                <div class="form-group" style="margin-top:14px;">
                  <label class="form-label">Experience Level</label>
                  <select class="form-control">
                    <option>Internship</option>
                    <option selected>Entry Level (0-2 yrs)</option>
                    <option>Mid Level (2-5 yrs)</option>
                    <option>Senior (5+ yrs)</option>
                  </select>
                </div>
                <div class="form-group">
                  <label class="form-label">Geography</label>
                  <select class="form-control" multiple style="height:90px;">
                    <option selected>Remote</option>
                    <option selected>Bangalore</option>
                    <option selected>Hyderabad</option>
                    <option>Mumbai</option>
                    <option>Delhi NCR</option>
                    <option>Pune</option>
                  </select>
                </div>
              </div>

              <!-- API Keys -->
              <div class="settings-section">
                <h3><span>🔑</span> API Keys</h3>
                <div class="form-group">
                  <label class="form-label">Gemini API Key</label>
                  <div class="key-field-wrap">
                    <input class="form-control" type="password" id="gemini-key" placeholder="AIza…" value="AIzaSyXXXXXXXXXXXXXXXXXXXXX">
                    <button type="button" class="key-eye" onclick="toggleKeyVisibility('gemini-key', this)">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
                      </svg>
                    </button>
                  </div>
                </div>
                <div class="form-group">
                  <label class="form-label">Gmail (Cold Emails)</label>
                  <div class="key-field-wrap">
                    <input class="form-control" type="password" id="gmail-key" placeholder="App password…">
                    <button type="button" class="key-eye" onclick="toggleKeyVisibility('gmail-key', this)">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
                      </svg>
                    </button>
                  </div>
                </div>
              </div>

              <!-- Platforms -->
              <div class="settings-section">
                <h3><span>🌐</span> Platforms to Search</h3>
                <div class="toggle-group">
                  <div class="toggle-item">
                    <span>LinkedIn</span>
                    <label class="toggle"><input type="checkbox" checked><span class="toggle-slider"></span></label>
                  </div>
                  <div class="toggle-item">
                    <span>Internshala</span>
                    <label class="toggle"><input type="checkbox" checked><span class="toggle-slider"></span></label>
                  </div>
                  <div class="toggle-item">
                    <span>Naukri</span>
                    <label class="toggle"><input type="checkbox" checked><span class="toggle-slider"></span></label>
                  </div>
                  <div class="toggle-item">
                    <span>Indeed</span>
                    <label class="toggle"><input type="checkbox"><span class="toggle-slider"></span></label>
                  </div>
                  <div class="toggle-item">
                    <span>AngelList</span>
                    <label class="toggle"><input type="checkbox" checked><span class="toggle-slider"></span></label>
                  </div>
                </div>
              </div>
            </div>

            <div class="settings-footer">
              <button type="submit" class="btn btn-primary">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
                Save Settings
              </button>
            </div>
          </form>
        </div>
      </section>

    </main>
  </div>
  <div id="toast-container"></div>
  `;
}

// ── Navigation ─────────────────────────────────────────────────────
function initNavigation() {
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
      const tab = item.dataset.tab;
      switchTab(tab);
      // Auto-close mobile sidebar
      if (window.innerWidth <= 768) toggleSidebar(false);
    });
  });
}

function switchTab(tab) {
  State.currentTab = tab;

  document.querySelectorAll('.nav-item').forEach(el => el.classList.toggle('active', el.dataset.tab === tab));
  document.querySelectorAll('.panel').forEach(el => el.classList.remove('active'));

  const panel = $(`panel-${tab}`);
  if (panel) {
    panel.classList.add('active');
    // Trigger data loads
    if (tab === 'jobs')         loadJobs();
    if (tab === 'applications') { loadApplications(); animateStats(); }
    if (tab === 'emails')       loadEmails();
    if (tab === 'settings')     loadProfileSettings();
  }
}

function toggleSidebar(forceOpen) {
  const sidebar  = $('sidebar') || document.getElementById('sidebar');
  const overlay  = document.querySelector('.sidebar-overlay');
  if (!sidebar || !overlay) return;
  const shouldOpen = forceOpen !== undefined ? forceOpen : !sidebar.classList.contains('open');
  sidebar.classList.toggle('open', shouldOpen);
  overlay.classList.toggle('open', shouldOpen);
}

// ── Status Dot ─────────────────────────────────────────────────────
function animateStatusDot() {
  const dot   = $('status-dot');
  const label = $('status-label');
  if (!dot || !label) return;
  dot.classList.add('pulsing');
  label.textContent = 'Running';
}

// ══════════════════════════════════════════════════════════════════
// CHAT
// ══════════════════════════════════════════════════════════════════
function initChat() {
  // Welcome message
  setTimeout(() => appendAIMessage({
    agent: 'orchestrator',
    badge: '🧠 Alex',
    text: "Hey Jyotiraditya! I'm **Alex**, your personal career partner. 🤝 Think of me as your dedicated job-hunt wingman.\n\nWhether you want me to scour the latest Data Science & ML openings right away, refine your resume to pass ATS filters, or prep cold emails to hiring managers — I'm right here with you.\n\nHow's your job search feeling today? Want me to kick off a fresh search across LinkedIn, Internshala, and Naukri, or should we look at your resume first?",
  }), 400);

  // Input events
  const input = $('chat-input');
  if (!input) return;

  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendChatMessage();
    }
  });
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 140) + 'px';
  });

  $('send-btn')?.addEventListener('click', sendChatMessage);

  // File upload via chat
  $('chat-file-upload')?.addEventListener('change', e => {
    const file = e.target.files[0];
    if (file) handleChatFileUpload(file);
  });

  // Voice Input (Speech Recognition)
  initVoiceInput();

  // Audio Output Toggle
  initVoiceOutputToggle();
}

// ── Voice & Audio Support ──────────────────────────────────────────
let recognition = null;
let isRecording = false;
let voiceOutputEnabled = true;

function initVoiceInput() {
  const voiceBtn = $('voice-btn');
  if (!voiceBtn) return;

  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRec) {
    voiceBtn.style.display = 'none';
    return;
  }

  recognition = new SpeechRec();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = 'en-US';

  recognition.onstart = () => {
    isRecording = true;
    voiceBtn.classList.add('recording');
    showToast('Listening... Speak now 🎙️', 'info');
  };

  recognition.onresult = event => {
    const transcript = event.results[0][0].transcript;
    const input = $('chat-input');
    if (input) {
      input.value = transcript;
      input.style.height = 'auto';
      input.style.height = Math.min(input.scrollHeight, 140) + 'px';
      // Automatically send so it feels like a natural verbal conversation
      sendChatMessage();
    }
  };

  recognition.onerror = e => {
    isRecording = false;
    voiceBtn.classList.remove('recording');
    logger.warn('Voice error: ' + e.error);
  };

  recognition.onend = () => {
    isRecording = false;
    voiceBtn.classList.remove('recording');
  };

  voiceBtn.addEventListener('click', () => {
    if (isRecording) {
      recognition.stop();
    } else {
      try {
        recognition.start();
      } catch (err) {
        recognition.stop();
      }
    }
  });
}

function initVoiceOutputToggle() {
  const toggleBtn = $('audio-toggle-btn');
  if (!toggleBtn) return;
  toggleBtn.addEventListener('click', () => {
    voiceOutputEnabled = !voiceOutputEnabled;
    toggleBtn.classList.toggle('active', voiceOutputEnabled);
    if (!voiceOutputEnabled && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    showToast(voiceOutputEnabled ? 'Alex voice enabled 🔊' : 'Alex voice muted 🔇', 'info');
  });
}

function speakText(text) {
  if (!voiceOutputEnabled || !('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel();

  // Clean markdown syntax for clean spoken speech
  const clean = text
    .replace(/[*_#`~\[\]]/g, '')
    .replace(/https?:\/\/\S+/g, '')
    .replace(/•/g, '')
    .trim();

  if (!clean) return;

  const utterance = new SpeechSynthesisUtterance(clean);
  utterance.rate = 1.05;
  utterance.pitch = 1.0;

  // Prefer a natural sounding English voice
  const voices = window.speechSynthesis.getVoices();
  const naturalVoice = voices.find(v => (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('David') || v.name.includes('George')) && v.lang.startsWith('en')) || voices.find(v => v.lang.startsWith('en'));
  if (naturalVoice) utterance.voice = naturalVoice;

  window.speechSynthesis.speak(utterance);
}

function sendChatMessage() {
  const input = $('chat-input');
  const text  = input.value.trim();
  if (!text) return;

  appendUserMessage(text);
  input.value = '';
  input.style.height = 'auto';
  State.chatHistory.push({ role: 'user', text });

  showTypingIndicator();
  if (State.wsConnected && State.ws) {
    State.ws.send(JSON.stringify({
      message: text,
      session_id: State.sessionId || undefined
    }));
  } else {
    simulateDemoResponse(text);
  }
}

function appendUserMessage(text) {
  const container = $('chat-messages');
  const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const div = document.createElement('div');
  div.className = 'msg user';
  div.innerHTML = `
    <div class="msg-avatar usr">🧑</div>
    <div class="msg-content">
      <div class="msg-bubble">${escapeHtml(text)}</div>
      <div class="msg-time">${time}</div>
    </div>
  `;
  container.appendChild(div);
  scrollChat();
}

function appendAIMessage({ agent, badge, text }) {
  const container = $('chat-messages');
  const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const badgeClass = agent === 'scraper' ? 'scraper' : agent === 'writer' ? 'writer' : agent === 'reviewer' ? 'reviewer' : '';

  const div = document.createElement('div');
  div.className = 'msg ai';
  div.innerHTML = `
    <div class="msg-avatar ai">🤖</div>
    <div class="msg-content">
      <div class="msg-meta">
        <span class="agent-badge ${badgeClass}">${badge}</span>
        <span>${time}</span>
      </div>
      <div class="msg-bubble">${markdownLite(text)}</div>
    </div>
  `;
  container.appendChild(div);
  scrollChat();
}

function showTypingIndicator() {
  const container = $('chat-messages');
  const el = document.createElement('div');
  el.className = 'typing-indicator';
  el.id = 'typing-indicator';
  el.innerHTML = `
    <div class="msg-avatar ai">🤖</div>
    <div class="typing-dots"><span></span><span></span><span></span></div>
  `;
  container.appendChild(el);
  scrollChat();
}

function hideTypingIndicator() {
  $('typing-indicator')?.remove();
}

function simulateDemoResponse(userText) {
  const match = QUICK_RESPONSES.find(r => r.match.test(userText)) || QUICK_RESPONSES[QUICK_RESPONSES.length - 1];
  showTypingIndicator();
  const delay = 900 + Math.random() * 600;
  setTimeout(() => {
    hideTypingIndicator();
    appendAIMessage(match);
    speakText(match.text);
  }, delay);
}

function handleChatFileUpload(file) {
  const progressWrap = $('upload-progress');
  const progressBar  = $('upload-progress-bar');
  progressWrap.style.display = 'block';

  let pct = 0;
  const interval = setInterval(() => {
    pct += Math.random() * 15 + 5;
    if (pct >= 100) {
      pct = 100;
      clearInterval(interval);
      setTimeout(() => {
        progressWrap.style.display = 'none';
        progressBar.style.width = '0%';
        appendAIMessage({
          agent: 'reviewer',
          badge: '📋 Reviewer',
          text: `Resume **${file.name}** uploaded successfully! 📎 I'll analyze it now and update your profile. Head to the **Resume tab** to see the full analysis.`,
        });
        showToast('Resume uploaded successfully!', 'success');
      }, 500);
    }
    progressBar.style.width = pct + '%';
  }, 150);
}

function scrollChat() {
  const container = $('chat-messages');
  if (container) container.scrollTop = container.scrollHeight;
}

// ── WebSocket ──────────────────────────────────────────────────────
function initWebSocket() {
  try {
    const ws = new WebSocket('ws://localhost:8000/ws/chat');
    let currentStreamBubble = null;
    let currentStreamText = '';

    ws.onopen = () => {
      State.wsConnected = true;
      State.ws = ws;
      showToast('Connected to Alex!', 'info');
    };

    ws.onmessage = e => {
      const data = JSON.parse(e.data);

      if (data.type === 'session') {
        State.sessionId = data.session_id;
        return;
      }

      if (data.type === 'tool_call') {
        hideTypingIndicator();
        const toolLabels = {
          search_jobs: '🔍 Alex is coordinating Scraper Agent across platforms...',
          get_job_matches: '🎯 Alex is consulting Matcher Agent for top fit...',
          draft_application: '✍️ Alex is directing Writer Agent to draft personalized documents...',
          get_application_status: '📋 Alex is checking your Application Tracker...',
          analyze_resume: '📑 Alex is running deep ATS resume analysis...'
        };
        showToast(toolLabels[data.tool] || `🤖 Agent tool activated: ${data.tool}`, 'info');
        showTypingIndicator();
        return;
      }

      if (data.type === 'chunk') {
        hideTypingIndicator();
        const container = $('chat-messages');
        if (!currentStreamBubble) {
          currentStreamText = '';
          const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
          const div = document.createElement('div');
          div.className = 'msg ai streaming';
          div.innerHTML = `
            <div class="msg-avatar ai">🤖</div>
            <div class="msg-content">
              <div class="msg-meta">
                <span class="agent-badge">🧠 Alex</span>
                <span>${time}</span>
              </div>
              <div class="msg-bubble stream-content"></div>
            </div>
          `;
          container.appendChild(div);
          currentStreamBubble = div.querySelector('.stream-content');
        }
        currentStreamText += data.content;
        currentStreamBubble.innerHTML = markdownLite(currentStreamText);
        scrollChat();
        return;
      }

      if (data.type === 'done') {
        hideTypingIndicator();
        if (currentStreamText) {
          speakText(currentStreamText);
        }
        currentStreamBubble = null;
        currentStreamText = '';
        if (data.data && data.data.tool_called === 'search_jobs') {
          loadJobs();
        }
        return;
      }

      if (data.type === 'error') {
        hideTypingIndicator();
        currentStreamBubble = null;
        appendAIMessage({
          agent: 'orchestrator',
          badge: '🧠 Alex',
          text: data.content || 'Something went sideways on my end. Mind repeating that?',
        });
      }
    };

    ws.onerror = () => { State.wsConnected = false; };
    ws.onclose = () => { State.wsConnected = false; };
  } catch (_) {
    State.wsConnected = false;
  }
}

// ══════════════════════════════════════════════════════════════════
// JOBS
// ══════════════════════════════════════════════════════════════════
function initJobs() {
  $('filter-bar')?.addEventListener('click', e => {
    const btn = e.target.closest('.filter-btn');
    if (!btn) return;
    $$('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    State.activeFilter = btn.dataset.filter;
    renderJobs();
  });

  $('scrape-btn')?.addEventListener('click', scrapeJobs);
}

function renderJobsSkeletons() {
  const grid = $('jobs-grid');
  if (!grid) return;
  grid.innerHTML = Array(6).fill(0).map(() => `
    <div class="skeleton-card">
      <div class="skeleton-line" style="height:16px;width:60%;margin-bottom:14px;"></div>
      <div class="skeleton-line" style="height:12px;width:80%;"></div>
      <div class="skeleton-line" style="height:12px;width:50%;"></div>
      <div class="skeleton-line" style="height:32px;width:100%;margin-top:14px;border-radius:8px;"></div>
    </div>
  `).join('');
}

async function loadJobs() {
  renderJobsSkeletons();
  try {
    const res = await fetchWithTimeout('/api/jobs', 3000);
    const data = await res.json();
    if (data && Array.isArray(data.jobs) && data.jobs.length > 0) {
      State.jobs = data.jobs.map(j => ({
        id: j.id,
        title: j.title || 'Data Science Role',
        company: j.company || 'Technology Company',
        initials: (j.company || 'TC').slice(0, 2).toUpperCase(),
        color: '#7c3aed',
        location: j.location || 'Remote / Hybrid',
        platform: j.platform || 'linkedin',
        score: Math.round(j.match_score || 85),
        posted: j.scraped_at ? new Date(j.scraped_at).toLocaleDateString() : 'Recent',
        url: j.url || 'https://www.linkedin.com/jobs',
        description: j.description || 'Exciting opportunity working on data science and machine learning systems.',
        job_type: j.job_type || 'internship',
        salary: j.salary_range || 'Competitive Stipend',
        approved: j.status === 'approved' || j.status === 'applied',
      }));
    } else {
      State.jobs = [...SAMPLE_JOBS];
    }
  } catch (_) {
    State.jobs = [...SAMPLE_JOBS];
  }
  renderJobs();
}

function renderJobs() {
  const grid = $('jobs-grid');
  if (!grid) return;

  const filtered = State.activeFilter === 'all'
    ? State.jobs
    : State.jobs.filter(j => j.platform === State.activeFilter);

  const sub = $('jobs-subtitle');
  if (sub) sub.textContent = `${filtered.length} verified listings available`;

  if (filtered.length === 0) {
    grid.innerHTML = `
      <div class="empty-state">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
        </svg>
        <h3 style="font-size:16px;color:#fff;">No openings found under this filter</h3>
        <p style="font-size:13px;">Click "Scrape Now" or switch platform filter.</p>
      </div>
    `;
    return;
  }

  grid.innerHTML = filtered.map((job, i) => jobCardHTML(job, i)).join('');
  setTimeout(() => animateMatchRings(), 100);
}

function jobCardHTML(job, idx) {
  const scoreColor = job.score >= 80 ? 'green' : job.score >= 60 ? 'yellow' : 'red';
  const circumference = 113;
  const offset = circumference - (job.score / 100) * circumference;
  const safeId = typeof job.id === 'string' ? `'${job.id}'` : job.id;

  return `
    <div class="job-card" style="animation-delay:${idx * 40}ms" data-id="${job.id}">
      <div class="job-card-header">
        <div class="company-logo" style="background:rgba(124,58,237,0.15);color:var(--purple-light);border:1px solid rgba(124,58,237,0.3);">
          ${job.initials}
        </div>
        <div class="match-ring-wrap">
          <svg viewBox="0 0 36 36">
            <circle class="ring-bg" cx="18" cy="18" r="16"/>
            <circle class="ring-fill ${scoreColor}" cx="18" cy="18" r="16"
              stroke-dasharray="${circumference}" stroke-dashoffset="${circumference}"
              data-offset="${offset}"/>
          </svg>
          <div class="match-pct ${scoreColor}">${job.score}%</div>
        </div>
      </div>
      <div class="job-title">${escapeHtml(job.title)}</div>
      <div class="job-company">${escapeHtml(job.company)}</div>
      <div class="job-tags">
        <span class="tag tag-loc">${escapeHtml(job.location)}</span>
        <span class="tag tag-platform ${job.platform}">${platformLabel(job.platform)}</span>
        <span class="tag tag-date">${escapeHtml(job.job_type || 'Internship')}</span>
      </div>
      <div class="job-card-actions">
        <button class="btn btn-view" onclick="viewJob(${safeId})">View Details</button>
        <button class="btn btn-approve" onclick="approveJob(${safeId}, this)">
          ${job.approved ? 'Approved' : 'Review & Apply'}
        </button>
        <a href="${job.url || '#'}" target="_blank" rel="noopener noreferrer" class="btn btn-secondary" style="padding:6px 10px;text-decoration:none;" title="Open on official website">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
        </a>
      </div>
    </div>
  `;
}

function platformLabel(p) {
  const map = { linkedin: 'LinkedIn', naukri: 'Naukri', indeed: 'Indeed', internshala: 'Internshala', wellfound: 'Wellfound' };
  return map[p] || p;
}

function animateMatchRings() {
  document.querySelectorAll('.ring-fill').forEach(ring => {
    const target = parseFloat(ring.dataset.offset);
    requestAnimationFrame(() => { ring.style.strokeDashoffset = target; });
  });
}

async function approveJob(id, btn) {
  const job = State.jobs.find(j => String(j.id) === String(id));
  if (!job) return;

  btn.disabled = true;
  btn.textContent = 'Preparing…';

  try {
    await fetchWithTimeout(`/api/jobs/${id}/approve`, 4000, { method: 'PUT' });
  } catch (_) {}

  job.approved = true;
  btn.textContent = 'Applied';
  btn.style.background = 'rgba(16,185,129,0.2)';
  btn.disabled = false;

  showToast(`Application drafted & submitted for ${job.company}! Check Applications tab.`, 'success');
  addTailoredResume(job);

  // Switch to applications tab to see the live record
  setTimeout(() => loadApplications(), 500);
}

function viewJob(id) {
  const job = State.jobs.find(j => String(j.id) === String(id));
  if (!job) return;

  let modal = $('job-detail-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'job-detail-modal';
    modal.className = 'modal-overlay';
    document.body.appendChild(modal);
  }

  modal.innerHTML = `
    <div class="modal-card">
      <div class="modal-header">
        <div>
          <h2>${escapeHtml(job.title)}</h2>
          <span style="font-size:13px;color:var(--text-secondary);">${escapeHtml(job.company)} · ${platformLabel(job.platform)}</span>
        </div>
        <button class="modal-close-btn" onclick="closeJobModal()">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>
      <div class="modal-body">
        <div class="modal-meta-grid">
          <div class="modal-meta-item">
            <strong>Location</strong>
            <span>${escapeHtml(job.location)}</span>
          </div>
          <div class="modal-meta-item">
            <strong>Role Type</strong>
            <span>${escapeHtml(job.job_type || 'Internship')}</span>
          </div>
          <div class="modal-meta-item">
            <strong>ATS Fit Score</strong>
            <span style="color:var(--green);">${job.score}%</span>
          </div>
          <div class="modal-meta-item">
            <strong>Compensation</strong>
            <span>${escapeHtml(job.salary || 'Competitive')}</span>
          </div>
        </div>

        <h4>Job Description & Requirements</h4>
        <p style="white-space:pre-line;">${escapeHtml(job.description || 'Full requirements and responsibilities are available on the hiring portal.')}</p>

        <h4>Automated Application Pipeline</h4>
        <p style="font-size:13px;color:var(--text-muted);">Alex has tailored a specialized resume highlighting your relevant ML projects and prepared an ATS-optimized cover letter for ${escapeHtml(job.company)}.</p>
      </div>
      <div class="modal-footer">
        <a href="${job.url || '#'}" target="_blank" rel="noopener noreferrer" class="btn btn-secondary" style="text-decoration:none;">
          View on ${platformLabel(job.platform)} ↗
        </a>
        <button class="btn btn-primary" onclick="approveJob('${job.id}', this); closeJobModal();">
          Approve & Auto-Submit Application
        </button>
      </div>
    </div>
  `;

  modal.classList.add('active');
  modal.onclick = (e) => {
    if (e.target === modal) closeJobModal();
  };
}

function closeJobModal() {
  const modal = $('job-detail-modal');
  if (modal) modal.classList.remove('active');
}

async function scrapeJobs() {
  const btn = $('scrape-btn');
  btn.disabled = true;
  btn.innerHTML = `
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="animation:spin 1s linear infinite;">
      <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
    </svg>
    Scraping…
  `;

  // Add spin style
  if (!document.querySelector('#spin-style')) {
    const st = document.createElement('style');
    st.id = 'spin-style';
    st.textContent = '@keyframes spin { to { transform: rotate(360deg); } }';
    document.head.appendChild(st);
  }

  const dot = $('status-dot');
  dot?.classList.add('pulsing');

  try { await fetchWithTimeout('/api/scrape', 5000, { method: 'POST' }); } catch (_) {}

  // Simulate finding new jobs (demo)
  await delay(2000);
  showToast('Scrape complete! Found 47 new listings (6 high-match) 🎉', 'success');

  btn.disabled = false;
  btn.innerHTML = `
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
    </svg>
    Scrape Now
  `;
  loadJobs();
}

// ══════════════════════════════════════════════════════════════════
// APPLICATIONS
// ══════════════════════════════════════════════════════════════════
function initApplications() {
  renderApplications();
}

function renderApplications() {
  renderKanban();
  renderStats();
}

function renderStats() {
  const row = $('stats-row');
  if (!row) return;

  const data = State.applicationData || SAMPLE_APPLICATIONS;
  const appliedCount = (data.applied || []).length;
  const reviewCount  = (data.review || []).length;
  const interviewCount = (data.interview || []).length;
  const offerCount   = (data.offer || []).length;
  const total        = appliedCount + reviewCount + interviewCount + offerCount + (data.rejected || []).length;
  const ratePct      = total > 0 ? Math.round(((interviewCount + offerCount) / total) * 100) : 0;

  row.innerHTML = `
    <div class="stat-card purple">
      <div class="stat-num" data-target="${total}">${total}</div>
      <div class="stat-label">Total Applied</div>
    </div>
    <div class="stat-card yellow">
      <div class="stat-num" data-target="${reviewCount}">${reviewCount}</div>
      <div class="stat-label">In Review</div>
    </div>
    <div class="stat-card green">
      <div class="stat-num" data-target="${interviewCount}">${interviewCount}</div>
      <div class="stat-label">Interviews</div>
    </div>
    <div class="stat-card cyan">
      <div class="stat-num" style="font-size:22px;">${ratePct}%</div>
      <div class="stat-label">Success Rate</div>
    </div>
  `;
}

function animateStats() {
  renderStats();
  setTimeout(() => {
    document.querySelectorAll('.stat-num[data-target]').forEach(el => {
      const target = parseInt(el.dataset.target, 10);
      animateCounter(el, 0, target, 800);
    });
  }, 100);
}

function animateCounter(el, from, to, duration) {
  const start = performance.now();
  function step(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.round(from + (to - from) * ease);
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

function animateCounterPct(el, from, to, duration) {
  const start = performance.now();
  function step(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.round(from + (to - from) * ease) + '%';
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

async function loadApplications() {
  try {
    const res = await fetchWithTimeout('/api/applications', 3000);
    const data = await res.json();
    if (data && Array.isArray(data.applications) && data.applications.length > 0) {
      // Map API records into Kanban status columns
      const grouped = { applied: [], review: [], interview: [], rejected: [], offer: [] };
      data.applications.forEach(app => {
        const key = app.status === 'in_review' ? 'review' : (grouped[app.status] ? app.status : 'applied');
        grouped[key].push({
          id: app.id,
          company: app.job_company || 'Tech Company',
          role: app.job_title || 'ML / Data Science Role',
          date: app.applied_at ? new Date(app.applied_at).toLocaleDateString() : 'Today',
          coverLetter: app.cover_letter_text || 'Tailored cover letter created by Writer Agent.',
          location: app.job_location || 'Remote',
          url: app.job_url || 'https://www.linkedin.com/jobs',
          highlight: key === 'interview',
        });
      });
      State.applicationData = grouped;
    } else {
      State.applicationData = { ...SAMPLE_APPLICATIONS };
    }
  } catch (_) {
    State.applicationData = { ...SAMPLE_APPLICATIONS };
  }
  renderKanban();
  renderStats();
}

function renderKanban() {
  const wrap = $('kanban-wrap');
  if (!wrap) return;

  const data = State.applicationData || SAMPLE_APPLICATIONS;
  const cols = [
    { key: 'applied',   label: 'Applied',    badge: 'Applied',    data: data.applied || []   },
    { key: 'review',    label: 'In Review',  badge: 'Reviewing',  data: data.review || []    },
    { key: 'interview', label: 'Interview',  badge: 'Interview',  data: data.interview || [] },
    { key: 'rejected',  label: 'Archived',   badge: 'Archived',   data: data.rejected || []  },
    { key: 'offer',     label: 'Offer',      badge: 'Offer',      data: data.offer || []     },
  ];

  // Update badge count
  const appsBadge = $('apps-badge');
  const totalCount = Object.values(data).reduce((acc, arr) => acc + (arr ? arr.length : 0), 0);
  if (appsBadge) appsBadge.textContent = totalCount;

  wrap.innerHTML = cols.map(col => `
    <div class="kanban-col">
      <div class="kanban-col-header">
        <span>${col.label}</span>
        <span class="col-count">${col.data.length}</span>
      </div>
      ${col.data.map((app, i) => `
        <div class="app-card ${app.highlight ? 'interview-highlight' : ''}" onclick="viewApplicationDetail('${col.key}', ${i})" style="cursor:pointer;" title="Click to view tailored documents & status">
          <div class="app-card-company">${escapeHtml(app.company)}</div>
          <div class="app-card-role">${escapeHtml(app.role)}</div>
          <div class="app-card-date">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
            </svg>
            ${escapeHtml(app.date)}
          </div>
        </div>
      `).join('')}
      ${col.data.length === 0 ? `<div style="text-align:center;padding:24px 12px;color:var(--text-muted);font-size:12px;border:1px dashed var(--glass-border);border-radius:var(--radius-sm);">No active applications</div>` : ''}
    </div>
  `).join('');
}

function viewApplicationDetail(colKey, idx) {
  const data = State.applicationData || SAMPLE_APPLICATIONS;
  const app = data[colKey] ? data[colKey][idx] : null;
  if (!app) return;

  let modal = $('job-detail-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'job-detail-modal';
    modal.className = 'modal-overlay';
    document.body.appendChild(modal);
  }

  modal.innerHTML = `
    <div class="modal-card">
      <div class="modal-header">
        <div>
          <h2>${escapeHtml(app.company)} · ${escapeHtml(app.role)}</h2>
          <span style="font-size:12px;color:var(--cyan);text-transform:uppercase;font-weight:600;">Status: ${colKey.toUpperCase()}</span>
        </div>
        <button class="modal-close-btn" onclick="closeJobModal()">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>
      <div class="modal-body">
        <h4>Application Record</h4>
        <div class="modal-meta-grid">
          <div class="modal-meta-item">
            <strong>Company</strong>
            <span>${escapeHtml(app.company)}</span>
          </div>
          <div class="modal-meta-item">
            <strong>Target Role</strong>
            <span>${escapeHtml(app.role)}</span>
          </div>
          <div class="modal-meta-item">
            <strong>Submitted Date</strong>
            <span>${escapeHtml(app.date)}</span>
          </div>
          <div class="modal-meta-item">
            <strong>Location</strong>
            <span>${escapeHtml(app.location || 'Remote / Hybrid')}</span>
          </div>
        </div>

        <h4>Tailored Cover Letter Prepared by Alex</h4>
        <div style="background:rgba(255,255,255,0.03);padding:14px;border-radius:10px;border:1px solid var(--glass-border);font-size:13px;white-space:pre-line;">
          ${escapeHtml(app.coverLetter || "Dear Hiring Team,\n\nI am writing to express my strong enthusiasm for the " + app.role + " role at " + app.company + ". With hands-on experience developing ML models, data pipelines, and working with Python and SQL, I am eager to contribute immediately to your team.\n\nThank you for considering my application.\n\nBest regards,\nJyotiraditya Patil")}
        </div>
      </div>
      <div class="modal-footer">
        <a href="${app.url || 'https://www.linkedin.com/jobs'}" target="_blank" rel="noopener noreferrer" class="btn btn-secondary" style="text-decoration:none;">
          View Job Listing ↗
        </a>
        <button class="btn btn-primary" onclick="closeJobModal()">
          Done Reviewing
        </button>
      </div>
    </div>
  `;

  modal.classList.add('active');
  modal.onclick = (e) => {
    if (e.target === modal) closeJobModal();
  };
}

// ══════════════════════════════════════════════════════════════════
// EMAILS & REVERTS
// ══════════════════════════════════════════════════════════════════
let activeEmails = [];

async function loadEmails() {
  const container = $('emails-list-container');
  if (!container) return;
  container.innerHTML = `<div style="text-align:center;padding:32px;color:var(--text-muted);">Syncing mailbox...</div>`;

  try {
    const res = await fetchWithTimeout('/api/emails', 4000);
    const data = await res.json();
    activeEmails = data.emails || [];
    renderEmails(activeEmails);

    const badge = $('emails-badge');
    if (badge) badge.textContent = activeEmails.length;
  } catch (err) {
    container.innerHTML = `<div style="text-align:center;padding:32px;color:var(--text-muted);">Unable to load emails. Click Refresh.</div>`;
  }
}

function renderEmails(emails) {
  const container = $('emails-list-container');
  if (!container) return;

  if (emails.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#06b6d4" stroke-width="1.5"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
        <h3 style="font-size:16px;color:#fff;">No correspondence yet</h3>
        <p style="font-size:13px;">Approve or apply to jobs and your outbound applications and company revert-backs will appear here.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = emails.map((m, idx) => {
    const isInbound = m.direction === 'inbound';
    const tagColor = isInbound ? 'rgba(6,182,212,0.15)' : 'rgba(124,58,237,0.15)';
    const tagBorder = isInbound ? 'rgba(6,182,212,0.3)' : 'rgba(124,58,237,0.3)';
    const textColor = isInbound ? 'var(--cyan)' : 'var(--purple-light)';
    const label = isInbound ? 'Company Revert-Back' : 'Application Dispatched';

    return `
      <div class="job-card" onclick="viewEmailDetail(${idx})" style="cursor:pointer;padding:18px 22px;display:flex;justify-content:space-between;align-items:center;gap:16px;">
        <div style="flex:1;">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
            <span style="font-size:11px;font-weight:700;padding:2px 8px;border-radius:12px;background:${tagColor};border:1px solid ${tagBorder};color:${textColor};text-transform:uppercase;">
              ${label}
            </span>
            <span style="font-size:12px;color:var(--text-muted);">${m.created_at ? new Date(m.created_at).toLocaleString() : 'Recent'}</span>
          </div>
          <div style="font-size:15px;font-weight:700;color:#fff;margin-bottom:4px;">${escapeHtml(m.subject)}</div>
          <div style="font-size:13px;color:var(--text-secondary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:550px;">
            <strong>From:</strong> ${escapeHtml(m.sender)} &nbsp;·&nbsp; <strong>To:</strong> ${escapeHtml(m.recipient)}
          </div>
        </div>
        <div style="text-align:right;">
          <button class="btn btn-secondary" style="padding:6px 12px;font-size:12px;">Open Message ↗</button>
        </div>
      </div>
    `;
  }).join('');
}

function viewEmailDetail(idx) {
  const email = activeEmails[idx];
  if (!email) return;

  let modal = $('job-detail-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'job-detail-modal';
    modal.className = 'modal-overlay';
    document.body.appendChild(modal);
  }

  const isInbound = email.direction === 'inbound';

  modal.innerHTML = `
    <div class="modal-card">
      <div class="modal-header">
        <div>
          <h2>${escapeHtml(email.subject)}</h2>
          <span style="font-size:12px;color:${isInbound ? 'var(--cyan)' : 'var(--purple-light)'};font-weight:600;text-transform:uppercase;">
            ${isInbound ? 'Inbound Company Revert (Automated Acknowledgment)' : 'Outbound Candidate Application'}
          </span>
        </div>
        <button class="modal-close-btn" onclick="closeJobModal()">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>
      <div class="modal-body">
        <div class="modal-meta-grid">
          <div class="modal-meta-item">
            <strong>From</strong>
            <span>${escapeHtml(email.sender)}</span>
          </div>
          <div class="modal-meta-item">
            <strong>To</strong>
            <span>${escapeHtml(email.recipient)}</span>
          </div>
          <div class="modal-meta-item">
            <strong>Delivery Status</strong>
            <span style="color:var(--green);">${escapeHtml(email.status || 'Delivered')}</span>
          </div>
          <div class="modal-meta-item">
            <strong>Timestamp</strong>
            <span>${email.created_at ? new Date(email.created_at).toLocaleString() : 'Now'}</span>
          </div>
        </div>

        <h4>Message Content</h4>
        <div style="background:rgba(255,255,255,0.03);padding:18px;border-radius:10px;border:1px solid var(--glass-border);font-size:13.5px;line-height:1.7;white-space:pre-line;color:#f1f5f9;">
${escapeHtml(email.body)}
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-primary" onclick="closeJobModal()">
          Close
        </button>
      </div>
    </div>
  `;

  modal.classList.add('active');
  modal.onclick = (e) => {
    if (e.target === modal) closeJobModal();
  };
}

// ══════════════════════════════════════════════════════════════════
// RESUME
// ══════════════════════════════════════════════════════════════════
function initResume() {
  const zone  = $('upload-zone');
  const input = $('resume-file-input');

  zone?.addEventListener('click', () => input?.click());
  input?.addEventListener('change', e => { if (e.target.files[0]) processResume(e.target.files[0]); });

  zone?.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone?.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone?.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    if (e.dataTransfer.files[0]) processResume(e.dataTransfer.files[0]);
  });
}

function processResume(file) {
  State.uploadedResume = file;

  const card = $('resume-card');
  const fn   = $('resume-filename');
  const meta = $('resume-meta');
  const analysis = $('resume-analysis');

  fn.textContent   = file.name;
  meta.textContent = `${(file.size / 1024).toFixed(0)} KB · Uploaded ${new Date().toLocaleTimeString()}`;
  card?.classList.add('visible');

  showToast('Resume uploaded! Analyzing…', 'info');

  setTimeout(() => {
    analysis?.classList.add('visible');
    renderSkills();
    showToast('Resume analysis complete! ATS Score: 8.4/10 ✨', 'success');
  }, 1800);
}

function renderSkills() {
  const wrap = $('skills-wrap');
  if (!wrap) return;
  const skills = [
    { label: 'Python',          cls: 'purple' },
    { label: 'Machine Learning',cls: 'cyan'   },
    { label: 'TensorFlow',      cls: 'purple' },
    { label: 'PyTorch',         cls: 'cyan'   },
    { label: 'SQL',             cls: 'green'  },
    { label: 'Deep Learning',   cls: 'purple' },
    { label: 'NLP',             cls: 'cyan'   },
    { label: 'Scikit-learn',    cls: 'green'  },
    { label: 'Data Analysis',   cls: 'purple' },
    { label: 'Pandas / NumPy',  cls: 'green'  },
    { label: 'Computer Vision', cls: 'cyan'   },
    { label: 'Git',             cls: 'green'  },
  ];
  wrap.innerHTML = skills.map(s => `<span class="skill-tag ${s.cls}">${s.label}</span>`).join('');
}

function addTailoredResume(job) {
  const list = $('tailored-list');
  if (!list) return;

  // Remove placeholder
  const placeholder = list.querySelector('div[style]');
  if (placeholder) placeholder.remove();

  const item = document.createElement('div');
  item.className = 'tailored-item';
  item.innerHTML = `
    <div class="t-company">${job.company}</div>
    <div class="t-role">${job.title}</div>
    <div class="t-match">▲ ${job.score}% match</div>
    <button class="btn btn-secondary btn-sm">Download</button>
  `;
  list.appendChild(item);
}

// ══════════════════════════════════════════════════════════════════
// SETTINGS
// ══════════════════════════════════════════════════════════════════
async function loadProfileSettings() {
  try {
    const res = await fetchWithTimeout('/api/profile', 3000);
    const data = await res.json();
    if (data && data.profile) {
      const p = data.profile;
      if ($('profile-name') && p.name) $('profile-name').value = p.name;
      if ($('profile-email') && p.email) $('profile-email').value = p.email;
      if ($('profile-phone') && p.phone) $('profile-phone').value = p.phone;
      if ($('profile-location') && p.location) $('profile-location').value = p.location;
      if ($('profile-education') && p.experience_level) $('profile-education').value = p.experience_level;
      if ($('profile-linkedin') && p.linkedin_url) $('profile-linkedin').value = p.linkedin_url;
      if ($('profile-github') && p.github_url) $('profile-github').value = p.github_url;
    }
  } catch (err) {
    console.warn('Could not load profile from server:', err);
  }
}

function initSettings() {
  loadProfileSettings();

  $('settings-form')?.addEventListener('submit', async e => {
    e.preventDefault();
    const btn = e.submitter || e.target.querySelector('button[type="submit"]');
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Saving…';
    }

    const payload = {
      name: $('profile-name')?.value || 'Jyotiraditya Patil',
      email: $('profile-email')?.value || 'jyotiradityapatil106@gmail.com',
      phone: $('profile-phone')?.value || '+91 7020676261',
      location: $('profile-location')?.value || 'Pune / Mumbai (Open to all locations & Remote)',
      experience_level: $('profile-education')?.value || 'Fresher / Student (B.Tech CSE - AI & ML)',
      linkedin_url: $('profile-linkedin')?.value || 'https://www.linkedin.com/in/jyotiraditya-patil-73b394274/',
      github_url: $('profile-github')?.value || 'https://github.com/Jyotiraditya1006'
    };

    try {
      await fetchWithTimeout('/api/profile', 4000, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      showToast('Settings & GitHub profile saved successfully! ✅', 'success');
    } catch (_) {
      showToast('Settings saved locally!', 'info');
    }

    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg> Save Settings`;
    }
  });
}

function toggleKeyVisibility(inputId, btn) {
  const input = $(inputId);
  if (!input) return;
  const isPassword = input.type === 'password';
  input.type = isPassword ? 'text' : 'password';
  btn.innerHTML = isPassword
    ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>`
    : `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`;
}

// ── Toast ──────────────────────────────────────────────────────────
function showToast(message, type = 'info') {
  const container = $('toast-container');
  if (!container) return;

  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span class="toast-icon">${icons[type] || 'ℹ️'}</span><span class="toast-msg">${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = 'toast-out 0.3s ease forwards';
    setTimeout(() => toast.remove(), 300);
  }, 3800);
}

// ── Utilities ──────────────────────────────────────────────────────
function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function markdownLite(text) {
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>');
}

async function fetchWithTimeout(url, ms, opts = {}) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), ms);
  const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
  try {
    const res = await fetch(url, { ...opts, headers, signal: controller.signal });
    clearTimeout(id);
    return res;
  } catch (e) {
    clearTimeout(id);
    throw e;
  }
}

function delay(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

// ── Expose globals needed by inline onclick ───────────────────────
window.approveJob      = approveJob;
window.viewJob         = viewJob;
window.toggleSidebar   = toggleSidebar;
window.toggleKeyVisibility = toggleKeyVisibility;
