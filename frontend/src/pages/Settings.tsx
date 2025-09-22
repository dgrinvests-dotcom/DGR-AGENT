import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Grid,
  Switch,
  TextField,
  Typography,
  Button,
  Divider,
  Alert,
  FormControlLabel,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Chip,
} from '@mui/material';
import {
  Save as SaveIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { useQuery } from 'react-query';
import { dashboardApi } from '../services/api';

const Settings: React.FC = () => {
  const [settings, setSettings] = useState({
    // AI Settings
    openai_model: 'gpt-4',
    max_tokens: 150,
    temperature: 0.7,
    
    // Compliance Settings
    quiet_hours_start: '21:00',
    quiet_hours_end: '08:00',
    timezone: 'America/New_York',
    auto_opt_out: true,
    
    // Campaign Settings
    default_max_daily_contacts: 50,
    default_follow_up_days: '1,3,7,14',
    default_response_timeout: 24,
    
    // Integration Settings
    telnyx_webhook_enabled: true,
    gmail_auto_sync: true,
    google_meet_auto_create: true,
  });

  const { data: integrationStatus } = useQuery('integrationStatus', dashboardApi.getIntegrationStatus);

  const handleSettingChange = (key: string, value: any) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const handleSave = () => {
    // TODO: Implement save settings API call
    console.log('Saving settings:', settings);
  };

  const testIntegration = (integration: string) => {
    // TODO: Implement integration test API calls
    console.log('Testing integration:', integration);
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Settings
      </Typography>

      <Grid container spacing={3}>
        {/* AI Configuration */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                AI Configuration
              </Typography>
              <Divider sx={{ mb: 2 }} />
              
              <TextField
                fullWidth
                label="OpenAI Model"
                value={settings.openai_model}
                onChange={(e) => handleSettingChange('openai_model', e.target.value)}
                margin="normal"
                helperText="GPT model to use for conversations"
              />
              
              <TextField
                fullWidth
                label="Max Tokens"
                type="number"
                value={settings.max_tokens}
                onChange={(e) => handleSettingChange('max_tokens', parseInt(e.target.value))}
                margin="normal"
                helperText="Maximum tokens per AI response"
              />
              
              <TextField
                fullWidth
                label="Temperature"
                type="number"
                inputProps={{ min: 0, max: 1, step: 0.1 }}
                value={settings.temperature}
                onChange={(e) => handleSettingChange('temperature', parseFloat(e.target.value))}
                margin="normal"
                helperText="AI creativity level (0-1)"
              />
            </CardContent>
          </Card>
        </Grid>

        {/* Compliance Settings */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Compliance Settings
              </Typography>
              <Divider sx={{ mb: 2 }} />
              
              <TextField
                fullWidth
                label="Quiet Hours Start"
                type="time"
                value={settings.quiet_hours_start}
                onChange={(e) => handleSettingChange('quiet_hours_start', e.target.value)}
                margin="normal"
                InputLabelProps={{ shrink: true }}
              />
              
              <TextField
                fullWidth
                label="Quiet Hours End"
                type="time"
                value={settings.quiet_hours_end}
                onChange={(e) => handleSettingChange('quiet_hours_end', e.target.value)}
                margin="normal"
                InputLabelProps={{ shrink: true }}
              />
              
              <TextField
                fullWidth
                label="Timezone"
                value={settings.timezone}
                onChange={(e) => handleSettingChange('timezone', e.target.value)}
                margin="normal"
                helperText="Default timezone for campaigns"
              />
              
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.auto_opt_out}
                    onChange={(e) => handleSettingChange('auto_opt_out', e.target.checked)}
                  />
                }
                label="Auto Opt-out Processing"
                sx={{ mt: 2 }}
              />
            </CardContent>
          </Card>
        </Grid>

        {/* Campaign Defaults */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Campaign Defaults
              </Typography>
              <Divider sx={{ mb: 2 }} />
              
              <TextField
                fullWidth
                label="Max Daily Contacts"
                type="number"
                value={settings.default_max_daily_contacts}
                onChange={(e) => handleSettingChange('default_max_daily_contacts', parseInt(e.target.value))}
                margin="normal"
                helperText="Default maximum contacts per day"
              />
              
              <TextField
                fullWidth
                label="Follow-up Days"
                value={settings.default_follow_up_days}
                onChange={(e) => handleSettingChange('default_follow_up_days', e.target.value)}
                margin="normal"
                helperText="Comma-separated days for follow-ups (e.g., 1,3,7,14)"
              />
              
              <TextField
                fullWidth
                label="Response Timeout (hours)"
                type="number"
                value={settings.default_response_timeout}
                onChange={(e) => handleSettingChange('default_response_timeout', parseInt(e.target.value))}
                margin="normal"
                helperText="Hours to wait before follow-up"
              />
            </CardContent>
          </Card>
        </Grid>

        {/* Integration Status */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Integration Status
              </Typography>
              <Divider sx={{ mb: 2 }} />
              
              <List>
                <ListItem>
                  <ListItemText
                    primary="Telnyx SMS"
                    secondary="SMS messaging service"
                  />
                  <ListItemSecondaryAction>
                    <Box display="flex" alignItems="center" gap={1}>
                      <Chip
                        label={integrationStatus?.telnyx ? 'Connected' : 'Disconnected'}
                        color={integrationStatus?.telnyx ? 'success' : 'error'}
                        size="small"
                      />
                      <Button
                        size="small"
                        onClick={() => testIntegration('telnyx')}
                      >
                        Test
                      </Button>
                    </Box>
                  </ListItemSecondaryAction>
                </ListItem>
                
                <ListItem>
                  <ListItemText
                    primary="Google Meet"
                    secondary="Video meeting scheduling"
                  />
                  <ListItemSecondaryAction>
                    <Box display="flex" alignItems="center" gap={1}>
                      <Chip
                        label={integrationStatus?.google_meet ? 'Connected' : 'Disconnected'}
                        color={integrationStatus?.google_meet ? 'success' : 'error'}
                        size="small"
                      />
                      <Button
                        size="small"
                        onClick={() => testIntegration('google_meet')}
                      >
                        Test
                      </Button>
                    </Box>
                  </ListItemSecondaryAction>
                </ListItem>
                
                <ListItem>
                  <ListItemText
                    primary="Gmail"
                    secondary="Email communication"
                  />
                  <ListItemSecondaryAction>
                    <Box display="flex" alignItems="center" gap={1}>
                      <Chip
                        label={integrationStatus?.gmail ? 'Connected' : 'Disconnected'}
                        color={integrationStatus?.gmail ? 'success' : 'error'}
                        size="small"
                      />
                      <Button
                        size="small"
                        onClick={() => testIntegration('gmail')}
                      >
                        Test
                      </Button>
                    </Box>
                  </ListItemSecondaryAction>
                </ListItem>
                
                <ListItem>
                  <ListItemText
                    primary="OpenAI"
                    secondary="AI conversation engine"
                  />
                  <ListItemSecondaryAction>
                    <Box display="flex" alignItems="center" gap={1}>
                      <Chip
                        label={integrationStatus?.openai ? 'Connected' : 'Disconnected'}
                        color={integrationStatus?.openai ? 'success' : 'error'}
                        size="small"
                      />
                      <Button
                        size="small"
                        onClick={() => testIntegration('openai')}
                      >
                        Test
                      </Button>
                    </Box>
                  </ListItemSecondaryAction>
                </ListItem>
              </List>
            </CardContent>
          </Card>
        </Grid>

        {/* Integration Settings */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Integration Settings
              </Typography>
              <Divider sx={{ mb: 2 }} />
              
              <Grid container spacing={2}>
                <Grid item xs={12} sm={4}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.telnyx_webhook_enabled}
                        onChange={(e) => handleSettingChange('telnyx_webhook_enabled', e.target.checked)}
                      />
                    }
                    label="Telnyx Webhooks"
                  />
                </Grid>
                
                <Grid item xs={12} sm={4}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.gmail_auto_sync}
                        onChange={(e) => handleSettingChange('gmail_auto_sync', e.target.checked)}
                      />
                    }
                    label="Gmail Auto Sync"
                  />
                </Grid>
                
                <Grid item xs={12} sm={4}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.google_meet_auto_create}
                        onChange={(e) => handleSettingChange('google_meet_auto_create', e.target.checked)}
                      />
                    }
                    label="Auto Create Meetings"
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Save Button */}
        <Grid item xs={12}>
          <Box display="flex" justifyContent="flex-end" gap={2}>
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
            >
              Reset to Defaults
            </Button>
            <Button
              variant="contained"
              startIcon={<SaveIcon />}
              onClick={handleSave}
            >
              Save Settings
            </Button>
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Settings;
