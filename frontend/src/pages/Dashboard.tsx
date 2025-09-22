import React from 'react';
import {
  Grid,
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  LinearProgress,
} from '@mui/material';
import {
  TrendingUp,
  People,
  Campaign,
  Chat,
  Phone,
} from '@mui/icons-material';
import { useQuery } from 'react-query';
import { dashboardApi } from '../services/api';

const StatCard: React.FC<{
  title: string;
  value: string | number;
  icon: React.ReactNode;
  color: string;
  subtitle?: string;
}> = ({ title, value, icon, color, subtitle }) => (
  <Card>
    <CardContent>
      <Box display="flex" alignItems="center" justifyContent="space-between">
        <Box>
          <Typography color="textSecondary" gutterBottom variant="body2">
            {title}
          </Typography>
          <Typography variant="h4" component="h2">
            {value}
          </Typography>
          {subtitle && (
            <Typography color="textSecondary" variant="body2">
              {subtitle}
            </Typography>
          )}
        </Box>
        <Box
          sx={{
            backgroundColor: color,
            borderRadius: '50%',
            p: 1,
            color: 'white',
          }}
        >
          {icon}
        </Box>
      </Box>
    </CardContent>
  </Card>
);

const Dashboard: React.FC = () => {
  const { data: stats, isLoading } = useQuery('dashboardStats', dashboardApi.getStats);
  const { data: integrationStatus } = useQuery('integrationStatus', dashboardApi.getIntegrationStatus);

  if (isLoading) {
    return (
      <Box sx={{ width: '100%' }}>
        <LinearProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard Overview
      </Typography>
      
      <Grid container spacing={3}>
        {/* Stats Cards */}
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Active Campaigns"
            value={stats?.active_campaigns || 0}
            icon={<Campaign />}
            color="#1976d2"
          />
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Leads"
            value={stats?.total_leads || 0}
            icon={<People />}
            color="#388e3c"
          />
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Active Conversations"
            value={stats?.active_conversations || 0}
            icon={<Chat />}
            color="#f57c00"
          />
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Appointments Today"
            value={stats?.appointments_today || 0}
            icon={<Phone />}
            color="#7b1fa2"
          />
        </Grid>

        {/* Performance Metrics */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Performance Metrics
            </Typography>
            <Box sx={{ mt: 2 }}>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                <Typography variant="body2">Response Rate</Typography>
                <Typography variant="body2" fontWeight="bold">
                  {stats?.response_rate ? `${stats.response_rate.toFixed(1)}%` : '0%'}
                </Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={stats?.response_rate || 0}
                sx={{ height: 8, borderRadius: 4 }}
              />
            </Box>
            
            <Box sx={{ mt: 3 }}>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                <Typography variant="body2">Conversion Rate</Typography>
                <Typography variant="body2" fontWeight="bold">
                  {stats?.conversion_rate ? `${stats.conversion_rate.toFixed(1)}%` : '0%'}
                </Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={stats?.conversion_rate || 0}
                sx={{ height: 8, borderRadius: 4 }}
                color="secondary"
              />
            </Box>
          </Paper>
        </Grid>

        {/* Integration Status */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Integration Status
            </Typography>
            <Box sx={{ mt: 2 }}>
              {[
                { name: 'Telnyx SMS', status: integrationStatus?.telnyx },
                { name: 'Google Meet', status: integrationStatus?.google_meet },
                { name: 'Gmail', status: integrationStatus?.gmail },
                { name: 'OpenAI', status: integrationStatus?.openai },
              ].map((integration) => (
                <Box
                  key={integration.name}
                  display="flex"
                  justifyContent="space-between"
                  alignItems="center"
                  py={1}
                >
                  <Typography variant="body2">{integration.name}</Typography>
                  <Box
                    sx={{
                      width: 12,
                      height: 12,
                      borderRadius: '50%',
                      backgroundColor: integration.status ? '#4caf50' : '#f44336',
                    }}
                  />
                </Box>
              ))}
            </Box>
          </Paper>
        </Grid>

        {/* Recent Activity */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Recent Activity
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Activity feed will be implemented with real-time updates
            </Typography>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;
