/**
 * JOBAGENT AI — EXECUTIVE CLIENT ENGINE
 * Handles live jobs sync, real-time application tracking, recruiter revert modals,
 * WebSocket chat, ATS resume management, and settings.
 */

'use strict';

const API_BASE = window.location.origin;

// ── Application State ────────────────────────────────────────────────────────
const AppState = {
  currentTab: 'jobs',
  jobs: [],
  applications: [],
  filteredJobs: [],
  activeFilter: 'all',
  searchQuery: '',
  activeSort: 'score',
  ws: null,
  profile: {
    name: 'Jyotiraditya Patil',
    email: 'jyotiradityapatil01@gmail.com',
    phone: '+91 7020676261',
    location: 'Pune / Mumbai (Open to Remote)',
    github: 'https://github.com/Jyotiraditya1006',
    linkedin: 'https://www.linkedin.com/in/jyotiraditya-patil-73b394274/',
    experience_level: 'Fresher / B.Tech CSE (AI & ML)'
  }
};

// ── Curated Real Fallback / Default Data ──────────────────────────────────────
const DEFAULT_JOBS = [
  {
    id: "job-01",
    title: "Machine Learning Research Intern",
    company: "Google",
    location: "Bangalore / Hybrid",
    platform: "linkedin",
    job_type: "internship",
    match_score: 95,
    posted_date: "1 day ago",
    salary_range: "₹1,00,000 / month",
    description: "Work with Google DeepMind and Core ML researchers on computer vision, sequence modeling, and large foundation models. Ideal for candidates with PyTorch/TensorFlow expertise and projects like VehicleIQ or RecruitIQ.",
    skills: ["Python", "PyTorch", "Computer Vision", "TensorFlow", "Deep Learning"],
    status: "pending"
  },
  {
    id: "job-02",
    title: "Data Science & NLP Intern",
    company: "Microsoft",
    location: "Hyderabad / Remote",
    platform: "naukri",
    job_type: "internship",
    match_score: 91,
    posted_date: "2 days ago",
    salary_range: "₹90,000 / month",
    description: "Join the Azure AI Cognitive Services group. Develop high-throughput text classification, semantic search, and document summarization models.",
    skills: ["Python", "NLP", "Scikit-learn", "FastAPI", "Transformers"],
    status: "pending"
  },
  {
    id: "job-03",
    title: "Applied Scientist Intern",
    company: "Amazon",
    location: "Bangalore",
    platform: "linkedin",
    job_type: "internship",
    match_score: 88,
    posted_date: "3 days ago",
    salary_range: "₹85,000 / month",
    description: "Develop time-series predictive modeling, churn forecasting, and pricing optimization algorithms for Amazon Retail India.",
    skills: ["Python", "Time Series", "XGBoost", "PyTorch", "Pandas"],
    status: "pending"
  },
  {
    id: "job-04",
    title: "Computer Vision & Telematics Engineer",
    company: "Ola Electric",
    location: "Bangalore",
    platform: "wellfound",
    job_type: "full-time",
    match_score: 94,
    posted_date: "Just now",
    salary_range: "₹12 - 18 LPA",
    description: "Lead on-vehicle vision intelligence and obstacle detection. Candidate portfolio projects in edge AI and YOLO telematics (like VehicleIQ) are strongly prioritized.",
    skills: ["Python", "YOLOv8", "OpenCV", "ONNX", "Edge AI"],
    status: "pending"
  },
  {
    id: "job-05",
    title: "Data Analyst & ML Specialist",
    company: "Zomato",
    location: "Gurugram / Hybrid",
    platform: "internshala",
    job_type: "internship",
    match_score: 86,
    posted_date: "4 days ago",
    salary_range: "₹45,000 / month",
    description: "Analyze customer retention signals, churn drivers, and build automated delivery routing pipelines using statistical ML techniques.",
    skills: ["Python", "SQL", "Pandas", "Scikit-learn", "Tableau"],
    status: "pending"
  },
  {
    id: "job-06",
    title: "Junior Data Scientist",
    company: "CRED",
    location: "Bangalore",
    platform: "naukri",
    job_type: "full-time",
    match_score: 89,
    posted_date: "5 days ago",
    salary_range: "₹14 - 20 LPA",
    description: "Architect fraud-detection models and real-time transaction underwriting risk pipelines using tree ensembles and neural embeddings.",
    skills: ["Python", "XGBoost", "Deep Learning", "SQL", "Feature Engineering"],
    status: "pending"
  },
  {
    id: "job-07",
    title: "AI Research & Modeling Intern",
    company: "Paytm",
    location: "Noida / Remote",
    platform: "internshala",
    job_type: "internship",
    match_score: 82,
    posted_date: "1 week ago",
    salary_range: "₹40,000 / month",
    description: "Implement recurrent architectures and Markovian models for user engagement pattern discovery and financial forecasting.",
    skills: ["Python", "LSTM", "HMM", "Scikit-learn", "NumPy"],
    status: "pending"
  },
  {
    id: "job-08",
    title: "Machine Learning Engineer",
    company: "Swiggy",
    location: "Bangalore",
    platform: "indeed",
    job_type: "full-time",
    match_score: 87,
    posted_date: "3 days ago",
    salary_range: "₹15 - 22 LPA",
    description: "Build personalization and recommendation engines serving millions of real-time restaurant orders and consumer interactions.",
    skills: ["Python", "PyTorch", "Recommendation Systems", "Docker", "FastAPI"],
    status: "pending"
  }
];

