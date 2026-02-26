/**
 * API Service Layer
 * Handles all HTTP requests to the backend with JWT token management.
 */

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

function getToken() {
  return localStorage.getItem("token");
}

async function request(endpoint, options = {}) {
  const token = getToken();
  const headers = { ...options.headers };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // Don't set Content-Type for FormData (browser sets it with boundary)
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  // Handle audio/binary responses
  if (options.responseType === "blob") {
    if (!res.ok) throw new Error("Request failed");
    return res.blob();
  }

  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.detail || "Request failed");
  }

  return data;
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
//  AUTH
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export async function signup(name, email, password) {
  return request("/api/auth/signup", {
    method: "POST",
    body: JSON.stringify({ name, email, password }),
  });
}

export async function signin(email, password) {
  return request("/api/auth/signin", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function getMe() {
  return request("/api/auth/me");
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
//  RESUME
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export async function parseResume(file) {
  const formData = new FormData();
  formData.append("file", file);
  return request("/api/parse-resume", {
    method: "POST",
    body: formData,
  });
}

export async function getConfidenceScores(candidateId) {
  return request("/api/confidence-scores", {
    method: "POST",
    body: JSON.stringify({ candidate_id: candidateId }),
  });
}

export async function fullPipeline(file) {
  const formData = new FormData();
  formData.append("file", file);
  return request("/api/full-pipeline", {
    method: "POST",
    body: formData,
  });
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
//  CANDIDATES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export async function getCandidates() {
  return request("/api/candidates");
}

export async function getCandidate(candidateId) {
  return request(`/api/candidates/${candidateId}`);
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
//  SCREENING
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export async function startScreening(candidateId, targetRole = "") {
  return request("/api/start-screening", {
    method: "POST",
    body: JSON.stringify({ candidate_id: candidateId, target_role: targetRole }),
  });
}

export async function sendScreeningResponse(interviewId, audioBlob) {
  const formData = new FormData();
  formData.append("file", audioBlob, `response_${Date.now()}.wav`);
  return request(`/api/screening/respond?interview_id=${interviewId}`, {
    method: "POST",
    body: formData,
  });
}

export async function getInterview(interviewId) {
  return request(`/api/interviews/${interviewId}`);
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
//  DEEP INTERVIEW
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export async function generateInterviewPlan(candidateId) {
  return request("/api/interview/generate-plan", {
    method: "POST",
    body: JSON.stringify({ candidate_id: candidateId }),
  });
}

export async function startDeepInterview(candidateId, deepInterviewId) {
  return request("/api/interview/start", {
    method: "POST",
    body: JSON.stringify({
      candidate_id: candidateId,
      deep_interview_id: deepInterviewId,
    }),
  });
}

export async function sendInterviewResponse(deepInterviewId, audioBlob) {
  const formData = new FormData();
  formData.append("file", audioBlob, `deep_response_${Date.now()}.wav`);
  return request(`/api/interview/respond?deep_interview_id=${deepInterviewId}`, {
    method: "POST",
    body: formData,
  });
}

export async function endInterview(deepInterviewId) {
  return request("/api/interview/end", {
    method: "POST",
    body: JSON.stringify({ deep_interview_id: deepInterviewId }),
  });
}

export async function getDeepInterview(deepInterviewId) {
  return request(`/api/interview/deep/${deepInterviewId}`);
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
//  REPORT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export async function generateReport(candidateId) {
  return request("/api/interview/generate-report", {
    method: "POST",
    body: JSON.stringify({ candidate_id: candidateId }),
  });
}

export async function getReport(candidateId) {
  return request(`/api/interview/report/${candidateId}`);
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
//  SESSION HISTORY
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export async function getCandidateSessions(candidateId) {
  return request(`/api/candidates/${candidateId}/sessions`);
}

export async function getMyReports() {
  return request("/api/my/reports");
}

export async function getScreeningInterviews(candidateId) {
  return request(`/api/candidates/${candidateId}/interviews`);
}

export async function getDeepInterviews(candidateId) {
  return request(`/api/candidates/${candidateId}/deep-interviews`);
}

export async function getCandidateReports(candidateId) {
  return request(`/api/candidates/${candidateId}/reports`);
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
//  AUDIO
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export function getAudioUrl(fileId) {
  return `${API_BASE}/api/audio/${fileId}`;
}
