import { BrowserRouter, Routes, Route, useNavigate, Navigate } from "react-router-dom";
import { useState } from "react";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { UploadContext, useUploadStatus } from "./context/UploadContext";
import Navbar from "./components/ui/Navbar";
import LandingPage from "./pages/Landing";
import SignIn from "./pages/SignIn";
import SignUp from "./pages/SignUp";
import UploadPage from "./pages/Upload";
import VoiceScreenPage from "./pages/VoiceScreen";
import InterviewPage from "./pages/Interview";
import ReportPage from "./pages/Report";
import HistoryPage from "./pages/History";
import "./design/styles.css";

function AuthRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return null;
  return isAuthenticated ? children : <Navigate to="/signin" replace />;
}

function GuestRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return null;
  return !isAuthenticated ? children : <Navigate to="/upload" replace />;
}

function ProtectedRoute({ children }) {
  const { isUploaded } = useUploadStatus();
  return isUploaded ? children : <Navigate to="/upload" replace />;
}

function ScreeningGate({ children }) {
  const { isUploaded } = useUploadStatus();
  if (!isUploaded) return <Navigate to="/upload" replace />;
  return children;
}

function InterviewGate({ children }) {
  const { isUploaded, interviewId } = useUploadStatus();
  if (!isUploaded) return <Navigate to="/upload" replace />;
  if (!interviewId) return <Navigate to="/voice-screen" replace />;
  return children;
}

function ReportGate({ children }) {
  const { isUploaded, candidateId } = useUploadStatus();
  if (!isUploaded) return <Navigate to="/upload" replace />;
  if (!candidateId) return <Navigate to="/upload" replace />;
  return children;
}

function AppContent() {
  const navigate = useNavigate();
  const [isUploaded, setIsUploaded] = useState(false);
  const [candidateId, setCandidateId] = useState(null);
  const [resumeData, setResumeData] = useState(null);
  const [confidenceScores, setConfidenceScores] = useState(null);
  const [interviewId, setInterviewId] = useState(null);

  const nav = (path) => navigate(`/${path.toLowerCase().replace(/\s+/g, "-")}`);

  return (
    <UploadContext.Provider value={{
      isUploaded, setIsUploaded,
      candidateId, setCandidateId,
      resumeData, setResumeData,
      confidenceScores, setConfidenceScores,
      interviewId, setInterviewId,
    }}>
      <div className="platform-root">
        <div className="noise" />
        <Navbar />
        <div className="content">
          <Routes>
            <Route path="/" element={<LandingPage onNavigate={nav} />} />
            <Route path="/signin" element={<GuestRoute><SignIn onNavigate={nav} /></GuestRoute>} />
            <Route path="/sign-in" element={<GuestRoute><SignIn onNavigate={nav} /></GuestRoute>} />
            <Route path="/signup" element={<GuestRoute><SignUp onNavigate={nav} /></GuestRoute>} />
            <Route path="/sign-up" element={<GuestRoute><SignUp onNavigate={nav} /></GuestRoute>} />
            <Route path="/upload" element={<AuthRoute><UploadPage onNavigate={nav} /></AuthRoute>} />
            <Route path="/voice-screen" element={<AuthRoute><ScreeningGate><VoiceScreenPage onNavigate={nav} /></ScreeningGate></AuthRoute>} />
            <Route path="/interview" element={<AuthRoute><InterviewGate><InterviewPage onNavigate={nav} /></InterviewGate></AuthRoute>} />
            <Route path="/report" element={<AuthRoute><ReportGate><ReportPage /></ReportGate></AuthRoute>} />
            <Route path="/history" element={<AuthRoute><HistoryPage /></AuthRoute>} />
          </Routes>
        </div>
      </div>
    </UploadContext.Provider >
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </BrowserRouter>
  );
}