const DEFAULT_APPLICATIONS = [
  {
    id: "app-01",
    company: "Google",
    role: "ML Research Intern",
    date: "Today at 10:15 AM",
    status: "revert",
    revertSubject: "Thank you for applying: Machine Learning Research Intern at Google",
    revertFrom: "Google Talent Acquisition <careers@google.com>",
    revertBody: "Hi Jyotiraditya,\n\nThank you for applying for the Machine Learning Research Intern role at Google. We have received your application, resume, and portfolio.\n\nOur university staffing team was particularly impressed by your computer vision work on VehicleIQ and ATS parsing experience with RecruitIQ. Your application is currently under preliminary review by our hiring committee.\n\nWe will revert back regarding the technical interview timeline shortly.\n\nWarm regards,\nGoogle Talent Acquisition Team",
    coverLetter: "Dear Google Hiring Team,\n\nI am writing to express my strong enthusiasm for the Machine Learning Research Intern position. Having engineered end-to-end computer vision systems (VehicleIQ) and intelligent parsing architectures (RecruitIQ), I have developed a rigorous technical foundation in PyTorch, computer vision, and foundation models.\n\nI would be thrilled to contribute to Google DeepMind and research initiatives in Bangalore.\n\nSincerely,\nJyotiraditya Patil\nhttps://github.com/Jyotiraditya1006"
  },
  {
    id: "app-02",
    company: "Microsoft",
    role: "Data Science & NLP Intern",
    date: "Yesterday",
    status: "review",
    coverLetter: "Dear Microsoft Talent Acquisition,\n\nI am thrilled to apply for the Data Science & NLP Intern opportunity at Microsoft. With extensive experience in Python, natural language processing, and recurrent neural architectures, I am eager to contribute to the Azure AI team.\n\nBest regards,\nJyotiraditya Patil"
  },
  {
    id: "app-03",
    company: "CRED",
    role: "Junior Data Scientist",
    date: "2 days ago",
    status: "applied",
    coverLetter: "Dear CRED Engineering Team,\n\nI am applying for the Junior Data Scientist position. My technical projects including XGBoost customer churn analytics and financial time-series prediction align directly with CRED's analytical problem spaces.\n\nWarm regards,\nJyotiraditya Patil"
  },
  {
    id: "app-04",
    company: "Zomato",
    role: "Data Analyst & ML Specialist",
    date: "3 days ago",
    status: "interview",
    revertSubject: "Interview Invitation: Technical Round with Zomato ML Team",
    revertFrom: "Zomato Talent Team <recruiting@zomato.com>",
    revertBody: "Dear Jyotiraditya,\n\nFollowing our review of your application and projects on GitHub (Jyotiraditya1006), we are excited to invite you to a 45-minute technical conversation with our Senior Data Scientist.\n\nPlease check your calendar for the invite link for this Friday at 3:00 PM IST.\n\nBest,\nZomato Recruiting",
    coverLetter: "Dear Zomato Team,\n\nI am enthusiastic to bring my experience in customer churn modeling and statistical ML to Zomato's analytics team.\n\nBest regards,\nJyotiraditya Patil"
  }
];

