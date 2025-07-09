import React, { useState, useEffect, createContext, useContext } from 'react';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

// Theme Context
const ThemeContext = createContext();

// Auth Context
const AuthContext = createContext();

// Theme Provider
const ThemeProvider = ({ children }) => {
  const [theme, setTheme] = useState('light');

  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme);
    document.documentElement.setAttribute('data-theme', savedTheme);
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    localStorage.setItem('theme', newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

// Auth Provider
const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCurrentUser();
  }, []);

  const fetchCurrentUser = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/me`);
      const userData = await response.json();
      setUser(userData);
    } catch (error) {
      console.error('Error fetching user:', error);
    } finally {
      setLoading(false);
    }
  };

  const login = async (authCode) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/google`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code: authCode, user_id: 'demo_user' }),
      });
      const data = await response.json();
      setUser(data.user);
      localStorage.setItem('auth_token', data.token);
      return data;
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('auth_token');
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading, fetchCurrentUser }}>
      {children}
    </AuthContext.Provider>
  );
};

// Modal Component
const Modal = ({ isOpen, onClose, title, children }) => {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{title}</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <div className="modal-body">
          {children}
        </div>
      </div>
    </div>
  );
};

// Profile Settings Component
const ProfileSettings = ({ isOpen, onClose }) => {
  const { user, fetchCurrentUser } = useContext(AuthContext);
  const [profileData, setProfileData] = useState({
    name: '',
    email: '',
    profile_picture: '',
    theme: 'light'
  });
  const [integrations, setIntegrations] = useState([]);

  useEffect(() => {
    if (user) {
      setProfileData({
        name: user.name || '',
        email: user.email || '',
        profile_picture: user.profile_picture || '',
        theme: user.theme || 'light'
      });
    }
    fetchIntegrations();
  }, [user]);

  const fetchIntegrations = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/integrations`);
      const data = await response.json();
      setIntegrations(data);
    } catch (error) {
      console.error('Error fetching integrations:', error);
    }
  };

  const updateProfile = async (e) => {
    e.preventDefault();
    try {
      await fetch(`${API_BASE_URL}/api/auth/me`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(profileData),
      });
      await fetchCurrentUser();
      alert('Profile updated successfully!');
    } catch (error) {
      console.error('Error updating profile:', error);
    }
  };

  const connectIntegration = async (integrationType) => {
    try {
      const credentials = {};
      if (integrationType === 'stripe') {
        const apiKey = prompt('Enter your Stripe API Key:');
        if (!apiKey) return;
        credentials.api_key = apiKey;
      } else if (integrationType === 'gmail') {
        alert('Gmail integration will redirect to Google OAuth');
        // In a real implementation, this would redirect to Google OAuth
        credentials.oauth_token = 'mock_gmail_token';
      } else if (integrationType === 'google_calendar') {
        alert('Google Calendar integration will redirect to Google OAuth');
        credentials.oauth_token = 'mock_calendar_token';
      }

      await fetch(`${API_BASE_URL}/api/integrations`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          integration_type: integrationType,
          credentials: credentials,
          settings: {}
        }),
      });
      
      fetchIntegrations();
      alert(`${integrationType} integration connected successfully!`);
    } catch (error) {
      console.error('Error connecting integration:', error);
    }
  };

  const disconnectIntegration = async (integrationType) => {
    try {
      await fetch(`${API_BASE_URL}/api/integrations/${integrationType}`, {
        method: 'DELETE',
      });
      fetchIntegrations();
      alert(`${integrationType} integration disconnected successfully!`);
    } catch (error) {
      console.error('Error disconnecting integration:', error);
    }
  };

  const getIntegrationStatus = (type) => {
    return integrations.find(i => i.integration_type === type)?.is_connected || false;
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Profile & Settings">
      <div className="profile-settings">
        <div className="settings-section">
          <h3>Profile Information</h3>
          <form onSubmit={updateProfile}>
            <div className="form-group">
              <label>Name</label>
              <input
                type="text"
                value={profileData.name}
                onChange={(e) => setProfileData({...profileData, name: e.target.value})}
                className="form-input"
              />
            </div>
            <div className="form-group">
              <label>Email</label>
              <input
                type="email"
                value={profileData.email}
                onChange={(e) => setProfileData({...profileData, email: e.target.value})}
                className="form-input"
                disabled
              />
            </div>
            <div className="form-group">
              <label>Profile Picture URL</label>
              <input
                type="url"
                value={profileData.profile_picture}
                onChange={(e) => setProfileData({...profileData, profile_picture: e.target.value})}
                className="form-input"
              />
            </div>
            <button type="submit" className="btn btn-primary">Update Profile</button>
          </form>
        </div>

        <div className="settings-section">
          <h3>Integrations</h3>
          
          <div className="integration-item">
            <div className="integration-info">
              <h4>Stripe</h4>
              <p>Connect your Stripe account to manage payments</p>
            </div>
            <div className="integration-actions">
              {getIntegrationStatus('stripe') ? (
                <button 
                  className="btn btn-danger"
                  onClick={() => disconnectIntegration('stripe')}
                >
                  Disconnect
                </button>
              ) : (
                <button 
                  className="btn btn-primary"
                  onClick={() => connectIntegration('stripe')}
                >
                  Connect
                </button>
              )}
            </div>
          </div>

          <div className="integration-item">
            <div className="integration-info">
              <h4>Gmail</h4>
              <p>Connect Gmail to send and receive emails</p>
            </div>
            <div className="integration-actions">
              {getIntegrationStatus('gmail') ? (
                <button 
                  className="btn btn-danger"
                  onClick={() => disconnectIntegration('gmail')}
                >
                  Disconnect
                </button>
              ) : (
                <button 
                  className="btn btn-primary"
                  onClick={() => connectIntegration('gmail')}
                >
                  Connect
                </button>
              )}
            </div>
          </div>

          <div className="integration-item">
            <div className="integration-info">
              <h4>Google Calendar</h4>
              <p>Connect Google Calendar to manage meetings</p>
            </div>
            <div className="integration-actions">
              {getIntegrationStatus('google_calendar') ? (
                <button 
                  className="btn btn-danger"
                  onClick={() => disconnectIntegration('google_calendar')}
                >
                  Disconnect
                </button>
              ) : (
                <button 
                  className="btn btn-primary"
                  onClick={() => connectIntegration('google_calendar')}
                >
                  Connect
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </Modal>
  );
};

// Login Component
const LoginPage = () => {
  const { login } = useContext(AuthContext);

  const handleGoogleLogin = async () => {
    try {
      // In a real implementation, this would redirect to Google OAuth
      const mockAuthCode = 'mock_google_auth_code_' + Date.now();
      await login(mockAuthCode);
    } catch (error) {
      console.error('Login failed:', error);
    }
  };

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-card">
          <h1>Business Hub</h1>
          <p>Manage your business with ease</p>
          <button className="btn btn-primary google-login-btn" onClick={handleGoogleLogin}>
            <span className="google-icon">G</span>
            Continue with Google
          </button>
        </div>
      </div>
    </div>
  );
};

// Main App Component
function App() {
  const { user, loading } = useContext(AuthContext);
  const { theme, toggleTheme } = useContext(ThemeContext);
  const [currentView, setCurrentView] = useState('dashboard');
  const [clients, setClients] = useState([]);
  const [projects, setProjects] = useState([]);
  const [teamMembers, setTeamMembers] = useState([]);
  const [payments, setPayments] = useState([]);
  const [upcomingMeetings, setUpcomingMeetings] = useState([]);
  const [dashboardStats, setDashboardStats] = useState({});
  const [showProfileSettings, setShowProfileSettings] = useState(false);
  
  // Modal states
  const [clientModal, setClientModal] = useState({ isOpen: false, data: null });
  const [projectModal, setProjectModal] = useState({ isOpen: false, data: null });
  const [teamMemberModal, setTeamMemberModal] = useState({ isOpen: false, data: null });
  const [paymentModal, setPaymentModal] = useState({ isOpen: false, data: null });

  // Fetch data functions
  const fetchClients = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/clients`);
      const data = await response.json();
      setClients(data);
    } catch (error) {
      console.error('Error fetching clients:', error);
    }
  };

  const fetchProjects = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/projects`);
      const data = await response.json();
      setProjects(data);
    } catch (error) {
      console.error('Error fetching projects:', error);
    }
  };

  const fetchTeamMembers = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/team-members`);
      const data = await response.json();
      setTeamMembers(data);
    } catch (error) {
      console.error('Error fetching team members:', error);
    }
  };

  const fetchPayments = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/payments`);
      const data = await response.json();
      setPayments(data);
    } catch (error) {
      console.error('Error fetching payments:', error);
    }
  };

  const fetchUpcomingMeetings = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/calendar/upcoming`);
      const data = await response.json();
      setUpcomingMeetings(data.upcoming_meetings || []);
    } catch (error) {
      console.error('Error fetching upcoming meetings:', error);
    }
  };

  const fetchDashboardStats = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/dashboard/stats`);
      const data = await response.json();
      setDashboardStats(data);
    } catch (error) {
      console.error('Error fetching dashboard stats:', error);
    }
  };

  useEffect(() => {
    if (user) {
      fetchClients();
      fetchProjects();
      fetchTeamMembers();
      fetchPayments();
      fetchUpcomingMeetings();
      fetchDashboardStats();
    }
  }, [user]);

  // Form Components
  const ClientForm = ({ onSubmit, initialData = {} }) => {
    const [formData, setFormData] = useState({
      name: initialData.name || '',
      email: initialData.email || '',
      phone: initialData.phone || '',
      company: initialData.company || '',
      address: initialData.address || ''
    });

    const handleSubmit = (e) => {
      e.preventDefault();
      onSubmit(formData);
    };

    return (
      <form onSubmit={handleSubmit} className="modal-form">
        <div className="form-group">
          <label>Name</label>
          <input
            type="text"
            required
            value={formData.name}
            onChange={(e) => setFormData({...formData, name: e.target.value})}
            className="form-input"
          />
        </div>
        <div className="form-group">
          <label>Email</label>
          <input
            type="email"
            required
            value={formData.email}
            onChange={(e) => setFormData({...formData, email: e.target.value})}
            className="form-input"
          />
        </div>
        <div className="form-group">
          <label>Phone</label>
          <input
            type="tel"
            value={formData.phone}
            onChange={(e) => setFormData({...formData, phone: e.target.value})}
            className="form-input"
          />
        </div>
        <div className="form-group">
          <label>Company</label>
          <input
            type="text"
            value={formData.company}
            onChange={(e) => setFormData({...formData, company: e.target.value})}
            className="form-input"
          />
        </div>
        <div className="form-group">
          <label>Address</label>
          <textarea
            value={formData.address}
            onChange={(e) => setFormData({...formData, address: e.target.value})}
            rows={3}
            className="form-input"
          />
        </div>
        <button type="submit" className="btn btn-primary">
          {initialData.id ? 'Update Client' : 'Create Client'}
        </button>
      </form>
    );
  };

  const ProjectForm = ({ onSubmit, initialData = {} }) => {
    const [formData, setFormData] = useState({
      name: initialData.name || '',
      description: initialData.description || '',
      client_id: initialData.client_id || '',
      budget: initialData.budget || '',
      start_date: initialData.start_date || '',
      end_date: initialData.end_date || ''
    });

    const handleSubmit = (e) => {
      e.preventDefault();
      onSubmit(formData);
    };

    return (
      <form onSubmit={handleSubmit} className="modal-form">
        <div className="form-group">
          <label>Project Name</label>
          <input
            type="text"
            required
            value={formData.name}
            onChange={(e) => setFormData({...formData, name: e.target.value})}
            className="form-input"
          />
        </div>
        <div className="form-group">
          <label>Client</label>
          <select
            required
            value={formData.client_id}
            onChange={(e) => setFormData({...formData, client_id: e.target.value})}
            className="form-input"
          >
            <option value="">Select a client</option>
            {clients.map(client => (
              <option key={client.id} value={client.id}>{client.name}</option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label>Description</label>
          <textarea
            value={formData.description}
            onChange={(e) => setFormData({...formData, description: e.target.value})}
            rows={3}
            className="form-input"
          />
        </div>
        <div className="form-group">
          <label>Budget</label>
          <input
            type="number"
            step="0.01"
            value={formData.budget}
            onChange={(e) => setFormData({...formData, budget: e.target.value})}
            className="form-input"
          />
        </div>
        <div className="form-group">
          <label>Start Date</label>
          <input
            type="date"
            value={formData.start_date}
            onChange={(e) => setFormData({...formData, start_date: e.target.value})}
            className="form-input"
          />
        </div>
        <div className="form-group">
          <label>End Date</label>
          <input
            type="date"
            value={formData.end_date}
            onChange={(e) => setFormData({...formData, end_date: e.target.value})}
            className="form-input"
          />
        </div>
        <button type="submit" className="btn btn-primary">
          {initialData.id ? 'Update Project' : 'Create Project'}
        </button>
      </form>
    );
  };

  const TeamMemberForm = ({ onSubmit, initialData = {} }) => {
    const [formData, setFormData] = useState({
      name: initialData.name || '',
      email: initialData.email || '',
      phone: initialData.phone || '',
      role: initialData.role || '',
      member_type: initialData.member_type || 'internal',
      hourly_rate: initialData.hourly_rate || ''
    });

    const handleSubmit = (e) => {
      e.preventDefault();
      onSubmit(formData);
    };

    return (
      <form onSubmit={handleSubmit} className="modal-form">
        <div className="form-group">
          <label>Name</label>
          <input
            type="text"
            required
            value={formData.name}
            onChange={(e) => setFormData({...formData, name: e.target.value})}
            className="form-input"
          />
        </div>
        <div className="form-group">
          <label>Email</label>
          <input
            type="email"
            required
            value={formData.email}
            onChange={(e) => setFormData({...formData, email: e.target.value})}
            className="form-input"
          />
        </div>
        <div className="form-group">
          <label>Phone</label>
          <input
            type="tel"
            value={formData.phone}
            onChange={(e) => setFormData({...formData, phone: e.target.value})}
            className="form-input"
          />
        </div>
        <div className="form-group">
          <label>Role</label>
          <input
            type="text"
            required
            value={formData.role}
            onChange={(e) => setFormData({...formData, role: e.target.value})}
            className="form-input"
          />
        </div>
        <div className="form-group">
          <label>Member Type</label>
          <select
            value={formData.member_type}
            onChange={(e) => setFormData({...formData, member_type: e.target.value})}
            className="form-input"
          >
            <option value="internal">Internal Team</option>
            <option value="freelancer">Freelancer</option>
          </select>
        </div>
        <div className="form-group">
          <label>Hourly Rate</label>
          <input
            type="number"
            step="0.01"
            value={formData.hourly_rate}
            onChange={(e) => setFormData({...formData, hourly_rate: e.target.value})}
            className="form-input"
          />
        </div>
        <button type="submit" className="btn btn-primary">
          {initialData.id ? 'Update Team Member' : 'Add Team Member'}
        </button>
      </form>
    );
  };

  const PaymentRequestForm = ({ onSubmit }) => {
    const [formData, setFormData] = useState({
      amount: '',
      currency: 'usd',
      description: '',
      client_id: '',
      project_id: ''
    });

    const handleSubmit = (e) => {
      e.preventDefault();
      onSubmit(formData);
    };

    return (
      <form onSubmit={handleSubmit} className="modal-form">
        <div className="form-group">
          <label>Amount</label>
          <input
            type="number"
            step="0.01"
            required
            value={formData.amount}
            onChange={(e) => setFormData({...formData, amount: e.target.value})}
            className="form-input"
          />
        </div>
        <div className="form-group">
          <label>Currency</label>
          <select
            value={formData.currency}
            onChange={(e) => setFormData({...formData, currency: e.target.value})}
            className="form-input"
          >
            <option value="usd">USD</option>
            <option value="eur">EUR</option>
            <option value="gbp">GBP</option>
          </select>
        </div>
        <div className="form-group">
          <label>Client</label>
          <select
            value={formData.client_id}
            onChange={(e) => setFormData({...formData, client_id: e.target.value})}
            className="form-input"
          >
            <option value="">Select a client</option>
            {clients.map(client => (
              <option key={client.id} value={client.id}>{client.name}</option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label>Project</label>
          <select
            value={formData.project_id}
            onChange={(e) => setFormData({...formData, project_id: e.target.value})}
            className="form-input"
          >
            <option value="">Select a project</option>
            {projects.map(project => (
              <option key={project.id} value={project.id}>{project.name}</option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label>Description</label>
          <textarea
            value={formData.description}
            onChange={(e) => setFormData({...formData, description: e.target.value})}
            rows={3}
            className="form-input"
          />
        </div>
        <button type="submit" className="btn btn-success">
          Request Payment
        </button>
      </form>
    );
  };

  // Handle form submissions
  const handleClientSubmit = async (formData) => {
    try {
      const url = clientModal.data ? 
        `${API_BASE_URL}/api/clients/${clientModal.data.id}` : 
        `${API_BASE_URL}/api/clients`;
      const method = clientModal.data ? 'PUT' : 'POST';
      
      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });
      
      if (response.ok) {
        fetchClients();
        setClientModal({ isOpen: false, data: null });
      }
    } catch (error) {
      console.error('Error saving client:', error);
    }
  };

  const handleProjectSubmit = async (formData) => {
    try {
      const url = projectModal.data ? 
        `${API_BASE_URL}/api/projects/${projectModal.data.id}` : 
        `${API_BASE_URL}/api/projects`;
      const method = projectModal.data ? 'PUT' : 'POST';
      
      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });
      
      if (response.ok) {
        fetchProjects();
        setProjectModal({ isOpen: false, data: null });
      }
    } catch (error) {
      console.error('Error saving project:', error);
    }
  };

  const handleTeamMemberSubmit = async (formData) => {
    try {
      const url = teamMemberModal.data ? 
        `${API_BASE_URL}/api/team-members/${teamMemberModal.data.id}` : 
        `${API_BASE_URL}/api/team-members`;
      const method = teamMemberModal.data ? 'PUT' : 'POST';
      
      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });
      
      if (response.ok) {
        fetchTeamMembers();
        setTeamMemberModal({ isOpen: false, data: null });
      }
    } catch (error) {
      console.error('Error saving team member:', error);
    }
  };

  const handlePaymentRequest = async (formData) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/payments/v1/checkout/session`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });
      
      if (response.ok) {
        const data = await response.json();
        window.location.href = data.url;
      }
    } catch (error) {
      console.error('Error creating payment request:', error);
    }
  };

  const handleDeleteClient = async (clientId) => {
    if (window.confirm('Are you sure you want to delete this client?')) {
      try {
        await fetch(`${API_BASE_URL}/api/clients/${clientId}`, {
          method: 'DELETE',
        });
        fetchClients();
      } catch (error) {
        console.error('Error deleting client:', error);
      }
    }
  };

  const handleDeleteProject = async (projectId) => {
    if (window.confirm('Are you sure you want to delete this project?')) {
      try {
        await fetch(`${API_BASE_URL}/api/projects/${projectId}`, {
          method: 'DELETE',
        });
        fetchProjects();
      } catch (error) {
        console.error('Error deleting project:', error);
      }
    }
  };

  const handleDeleteTeamMember = async (memberId) => {
    if (window.confirm('Are you sure you want to delete this team member?')) {
      try {
        await fetch(`${API_BASE_URL}/api/team-members/${memberId}`, {
          method: 'DELETE',
        });
        fetchTeamMembers();
      } catch (error) {
        console.error('Error deleting team member:', error);
      }
    }
  };

  // Check for payment success/failure on page load
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session_id');
    
    if (sessionId) {
      checkPaymentStatus(sessionId);
    }
  }, []);

  const checkPaymentStatus = async (sessionId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/payments/v1/checkout/status/${sessionId}`);
      if (response.ok) {
        const data = await response.json();
        if (data.payment_status === 'paid') {
          alert('Payment successful! Thank you for your payment.');
          fetchPayments();
          fetchDashboardStats();
        }
      }
    } catch (error) {
      console.error('Error checking payment status:', error);
    }
  };

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  if (!user) {
    return <LoginPage />;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation */}
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <h1 className="text-xl font-bold text-gray-900">Business Hub</h1>
              </div>
              <div className="hidden md:ml-6 md:flex md:space-x-8">
                <button
                  onClick={() => setCurrentView('dashboard')}
                  className={`nav-button ${currentView === 'dashboard' ? 'active' : ''}`}
                >
                  Dashboard
                </button>
                <button
                  onClick={() => setCurrentView('clients')}
                  className={`nav-button ${currentView === 'clients' ? 'active' : ''}`}
                >
                  Clients
                </button>
                <button
                  onClick={() => setCurrentView('projects')}
                  className={`nav-button ${currentView === 'projects' ? 'active' : ''}`}
                >
                  Projects
                </button>
                <button
                  onClick={() => setCurrentView('team')}
                  className={`nav-button ${currentView === 'team' ? 'active' : ''}`}
                >
                  Team
                </button>
                <button
                  onClick={() => setCurrentView('payments')}
                  className={`nav-button ${currentView === 'payments' ? 'active' : ''}`}
                >
                  Payments
                </button>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={toggleTheme}
                className="theme-toggle"
                title={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
              >
                {theme === 'light' ? '🌙' : '☀️'}
              </button>
              <button
                onClick={() => setShowProfileSettings(true)}
                className="profile-btn"
              >
                <img
                  src={user.profile_picture || 'https://via.placeholder.com/40'}
                  alt="Profile"
                  className="w-8 h-8 rounded-full"
                />
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {/* Dashboard */}
        {currentView === 'dashboard' && (
          <div className="space-y-6">
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <h2 className="text-lg font-medium text-gray-900">Dashboard Overview</h2>
                <p className="text-sm text-gray-500">Welcome back, {user.name}!</p>
              </div>
            </div>
            
            {/* Stats Cards */}
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
              <div className="stat-card">
                <div className="p-5">
                  <div className="flex items-center">
                    <div className="flex-shrink-0">
                      <div className="stat-card-icon bg-indigo-500">
                        <span className="text-white font-bold">C</span>
                      </div>
                    </div>
                    <div className="ml-5 w-0 flex-1">
                      <dl>
                        <dt className="stat-card-label">Total Clients</dt>
                        <dd className="stat-card-value">{dashboardStats.clients_count || 0}</dd>
                      </dl>
                    </div>
                  </div>
                </div>
              </div>

              <div className="stat-card">
                <div className="p-5">
                  <div className="flex items-center">
                    <div className="flex-shrink-0">
                      <div className="stat-card-icon bg-green-500">
                        <span className="text-white font-bold">P</span>
                      </div>
                    </div>
                    <div className="ml-5 w-0 flex-1">
                      <dl>
                        <dt className="stat-card-label">Active Projects</dt>
                        <dd className="stat-card-value">{dashboardStats.active_projects || 0}</dd>
                      </dl>
                    </div>
                  </div>
                </div>
              </div>

              <div className="stat-card">
                <div className="p-5">
                  <div className="flex items-center">
                    <div className="flex-shrink-0">
                      <div className="stat-card-icon bg-blue-500">
                        <span className="text-white font-bold">T</span>
                      </div>
                    </div>
                    <div className="ml-5 w-0 flex-1">
                      <dl>
                        <dt className="stat-card-label">Team Members</dt>
                        <dd className="stat-card-value">{dashboardStats.team_members_count || 0}</dd>
                      </dl>
                    </div>
                  </div>
                </div>
              </div>

              <div className="stat-card">
                <div className="p-5">
                  <div className="flex items-center">
                    <div className="flex-shrink-0">
                      <div className="stat-card-icon bg-yellow-500">
                        <span className="text-white font-bold">$</span>
                      </div>
                    </div>
                    <div className="ml-5 w-0 flex-1">
                      <dl>
                        <dt className="stat-card-label">Total Received</dt>
                        <dd className="stat-card-value">${dashboardStats.total_received || 0}</dd>
                      </dl>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Upcoming Meetings */}
            <div className="bg-white shadow rounded-lg">
              <div className="p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Upcoming Meetings</h3>
                {upcomingMeetings.length > 0 ? (
                  <div className="space-y-3">
                    {upcomingMeetings.map(meeting => (
                      <div key={meeting.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <div>
                          <h4 className="font-medium text-gray-900">{meeting.title}</h4>
                          <p className="text-sm text-gray-500">
                            {new Date(meeting.start_time).toLocaleString()}
                          </p>
                          <p className="text-sm text-gray-500">
                            {meeting.attendees_count} attendees • {meeting.location}
                          </p>
                        </div>
                        <div className="flex items-center">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                            Upcoming
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500">No upcoming meetings</p>
                )}
              </div>
            </div>

            {/* Quick Actions */}
            <div className="bg-white shadow rounded-lg">
              <div className="p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Quick Actions</h3>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <button
                    onClick={() => setClientModal({ isOpen: true, data: null })}
                    className="btn btn-primary"
                  >
                    Add Client
                  </button>
                  <button
                    onClick={() => setProjectModal({ isOpen: true, data: null })}
                    className="btn btn-success"
                  >
                    Add Project
                  </button>
                  <button
                    onClick={() => setTeamMemberModal({ isOpen: true, data: null })}
                    className="btn btn-info"
                  >
                    Add Team Member
                  </button>
                  <button
                    onClick={() => setPaymentModal({ isOpen: true, data: null })}
                    className="btn btn-warning"
                  >
                    Request Payment
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Clients */}
        {currentView === 'clients' && (
          <div className="space-y-6">
            <div className="bg-white shadow rounded-lg">
              <div className="p-6">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-lg font-medium text-gray-900">Clients</h2>
                  <button
                    onClick={() => setClientModal({ isOpen: true, data: null })}
                    className="btn btn-primary"
                  >
                    Add Client
                  </button>
                </div>
                <div className="table-wrapper">
                  <table className="table">
                    <thead className="table-header">
                      <tr>
                        <th>Name</th>
                        <th>Email</th>
                        <th>Company</th>
                        <th>Phone</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody className="table-body">
                      {clients.map(client => (
                        <tr key={client.id}>
                          <td className="font-medium">{client.name}</td>
                          <td>{client.email}</td>
                          <td>{client.company || '-'}</td>
                          <td>{client.phone || '-'}</td>
                          <td>
                            <div className="flex space-x-2">
                              <button
                                onClick={() => setClientModal({ isOpen: true, data: client })}
                                className="btn btn-secondary btn-sm"
                              >
                                Edit
                              </button>
                              <button
                                onClick={() => handleDeleteClient(client.id)}
                                className="btn btn-danger btn-sm"
                              >
                                Delete
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Projects */}
        {currentView === 'projects' && (
          <div className="space-y-6">
            <div className="bg-white shadow rounded-lg">
              <div className="p-6">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-lg font-medium text-gray-900">Projects</h2>
                  <button
                    onClick={() => setProjectModal({ isOpen: true, data: null })}
                    className="btn btn-primary"
                  >
                    Add Project
                  </button>
                </div>
                <div className="table-wrapper">
                  <table className="table">
                    <thead className="table-header">
                      <tr>
                        <th>Name</th>
                        <th>Client</th>
                        <th>Status</th>
                        <th>Budget</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody className="table-body">
                      {projects.map(project => (
                        <tr key={project.id}>
                          <td className="font-medium">{project.name}</td>
                          <td>{project.client_name || '-'}</td>
                          <td>
                            <span className={`badge project-status-${project.status}`}>
                              {project.status}
                            </span>
                          </td>
                          <td>${project.budget || '-'}</td>
                          <td>
                            <div className="flex space-x-2">
                              <button
                                onClick={() => setProjectModal({ isOpen: true, data: project })}
                                className="btn btn-secondary btn-sm"
                              >
                                Edit
                              </button>
                              <button
                                onClick={() => handleDeleteProject(project.id)}
                                className="btn btn-danger btn-sm"
                              >
                                Delete
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Team */}
        {currentView === 'team' && (
          <div className="space-y-6">
            <div className="bg-white shadow rounded-lg">
              <div className="p-6">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-lg font-medium text-gray-900">Team Members</h2>
                  <button
                    onClick={() => setTeamMemberModal({ isOpen: true, data: null })}
                    className="btn btn-primary"
                  >
                    Add Team Member
                  </button>
                </div>
                <div className="table-wrapper">
                  <table className="table">
                    <thead className="table-header">
                      <tr>
                        <th>Name</th>
                        <th>Email</th>
                        <th>Role</th>
                        <th>Type</th>
                        <th>Rate</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody className="table-body">
                      {teamMembers.map(member => (
                        <tr key={member.id}>
                          <td className="font-medium">{member.name}</td>
                          <td>{member.email}</td>
                          <td>{member.role}</td>
                          <td>
                            <span className={`badge member-type-${member.member_type}`}>
                              {member.member_type}
                            </span>
                          </td>
                          <td>${member.hourly_rate || '-'}/hr</td>
                          <td>
                            <div className="flex space-x-2">
                              <button
                                onClick={() => setTeamMemberModal({ isOpen: true, data: member })}
                                className="btn btn-secondary btn-sm"
                              >
                                Edit
                              </button>
                              <button
                                onClick={() => handleDeleteTeamMember(member.id)}
                                className="btn btn-danger btn-sm"
                              >
                                Delete
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Payments */}
        {currentView === 'payments' && (
          <div className="space-y-6">
            <div className="bg-white shadow rounded-lg">
              <div className="p-6">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-lg font-medium text-gray-900">Payment Transactions</h2>
                  <button
                    onClick={() => setPaymentModal({ isOpen: true, data: null })}
                    className="btn btn-success"
                  >
                    Request Payment
                  </button>
                </div>
                <div className="table-wrapper">
                  <table className="table">
                    <thead className="table-header">
                      <tr>
                        <th>Type</th>
                        <th>Amount</th>
                        <th>Status</th>
                        <th>Client/Member</th>
                        <th>Date</th>
                      </tr>
                    </thead>
                    <tbody className="table-body">
                      {payments.map(payment => (
                        <tr key={payment.id}>
                          <td>
                            <span className={`badge ${payment.payment_type === 'received' ? 'badge-success' : 'badge-info'}`}>
                              {payment.payment_type}
                            </span>
                          </td>
                          <td>${payment.amount} {payment.currency.toUpperCase()}</td>
                          <td>
                            <span className={`badge payment-status-${payment.payment_status}`}>
                              {payment.payment_status}
                            </span>
                          </td>
                          <td>
                            {payment.client_name || payment.team_member_name || '-'}
                          </td>
                          <td>
                            {new Date(payment.created_at).toLocaleDateString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Modals */}
      <Modal
        isOpen={clientModal.isOpen}
        onClose={() => setClientModal({ isOpen: false, data: null })}
        title={clientModal.data ? 'Edit Client' : 'Add Client'}
      >
        <ClientForm 
          onSubmit={handleClientSubmit}
          initialData={clientModal.data || {}}
        />
      </Modal>

      <Modal
        isOpen={projectModal.isOpen}
        onClose={() => setProjectModal({ isOpen: false, data: null })}
        title={projectModal.data ? 'Edit Project' : 'Add Project'}
      >
        <ProjectForm 
          onSubmit={handleProjectSubmit}
          initialData={projectModal.data || {}}
        />
      </Modal>

      <Modal
        isOpen={teamMemberModal.isOpen}
        onClose={() => setTeamMemberModal({ isOpen: false, data: null })}
        title={teamMemberModal.data ? 'Edit Team Member' : 'Add Team Member'}
      >
        <TeamMemberForm 
          onSubmit={handleTeamMemberSubmit}
          initialData={teamMemberModal.data || {}}
        />
      </Modal>

      <Modal
        isOpen={paymentModal.isOpen}
        onClose={() => setPaymentModal({ isOpen: false, data: null })}
        title="Request Payment"
      >
        <PaymentRequestForm onSubmit={handlePaymentRequest} />
      </Modal>

      <ProfileSettings 
        isOpen={showProfileSettings}
        onClose={() => setShowProfileSettings(false)}
      />
    </div>
  );
}

// Main App with Providers
function AppWithProviders() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <App />
      </AuthProvider>
    </ThemeProvider>
  );
}

export default AppWithProviders;