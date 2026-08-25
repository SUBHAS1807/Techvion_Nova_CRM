const express = require('express');
const cors = require('cors');
const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '.env') });

const migrate = require('./config/migrate');
const seedDatabase = require('./config/seed');

const dashboardRoutes = require('./routes/dashboard');
const leadsRoutes = require('./routes/leads');
const importRoutes = require('./routes/import');
const exportRoutes = require('./routes/export');
const filtersRoutes = require('./routes/filters');

const app = express();
const PORT = process.env.PORT || 5000;

// Enable CORS for client
app.use(cors({
  origin: '*',
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization'],
}));

// Body parsing middleware
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Request logging middleware in development
app.use((req, res, next) => {
  if (process.env.NODE_ENV !== 'production' && req.path.startsWith('/api')) {
    console.log(`[${new Date().toISOString().split('T')[1].slice(0, 8)}] ${req.method} ${req.path}`);
  }
  next();
});

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    service: 'TechvionNova Lead Management CRM Backend',
    timestamp: new Date().toISOString(),
  });
});

// Mount CRM API Routes
app.use('/api/dashboard', dashboardRoutes);
app.use('/api/leads', leadsRoutes);
app.use('/api/import', importRoutes);
app.use('/api/export', exportRoutes);
app.use('/api/filters', filtersRoutes);

// Global error handler
app.use((err, req, res, next) => {
  console.error('Unhandled Server Error:', err);
  res.status(500).json({
    success: false,
    error: err.message || 'Internal Server Error',
  });
});

// Initialize database and start server
async function startServer() {
  try {
    // 1. Run migrations
    await migrate();

    // 2. Seed initial sample data if empty
    await seedDatabase();

    // 3. Start listening
    app.listen(PORT, () => {
      console.log(`\n======================================================`);
      console.log(`🚀 TechvionNova Lead CRM API Server running on port ${PORT}`);
      console.log(`🔗 API Base: http://localhost:${PORT}/api`);
      console.log(`📊 Dashboard Stats: http://localhost:${PORT}/api/dashboard/stats`);
      console.log(`📋 Leads List: http://localhost:${PORT}/api/leads`);
      console.log(`======================================================\n`);
    });
  } catch (err) {
    console.error('Failed to start server:', err);
    process.exit(1);
  }
}

startServer();