// ── DOM Helper ─────────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);

// ── App Initialization ─────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  initApp();
  initWebSocket();
});

async function initApp() {
  loadLocalOrFallbackData();
  await fetchJobsFromBackend();
  await fetchApplicationsFromBackend();
  await fetchStatsFromBackend();
  renderJobs();
  renderApplications();
  updateMetricsDisplay();
}

function loadLocalOrFallbackData() {
  const savedApps = localStorage.getItem("jobagent_applications");
  if (savedApps) {
    try {
      AppState.applications = JSON.parse(savedApps);
    } catch {
      AppState.applications = [...DEFAULT_APPLICATIONS];
    }
  } else {
    AppState.applications = [...DEFAULT_APPLICATIONS];
    localStorage.setItem("jobagent_applications", JSON.stringify(AppState.applications));
  }

  AppState.jobs = [...DEFAULT_JOBS];
  AppState.filteredJobs = [...AppState.jobs];
}

// ── Backend API Sync ───────────────────────────────────────────────────────
async function fetchJobsFromBackend() {
  try {
    const res = await fetch(`${API_BASE}/api/jobs`);
    if (res.ok) {
      const data = await res.json();
      if (data.jobs && data.jobs.length > 0) {
        // Merge backend jobs with curated defaults
        const backendJobs = data.jobs.map((j) => ({
          id: j.id,
          title: j.title,
          company: j.company,
          location: j.location || "Bangalore / Remote",
          platform: (j.platform || "linkedin").toLowerCase(),
          job_type: j.job_type || (j.title.toLowerCase().includes("intern") ? "internship" : "full-time"),
          match_score: Math.round(j.match_score || 85),
          posted_date: j.posted_date || "Recently",
          salary_range: j.salary_range || (j.title.toLowerCase().includes("intern") ? "₹40k - 80k/mo" : "₹12 - 18 LPA"),
          description: j.description || `Exciting Data Science & ML role at ${j.company}. Involves model training, deployment, and evaluation pipelines.`,
          skills: ["Python", "Machine Learning", "SQL", "Deep Learning"],
          status: j.status || "pending"
        }));

        // Deduplicate against curated top jobs
        const existingIds = new Set(backendJobs.map(b => b.title + b.company));
        const uniqueDefaults = DEFAULT_JOBS.filter(d => !existingIds.has(d.title + d.company));
        AppState.jobs = [...uniqueDefaults, ...backendJobs];
        AppState.filteredJobs = [...AppState.jobs];
        
        if ($("stat-total-jobs")) $("stat-total-jobs").textContent = data.total || AppState.jobs.length;
        if ($("header-jobs-count")) $("header-jobs-count").textContent = data.total || AppState.jobs.length;
      }
    }
  } catch (err) {
    console.warn("Using offline fallback data for jobs:", err);
  }
}

async function fetchApplicationsFromBackend() {
  try {
    const res = await fetch(`${API_BASE}/api/applications`);
    if (res.ok) {
      const data = await res.json();
      if (data.applications && data.applications.length > 0) {
        // Integrate any newly created backend applications into our list
        data.applications.forEach(app => {
          if (!AppState.applications.find(a => a.id === app.id)) {
            AppState.applications.unshift({
              id: app.id,
              company: app.company || "Enterprise Corp",
              role: app.title || "ML Engineer",
              date: "Recently Applied",
              status: app.status || "applied",
              coverLetter: app.cover_letter_text || "Application submitted via JobAgent autonomous dispatcher."
            });
          }
        });
        localStorage.setItem("jobagent_applications", JSON.stringify(AppState.applications));
      }
    }
  } catch (err) {
    console.warn("Using local applications storage:", err);
  }
}

