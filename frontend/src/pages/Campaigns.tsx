import React, { useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  IconButton,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
  Alert,
  Snackbar,
} from '@mui/material';
import {
  Add as AddIcon,
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  Stop as StopIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Send as ExecuteIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { campaignApi } from '../services/api';
import { Campaign, PropertyType, CampaignStatus } from '../types';

const Campaigns: React.FC = () => {
  const [openDialog, setOpenDialog] = useState(false);
  const [selectedCampaign, setSelectedCampaign] = useState<Campaign | null>(null);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [campaignToDelete, setCampaignToDelete] = useState<Campaign | null>(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' });
  const queryClient = useQueryClient();

  const { data: campaigns, isLoading } = useQuery('campaigns', campaignApi.getAll);

  const createMutation = useMutation(campaignApi.create, {
    onSuccess: () => {
      queryClient.invalidateQueries('campaigns');
      setOpenDialog(false);
      setSelectedCampaign(null);
      setSnackbar({ open: true, message: 'Campaign created successfully!', severity: 'success' });
    },
    onError: () => {
      setSnackbar({ open: true, message: 'Failed to create campaign', severity: 'error' });
    },
  });

  const updateMutation = useMutation(
    ({ id, data }: { id: string; data: Partial<Campaign> }) =>
      campaignApi.update(id, data),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('campaigns');
        setOpenDialog(false);
        setSelectedCampaign(null);
        setSnackbar({ open: true, message: 'Campaign updated successfully!', severity: 'success' });
      },
      onError: () => {
        setSnackbar({ open: true, message: 'Failed to update campaign', severity: 'error' });
      },
    }
  );

  const startMutation = useMutation(campaignApi.start, {
    onSuccess: () => {
      queryClient.invalidateQueries('campaigns');
      setSnackbar({ open: true, message: 'Campaign started successfully!', severity: 'success' });
    },
    onError: () => {
      setSnackbar({ open: true, message: 'Failed to start campaign', severity: 'error' });
    },
  });

  const pauseMutation = useMutation(campaignApi.pause, {
    onSuccess: () => {
      queryClient.invalidateQueries('campaigns');
      setSnackbar({ open: true, message: 'Campaign paused successfully!', severity: 'success' });
    },
    onError: () => {
      setSnackbar({ open: true, message: 'Failed to pause campaign', severity: 'error' });
    },
  });

  const stopMutation = useMutation(campaignApi.stop, {
    onSuccess: () => {
      queryClient.invalidateQueries('campaigns');
      setSnackbar({ open: true, message: 'Campaign stopped successfully!', severity: 'success' });
    },
    onError: () => {
      setSnackbar({ open: true, message: 'Failed to stop campaign', severity: 'error' });
    },
  });

  const executeMutation = useMutation(campaignApi.execute, {
    onSuccess: (data) => {
      queryClient.invalidateQueries('campaigns');
      setSnackbar({ 
        open: true, 
        message: data.message || 'Campaign execution started!', 
        severity: 'success' 
      });
    },
    onError: () => {
      setSnackbar({ open: true, message: 'Failed to execute campaign', severity: 'error' });
    },
  });

  const deleteMutation = useMutation(campaignApi.delete, {
    onSuccess: () => {
      queryClient.invalidateQueries('campaigns');
      setDeleteConfirmOpen(false);
      setCampaignToDelete(null);
      setSnackbar({ open: true, message: 'Campaign deleted successfully!', severity: 'success' });
    },
    onError: () => {
      setSnackbar({ open: true, message: 'Failed to delete campaign', severity: 'error' });
    },
  });

  const handleCreateCampaign = () => {
    setSelectedCampaign(null);
    setOpenDialog(true);
  };

  const handleEditCampaign = (campaign: Campaign) => {
    setSelectedCampaign(campaign);
    setOpenDialog(true);
  };

  const handleDeleteCampaign = (campaign: Campaign) => {
    setCampaignToDelete(campaign);
    setDeleteConfirmOpen(true);
  };

  const confirmDelete = () => {
    if (campaignToDelete) {
      deleteMutation.mutate(campaignToDelete.id);
    }
  };

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    
    const campaignData = {
      name: formData.get('name') as string,
      property_type: formData.get('property_type') as PropertyType,
      config: {
        max_daily_contacts: parseInt(formData.get('max_daily_contacts') as string),
        follow_up_days: [1, 3, 7, 14],
        target_response_rate: parseFloat(formData.get('target_response_rate') as string),
        quiet_hours_start: formData.get('quiet_hours_start') as string,
        quiet_hours_end: formData.get('quiet_hours_end') as string,
      },
    };

    if (selectedCampaign) {
      updateMutation.mutate({ id: selectedCampaign.id, data: campaignData });
    } else {
      createMutation.mutate(campaignData);
    }
  };

  const getStatusColor = (status: CampaignStatus) => {
    switch (status) {
      case CampaignStatus.ACTIVE:
        return 'success';
      case CampaignStatus.PAUSED:
        return 'warning';
      case CampaignStatus.STOPPED:
        return 'error';
      default:
        return 'default';
    }
  };

  const getPropertyTypeLabel = (type: PropertyType) => {
    switch (type) {
      case PropertyType.FIX_FLIP:
        return 'Fix & Flip';
      case PropertyType.RENTAL:
        return 'Rental';
      case PropertyType.VACANT_LAND:
        return 'Vacant Land';
      default:
        return type;
    }
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Campaigns</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleCreateCampaign}
        >
          Create Campaign
        </Button>
      </Box>

      <Grid container spacing={3}>
        {campaigns?.map((campaign) => (
          <Grid item xs={12} md={6} lg={4} key={campaign.id}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="start" mb={2}>
                  <Typography variant="h6" component="h2">
                    {campaign.name}
                  </Typography>
                  <Chip
                    label={campaign.status}
                    color={getStatusColor(campaign.status)}
                    size="small"
                  />
                </Box>
                
                <Typography color="textSecondary" gutterBottom>
                  {getPropertyTypeLabel(campaign.property_type)}
                </Typography>
                
                <Box mt={2}>
                  <Typography variant="body2">
                    Total Leads: {campaign.stats?.total_leads || 0}
                  </Typography>
                  <Typography variant="body2">
                    Response Rate: {campaign.stats?.response_rate?.toFixed(1) || 0}%
                  </Typography>
                  <Typography variant="body2">
                    Appointments: {campaign.stats?.appointments_set || 0}
                  </Typography>
                </Box>

                <Box display="flex" justifyContent="space-between" mt={2}>
                  <Box>
                    {campaign.status === CampaignStatus.CREATED && (
                      <IconButton
                        color="primary"
                        onClick={() => startMutation.mutate(campaign.id)}
                        title="Start Campaign"
                      >
                        <PlayIcon />
                      </IconButton>
                    )}
                    {campaign.status === CampaignStatus.ACTIVE && (
                      <>
                        <IconButton
                          color="success"
                          onClick={() => executeMutation.mutate(campaign.id)}
                          title="Execute Campaign (Process New Leads)"
                        >
                          <ExecuteIcon />
                        </IconButton>
                        <IconButton
                          color="warning"
                          onClick={() => pauseMutation.mutate(campaign.id)}
                          title="Pause Campaign"
                        >
                          <PauseIcon />
                        </IconButton>
                      </>
                    )}
                    {campaign.status === CampaignStatus.PAUSED && (
                      <>
                        <IconButton
                          color="primary"
                          onClick={() => startMutation.mutate(campaign.id)}
                          title="Resume Campaign"
                        >
                          <PlayIcon />
                        </IconButton>
                        <IconButton
                          color="error"
                          onClick={() => stopMutation.mutate(campaign.id)}
                          title="Stop Campaign"
                        >
                          <StopIcon />
                        </IconButton>
                      </>
                    )}
                  </Box>
                  <Box>
                    <IconButton
                      onClick={() => handleEditCampaign(campaign)}
                    >
                      <EditIcon />
                    </IconButton>
                    <IconButton
                      color="error"
                      onClick={() => handleDeleteCampaign(campaign)}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Create/Edit Campaign Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="sm" fullWidth>
        <form onSubmit={handleSubmit}>
          <DialogTitle>
            {selectedCampaign ? 'Edit Campaign' : 'Create New Campaign'}
          </DialogTitle>
          <DialogContent>
            <TextField
              autoFocus
              margin="dense"
              name="name"
              label="Campaign Name"
              fullWidth
              variant="outlined"
              defaultValue={selectedCampaign?.name || ''}
              required
            />
            
            <FormControl fullWidth margin="dense" variant="outlined">
              <InputLabel>Property Type</InputLabel>
              <Select
                name="property_type"
                label="Property Type"
                defaultValue={selectedCampaign?.property_type || PropertyType.FIX_FLIP}
                required
              >
                <MenuItem value={PropertyType.FIX_FLIP}>Fix & Flip</MenuItem>
                <MenuItem value={PropertyType.RENTAL}>Rental</MenuItem>
                <MenuItem value={PropertyType.VACANT_LAND}>Vacant Land</MenuItem>
              </Select>
            </FormControl>

            <TextField
              margin="dense"
              name="max_daily_contacts"
              label="Max Daily Contacts"
              type="number"
              fullWidth
              variant="outlined"
              defaultValue={selectedCampaign?.config?.max_daily_contacts || 50}
              required
            />

            <TextField
              margin="dense"
              name="target_response_rate"
              label="Target Response Rate (%)"
              type="number"
              fullWidth
              variant="outlined"
              defaultValue={selectedCampaign?.config?.target_response_rate || 15}
              required
            />

            <TextField
              margin="dense"
              name="quiet_hours_start"
              label="Quiet Hours Start"
              type="time"
              fullWidth
              variant="outlined"
              defaultValue={selectedCampaign?.config?.quiet_hours_start || '21:00'}
              InputLabelProps={{ shrink: true }}
              required
            />

            <TextField
              margin="dense"
              name="quiet_hours_end"
              label="Quiet Hours End"
              type="time"
              fullWidth
              variant="outlined"
              defaultValue={selectedCampaign?.config?.quiet_hours_end || '08:00'}
              InputLabelProps={{ shrink: true }}
              required
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
            <Button type="submit" variant="contained">
              {selectedCampaign ? 'Update' : 'Create'}
            </Button>
          </DialogActions>
        </form>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteConfirmOpen} onClose={() => setDeleteConfirmOpen(false)}>
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete the campaign "{campaignToDelete?.name}"? 
            This will also affect all associated leads and conversations. This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteConfirmOpen(false)}>Cancel</Button>
          <Button 
            onClick={confirmDelete} 
            color="error" 
            variant="contained"
            disabled={deleteMutation.isLoading}
          >
            {deleteMutation.isLoading ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert 
          onClose={() => setSnackbar({ ...snackbar, open: false })} 
          severity={snackbar.severity}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default Campaigns;