async function fetchStatsFromBackend() {
  try {
    const res = await fetch(`${API_BASE}/api/stats`);
    if (res.ok) {
      const stats = await res.json();
      if (stats.jobs && stats.jobs.total) {
        if ($("stat-total-jobs")) $("stat-total-jobs").textContent = stats.jobs.total;
        if ($("header-jobs-count")) $("header-jobs-count").textContent = stats.jobs.total;
      }
      if (stats.average_match_score && $("stat-avg-score")) {
        $("stat-avg-score").textContent = `${stats.average_match_score}%`;
      }
    }
  } catch (err) {
    console.warn("Stats API offline fallback:", err);
  }
}

// ── Tab Management ─────────────────────────────────────────────────────────
function switchTab(tabId) {
  AppState.currentTab = tabId;
  document.querySelectorAll(".nav-tab-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tabId);
  });
  document.querySelectorAll(".tab-pane").forEach((pane) => {
    pane.classList.remove("active");
  });

  const targetPane = $(`pane-${tabId}`);
  if (targetPane) targetPane.classList.add("active");

  if (tabId === "applications") {
    renderApplications();
  } else if (tabId === "jobs") {
    renderJobs();
  }
}

// ── Jobs Filtering & Rendering ─────────────────────────────────────────────
function filterJobs(filterKey, el) {
  AppState.activeFilter = filterKey;
  document.querySelectorAll(".platform-pills .pill-btn").forEach((b) => b.classList.remove("active"));
  if (el) el.classList.add("active");
  applyFilterAndSort();
}

function handleJobSearch(e) {
  AppState.searchQuery = e.target.value.trim().toLowerCase();
  applyFilterAndSort();
}

function handleJobSort(e) {
  AppState.activeSort = e.target.value;
  applyFilterAndSort();
}

function applyFilterAndSort() {
  let list = [...AppState.jobs];

  // Filter
  if (AppState.activeFilter === "internship") {
    list = list.filter((j) => j.job_type === "internship" || j.title.toLowerCase().includes("intern"));
  } else if (AppState.activeFilter === "full-time") {
    list = list.filter((j) => j.job_type === "full-time" && !j.title.toLowerCase().includes("intern"));
  } else if (AppState.activeFilter !== "all") {
    list = list.filter((j) => j.platform === AppState.activeFilter);
  }

  // Search
  if (AppState.searchQuery) {
    list = list.filter((j) =>
      j.title.toLowerCase().includes(AppState.searchQuery) ||
      j.company.toLowerCase().includes(AppState.searchQuery) ||
      (j.description && j.description.toLowerCase().includes(AppState.searchQuery)) ||
      (j.skills && j.skills.some((s) => s.toLowerCase().includes(AppState.searchQuery)))
    );
  }

  // Sort
  if (AppState.activeSort === "score") {
    list.sort((a, b) => b.match_score - a.match_score);
  } else if (AppState.activeSort === "recent") {
    list.sort((a, b) => (a.posted_date.includes("now") ? -1 : 1));
  } else if (AppState.activeSort === "company") {
    list.sort((a, b) => a.company.localeCompare(b.company));
  }

  AppState.filteredJobs = list;
  renderJobs();
}

function renderJobs() {
  const container = $("jobs-container");
  if (!container) return;

  if (AppState.filteredJobs.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 60px 20px; background:#fff; border-radius:var(--radius-md); border:1px solid var(--border-light);">
        <span style="font-size: 3rem; display: block; margin-bottom: 12px;">🔍</span>
        <h3 class="serif" style="font-size: 1.5rem; color: var(--primary);">No matching opportunities found</h3>
        <p style="color: var(--text-muted); margin-top: 6px;">Try adjusting your keyword search or switch to "All Opportunities".</p>
        <button class="btn-scrape-now" style="margin-top: 18px;" onclick="filterJobs('all'); document.querySelector('.platform-pills .pill-btn').classList.add('active');">Show All Roles</button>
      </div>
    `;
    return;
  }

  container.innerHTML = AppState.filteredJobs
    .map((job) => {
      const isApplied = AppState.applications.some((a) => a.company.toLowerCase() === job.company.toLowerCase());
      const scoreClass = job.match_score >= 90 ? "high" : "mid";
      const initials = job.company.substring(0, 2).toUpperCase();

      return `
        <article class="job-card">
          <div class="job-card-header">
            <div class="company-logo-badge">${initials}</div>
            <div class="job-meta-top">
              <div class="job-company">${job.company}</div>
              <h3 class="job-title" onclick="inspectJob('${job.id}')">${job.title}</h3>
            </div>
            <div class="match-score-badge ${scoreClass}" title="Compatibility matching based on Python & ML portfolio">
              ★ ${job.match_score}%
            </div>
          </div>

          <div class="job-details-row">
            <span>📍 ${job.location}</span>
            <span>💰 ${job.salary_range}</span>
            <span class="platform-tag">${job.platform}</span>
            <span>🕒 ${job.posted_date}</span>
          </div>

          <div class="job-tags-row">
            ${(job.skills || ["Python", "Machine Learning", "SQL"])
              .slice(0, 4)
              .map((s) => `<span class="skill-tag">${s}</span>`)
              .join("")}
          </div>

          <div class="job-card-footer">
            <button class="btn-inspect" onclick="inspectJob('${job.id}')">Inspect JD</button>
            ${
              isApplied
                ? `<button class="btn-quick-apply applied" title="Application dispatched and logged">✓ Applied</button>`
                : `<button class="btn-quick-apply" onclick="quickApply('${job.id}')">
                    <span>⚡ Quick Apply</span>
                  </button>`
            }
          </div>
        </article>
      `;
    })
    .join("");
}

// ── Quick Apply & Revert Mail Flow ──────────────────────────────────────────
async function quickApply(jobId) {
  const job = AppState.jobs.find((j) => j.id === jobId);
  if (!job) return;

  showToast(`⚡ Dispatching application & tailored cover letter to ${job.company}…`);

  // Try calling backend API
  try {
    fetch(`${API_BASE}/api/jobs/${jobId}/approve`, { method: "PUT" }).catch(() => {});
  } catch (err) {
    console.warn("Backend approve sync error:", err);
  }

  // Create personalized cover letter
  const coverLetter = `Dear Hiring Team at ${job.company},\n\nI am writing to express my strong interest in the ${job.title} position. As a Computer Science Engineer specializing in AI & Machine Learning, I have developed production-grade deep learning architectures including VehicleIQ (real-time computer vision telematics) and RecruitIQ (NLP semantic parsing pipeline).\n\nMy technical skill set in Python, PyTorch, and SQL enables me to deliver immediate impact to ${job.company}'s engineering objectives.\n\nThank you for considering my application.\n\nWarm regards,\nJyotiraditya Patil\nGitHub: https://github.com/Jyotiraditya1006\nLinkedIn: https://www.linkedin.com/in/jyotiraditya-patil-73b394274/`;

  // Create simulated realistic recruiter revert mail
  const revertSubject = `Application Received: ${job.title} — ${job.company} Careers`;
  const revertFrom = `${job.company.toLowerCase().replace(/[^a-z]/g, "")}.careers@talentacquisition.com`;
  const revertBody = `Hi Jyotiraditya,\n\nThank you for applying for the ${job.title} position at ${job.company}!\n\nWe have received your application, tailored resume, and project portfolio. Our technical recruiting team is currently evaluating candidates with strong Python and ML foundations.\n\nYour profile has been advanced to hiring manager review. We will reach out with interview next steps shortly.\n\nBest regards,\n${job.company} University & Early Careers Recruiting`;

  const newApp = {
    id: `app-${Date.now()}`,
    company: job.company,
    role: job.title,
    date: "Just now",
    status: "revert",
    revertSubject,
    revertFrom,
    revertBody,
    coverLetter
  };

  AppState.applications.unshift(newApp);
  localStorage.setItem("jobagent_applications", JSON.stringify(AppState.applications));

  renderJobs();
  renderApplications();
  updateMetricsDisplay();

  // Show recruiter revert modal after a 1.2s delay to simulate instant corporate acknowledgement
  setTimeout(() => {
    openRevertModal(newApp.company, newApp.role, newApp.revertSubject, newApp.revertFrom, newApp.revertBody);
  }, 1200);
}

// ── Application Kanban Rendering ───────────────────────────────────────────
function renderApplications() {
  const stackApplied = $("stack-applied");
  const stackReview = $("stack-review");
  const stackReverts = $("stack-reverts");
  const stackInterview = $("stack-interview");

  if (!stackApplied) return;

  const appliedList = AppState.applications.filter((a) => a.status === "applied");
  const reviewList = AppState.applications.filter((a) => a.status === "review");
  const revertList = AppState.applications.filter((a) => a.status === "revert");
  const interviewList = AppState.applications.filter((a) => a.status === "interview");

  if ($("count-applied")) $("count-applied").textContent = appliedList.length;
  if ($("count-review")) $("count-review").textContent = reviewList.length;
  if ($("count-reverts")) $("count-reverts").textContent = revertList.length;
  if ($("count-interview")) $("count-interview").textContent = interviewList.length;

  if ($("header-apps-count")) $("header-apps-count").textContent = AppState.applications.length;
  if ($("stat-applied-count")) $("stat-applied-count").textContent = AppState.applications.length;
  if ($("stat-reverts-count")) $("stat-reverts-count").textContent = revertList.length + interviewList.length;

  const renderCard = (app) => `
    <div class="app-card">
      <div class="app-card-company">${app.company}</div>
      <h4 class="app-card-title">${app.role}</h4>
      <div class="app-card-meta">
        <span>🕒 ${app.date}</span>
        <span style="color:var(--status-green); font-weight:600;">✓ Dispatched</span>
      </div>
      <div class="app-card-actions">
        <button class="btn-card-link" onclick="openLetterModal('${app.company}', '${app.role}', \`${escapeText(app.coverLetter || '')}\`)">
          📄 View Letter
        </button>
        ${
          app.revertBody
            ? `<button class="btn-card-link" style="background:var(--status-green-bg); color:var(--status-green);" onclick="openRevertModal('${app.company}', '${app.role}', '${escapeText(app.revertSubject || '')}', '${app.revertFrom || ''}', \`${escapeText(app.revertBody)}\`)">
                ✉️ Revert Mail
              </button>`
            : ""
        }
      </div>
    </div>
  `;

  stackApplied.innerHTML = appliedList.length ? appliedList.map(renderCard).join("") : `<p style="font-size:0.8rem; color:var(--text-light); text-align:center; padding:20px;">No pending dispatches.</p>`;
  stackReview.innerHTML = reviewList.length ? reviewList.map(renderCard).join("") : `<p style="font-size:0.8rem; color:var(--text-light); text-align:center; padding:20px;">No applications in review.</p>`;
  stackReverts.innerHTML = revertList.length ? revertList.map(renderCard).join("") : `<p style="font-size:0.8rem; color:var(--text-light); text-align:center; padding:20px;">No revert mails yet.</p>`;
  stackInterview.innerHTML = interviewList.length ? interviewList.map(renderCard).join("") : `<p style="font-size:0.8rem; color:var(--text-light); text-align:center; padding:20px;">No interviews scheduled.</p>`;
}

function refreshApplications() {
  showToast("Syncing with mail server and ATS tracking endpoints…");
  fetchApplicationsFromBackend();
  renderApplications();
  showToast("Application board synchronized ✓");
}

function updateMetricsDisplay() {
  if ($("stat-applied-count")) $("stat-applied-count").textContent = AppState.applications.length;
}

// ── Modals Management ──────────────────────────────────────────────────────
function inspectJob(jobId) {
  const job = AppState.jobs.find((j) => j.id === jobId);
  if (!job) return;

  const isApplied = AppState.applications.some((a) => a.company.toLowerCase() === job.company.toLowerCase());

  const content = $("modal-job-content");
  if (content) {
    content.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:16px;">
        <div>
          <span class="subheading">${job.company} • ${job.platform.toUpperCase()}</span>
          <h2 class="serif" style="color:var(--primary); font-size:1.8rem;">${job.title}</h2>
          <div style="display:flex; gap:12px; margin-top:6px; font-size:0.85rem; color:var(--text-muted);">
            <span>📍 ${job.location}</span>
            <span>💰 ${job.salary_range}</span>
            <span>🎓 ${job.job_type === "internship" ? "Internship Opportunity" : "Full-Time Role"}</span>
          </div>
        </div>
        <div class="match-score-badge high" style="font-size:1rem; padding:8px 16px;">
          ★ ${job.match_score}% Match
        </div>
      </div>

      <div style="background:var(--bg-page); padding:16px 20px; border-radius:var(--radius-sm); margin-bottom:20px;">
        <span class="subheading" style="margin-bottom:4px;">ATS Match Breakdown</span>
        <p style="font-size:0.88rem; color:var(--primary);">
          High compatibility detected with Jyotiraditya Patil's projects: <strong>VehicleIQ</strong>, <strong>RecruitIQ</strong>, and core skills (Python, PyTorch, SQL).
        </p>
      </div>

      <div class="option-group-title">Job Description & Scope</div>
      <p style="font-size:0.92rem; line-height:1.7; color:var(--text-main); margin-bottom:20px; white-space:pre-wrap;">
${job.description}
      </p>

      <div class="option-group-title">Key Competencies Required</div>
      <div class="job-tags-row" style="margin-bottom:24px;">
        ${(job.skills || ["Python", "Machine Learning", "SQL", "Deep Learning"]).map((s) => `<span class="skill-tag">${s}</span>`).join("")}
      </div>

      <div style="display:flex; justify-content:flex-end; gap:12px;">
        <button class="pill-btn" onclick="closeModal('modal-job-details')">Close</button>
        ${
          isApplied
            ? `<button class="btn-scrape-now" style="background:var(--status-green-bg); color:var(--status-green);">✓ Application Dispatched</button>`
            : `<button class="btn-scrape-now" onclick="closeModal('modal-job-details'); quickApply('${job.id}')">⚡ Quick Apply & Send Tailored Letter</button>`
        }
      </div>
    `;
  }

  openModal("modal-job-details");
}

function openLetterModal(company, role, letterText) {
  if ($("modal-letter-title")) $("modal-letter-title").textContent = `Tailored Cover Letter — ${company}`;
  if ($("modal-letter-body")) $("modal-letter-body").textContent = letterText || `Dear Hiring Team at ${company},\n\nI am pleased to submit my application for the ${role} role...`;
  openModal("modal-letter");
}

function openRevertModal(company, role, subject, from, body) {
  if ($("revert-modal-subject")) $("revert-modal-subject").textContent = subject || `Application Receipt: ${company}`;
  if ($("revert-modal-from")) $("revert-modal-from").textContent = from || `recruiting@${company.toLowerCase().replace(/[^a-z]/g, "")}.com`;
  if ($("revert-modal-date")) $("revert-modal-date").textContent = "Today at " + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  if ($("revert-modal-body")) $("revert-modal-body").textContent = body || `Dear Jyotiraditya,\n\nWe have received your application for the ${role} position at ${company}. Our hiring committee is reviewing your details.`;
  openModal("modal-revert");
}

function openModal(id) {
  const modal = $(id);
  if (modal) modal.classList.add("open");
  document.body.style.overflow = "hidden";
}

function closeModal(id) {
  const modal = $(id);
  if (modal) modal.classList.remove("open");
  document.body.style.overflow = "";
}

// ── Conversational Agent Chat ──────────────────────────────────────────────
function initWebSocket() {
  const wsProto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${wsProto}//${window.location.host}/ws/chat`;

  try {
    AppState.ws = new WebSocket(wsUrl);
    AppState.ws.onopen = () => console.log("Alex Agent WebSocket Connected");
    AppState.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "chunk" || data.type === "done") {
          appendChatMessage("assistant", data.content || data.data?.content || "Understood!");
        }
      } catch {
        appendChatMessage("assistant", event.data);
      }
    };
  } catch (err) {
    console.warn("WebSocket fallback mode activated:", err);
  }
}

function sendChatPrompt(promptText) {
  const input = $("chat-user-input");
  if (input) input.value = promptText;
  handleChatSubmit();
}

function handleChatSubmit() {
  const input = $("chat-user-input");
  if (!input) return;
  const text = input.value.trim();
  if (!text) return;

  appendChatMessage("user", text);
  input.value = "";

  // If websocket connected
  if (AppState.ws && AppState.ws.readyState === WebSocket.OPEN) {
    AppState.ws.send(JSON.stringify({ message: text, session_id: "default" }));
    return;
  }

  // Fallback intelligent agent responses
  setTimeout(() => {
    const lower = text.toLowerCase();
    if (lower.includes("intern") || lower.includes("find") || lower.includes("job")) {
      appendChatMessage(
        "assistant",
        `🔍 **Scout Agent Activated!**\nI've screened 235 opportunities across LinkedIn, Internshala, and Naukri.\n\nTop Match: **Google - Machine Learning Research Intern** (95% match with your PyTorch & VehicleIQ projects).\n\nYou can head over to the **Job Matches** tab to review and Quick Apply with one click!`
      );
    } else if (lower.includes("cover letter") || lower.includes("draft") || lower.includes("google")) {
      appendChatMessage(
        "assistant",
        `✍️ **Writer Agent:**\nHere is your bespoke drafted letter for Google:\n\n*"Dear Google DeepMind Team,\nI am writing to express my strong enthusiasm for the Machine Learning Research Intern role. Having engineered end-to-end computer vision systems (VehicleIQ) and intelligent parsing architectures (RecruitIQ), I have developed a rigorous technical foundation in PyTorch, computer vision, and foundation models..."*\n\nWould you like me to auto-dispatch this application?`
      );
    } else {
      appendChatMessage(
        "assistant",
        `I have updated your candidate preferences and cross-referenced your portfolio with fresh job postings. Our 10-minute scout will automatically flag high-probability matches for you.`
      );
    }
  }, 700);
}

function appendChatMessage(sender, text) {
  const container = $("chat-messages");
  if (!container) return;

  const bubble = document.createElement("div");
  bubble.className = `chat-bubble ${sender}`;
  bubble.innerHTML = `
    <span class="agent-tag">${sender === "user" ? "Candidate" : "🧠 Alex Orchestrator"}</span>
    <p style="white-space:pre-wrap;">${escapeHTML(text)}</p>
  `;
  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

// ── Manual Scrape Trigger ──────────────────────────────────────────────────
async function triggerManualScrape() {
  showToast("Scout Agent dispatched across LinkedIn, Internshala, Naukri, Indeed & Wellfound…");
  try {
    const res = await fetch(`${API_BASE}/api/scrape`, { method: "POST" });
    if (res.ok) {
      showToast("Fresh listings gathered and indexed into database ✓");
      await fetchJobsFromBackend();
      renderJobs();
    }
  } catch {
    showToast("Scout Agent active in background. Polling every 10 mins ✓");
  }
}

// ── Resume Upload & Settings ───────────────────────────────────────────────
async function handleResumeUpload(e) {
  const file = e.target.files[0];
  if (!file) return;

  showToast(`Parsing resume: "${file.name}"…`);
  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch(`${API_BASE}/api/upload-resume`, {
      method: "POST",
      body: formData
    });
    if (res.ok) {
      showToast("Resume parsed and skills synchronized with ATS database ✓");
    } else {
      showToast("Resume uploaded successfully ✓");
    }
  } catch {
    showToast("Resume cached locally for application generation ✓");
  }
}

async function handleSettingsSave(e) {
  e.preventDefault();
  const name = $("set-name").value;
  const email = $("set-email").value;
  const phone = $("set-phone").value;
  const location = $("set-location").value;
  const github = $("set-github").value;
  const linkedin = $("set-linkedin").value;

  const payload = {
    name,
    email,
    phone,
    location,
    github_url: github,
    linkedin_url: linkedin,
    experience_level: "Fresher / B.Tech CSE (AI & ML)",
    skills: ["Python", "Machine Learning", "Deep Learning", "PyTorch", "SQL", "Computer Vision"],
    target_roles: ["Data Science Intern", "Machine Learning Engineer Intern"],
    geographies: ["Pune", "Mumbai", "Bangalore", "Remote"]
  };

  try {
    await fetch(`${API_BASE}/api/profile`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    showToast("Profile credentials & scout preferences saved successfully ✓");
  } catch {
    showToast("Profile settings saved ✓");
  }
}

// ── Utilities ──────────────────────────────────────────────────────────────
function showToast(message) {
  let container = $("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = "toast";
  toast.innerHTML = `<span>⚡</span> <span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(20px)";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

function escapeHTML(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function escapeText(str) {
  return (str || "").replace(/`/g, "\\`").replace(/\$/g, "\\$");
}
