import React, { useState } from 'react';
import {
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  Grid,
  IconButton,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Typography,
  Alert,
  Snackbar,
} from '@mui/material';
import {
  Add as AddIcon,
  Upload as UploadIcon,
  Download as DownloadIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { leadApi, campaignApi } from '../services/api';
import { Lead, LeadStatus, PropertyType } from '../types';

const Leads: React.FC = () => {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [openDialog, setOpenDialog] = useState(false);
  const [openImportDialog, setOpenImportDialog] = useState(false);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [leadToDelete, setLeadToDelete] = useState<Lead | null>(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' });
  const [filters, setFilters] = useState({
    campaign_id: '',
    status: '',
    property_type: '',
  });

  const queryClient = useQueryClient();

  const { data: leadsData, isLoading } = useQuery(
    ['leads', page, rowsPerPage, filters],
    () => leadApi.getAll({ ...filters, page: page + 1, limit: rowsPerPage })
  );

  const { data: campaigns } = useQuery('campaigns', campaignApi.getAll);

  const createMutation = useMutation(leadApi.create, {
    onSuccess: () => {
      queryClient.invalidateQueries('leads');
      setOpenDialog(false);
      setSelectedLead(null);
    },
  });

  const updateMutation = useMutation(
    ({ id, data }: { id: string; data: Partial<Lead> }) =>
      leadApi.update(id, data),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('leads');
        setOpenDialog(false);
        setSelectedLead(null);
      },
    }
  );

  const importMutation = useMutation(
    ({ file, campaignId }: { file: File; campaignId: string }) =>
      leadApi.import(file, campaignId),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('leads');
        setOpenImportDialog(false);
        setSnackbar({ open: true, message: 'Leads imported successfully!', severity: 'success' });
      },
      onError: () => {
        setSnackbar({ open: true, message: 'Failed to import leads', severity: 'error' });
      },
    }
  );

  const deleteMutation = useMutation(leadApi.delete, {
    onSuccess: () => {
      queryClient.invalidateQueries('leads');
      setDeleteConfirmOpen(false);
      setLeadToDelete(null);
      setSnackbar({ open: true, message: 'Lead deleted successfully!', severity: 'success' });
    },
    onError: () => {
      setSnackbar({ open: true, message: 'Failed to delete lead', severity: 'error' });
    },
  });

  const onDrop = (acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0];
      const campaignId = (document.getElementById('import-campaign-select') as HTMLInputElement)?.value;
      if (campaignId) {
        importMutation.mutate({ file, campaignId });
      }
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    },
    multiple: false,
  });

  const handleCreateLead = () => {
    setSelectedLead(null);
    setOpenDialog(true);
  };

  const handleEditLead = (lead: Lead) => {
    setSelectedLead(lead);
    setOpenDialog(true);
  };

  const handleDeleteLead = (lead: Lead) => {
    setLeadToDelete(lead);
    setDeleteConfirmOpen(true);
  };

  const confirmDelete = () => {
    if (leadToDelete) {
      deleteMutation.mutate(leadToDelete.id);
    }
  };

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    
    const leadData = {
      first_name: formData.get('first_name') as string,
      last_name: formData.get('last_name') as string,
      phone: formData.get('phone') as string,
      email: formData.get('email') as string,
      property_address: formData.get('property_address') as string,
      property_type: formData.get('property_type') as PropertyType,
      campaign_id: formData.get('campaign_id') as string,
      property_value: parseFloat(formData.get('property_value') as string) || undefined,
      condition: formData.get('condition') as string,
      notes: formData.get('notes') as string,
    };

    if (selectedLead) {
      updateMutation.mutate({ id: selectedLead.id, data: leadData });
    } else {
      createMutation.mutate(leadData);
    }
  };

  const getStatusColor = (status: LeadStatus) => {
    switch (status) {
      case LeadStatus.NEW:
        return 'default';
      case LeadStatus.CONTACTED:
        return 'info';
      case LeadStatus.RESPONDED:
        return 'primary';
      case LeadStatus.QUALIFIED:
        return 'success';
      case LeadStatus.APPOINTMENT_SET:
        return 'success';
      case LeadStatus.NOT_INTERESTED:
        return 'error';
      case LeadStatus.OPTED_OUT:
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
        <Typography variant="h4">Leads</Typography>
        <Box>
          <Button
            variant="outlined"
            startIcon={<UploadIcon />}
            onClick={() => setOpenImportDialog(true)}
            sx={{ mr: 1 }}
          >
            Import
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleCreateLead}
          >
            Add Lead
          </Button>
        </Box>
      </Box>

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={4}>
            <FormControl fullWidth size="small">
              <InputLabel>Campaign</InputLabel>
              <Select
                value={filters.campaign_id}
                label="Campaign"
                onChange={(e) => setFilters({ ...filters, campaign_id: e.target.value })}
              >
                <MenuItem value="">All Campaigns</MenuItem>
                {campaigns?.map((campaign) => (
                  <MenuItem key={campaign.id} value={campaign.id}>
                    {campaign.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={4}>
            <FormControl fullWidth size="small">
              <InputLabel>Status</InputLabel>
              <Select
                value={filters.status}
                label="Status"
                onChange={(e) => setFilters({ ...filters, status: e.target.value })}
              >
                <MenuItem value="">All Statuses</MenuItem>
                {Object.values(LeadStatus).map((status) => (
                  <MenuItem key={status} value={status}>
                    {status.replace('_', ' ').toUpperCase()}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={4}>
            <FormControl fullWidth size="small">
              <InputLabel>Property Type</InputLabel>
              <Select
                value={filters.property_type}
                label="Property Type"
                onChange={(e) => setFilters({ ...filters, property_type: e.target.value })}
              >
                <MenuItem value="">All Types</MenuItem>
                {Object.values(PropertyType).map((type) => (
                  <MenuItem key={type} value={type}>
                    {getPropertyTypeLabel(type)}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
        </Grid>
      </Paper>

      {/* Leads Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Phone</TableCell>
              <TableCell>Property Address</TableCell>
              <TableCell>Property Type</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Campaign</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {leadsData?.leads?.map((lead) => (
              <TableRow key={lead.id}>
                <TableCell>
                  {lead.first_name} {lead.last_name}
                </TableCell>
                <TableCell>{lead.phone}</TableCell>
                <TableCell>{lead.property_address}</TableCell>
                <TableCell>{getPropertyTypeLabel(lead.property_type)}</TableCell>
                <TableCell>
                  <Chip
                    label={lead.status.replace('_', ' ').toUpperCase()}
                    color={getStatusColor(lead.status)}
                    size="small"
                  />
                </TableCell>
                <TableCell>
                  {campaigns?.find(c => c.id === lead.campaign_id)?.name || 'N/A'}
                </TableCell>
                <TableCell>
                  <IconButton
                    size="small"
                    onClick={() => handleEditLead(lead)}
                  >
                    <EditIcon />
                  </IconButton>
                  <IconButton
                    size="small"
                    color="error"
                    onClick={() => handleDeleteLead(lead)}
                  >
                    <DeleteIcon />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <TablePagination
          rowsPerPageOptions={[10, 25, 50]}
          component="div"
          count={leadsData?.total || 0}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={(_, newPage) => setPage(newPage)}
          onRowsPerPageChange={(event) => {
            setRowsPerPage(parseInt(event.target.value, 10));
            setPage(0);
          }}
        />
      </TableContainer>

      {/* Create/Edit Lead Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="md" fullWidth>
        <form onSubmit={handleSubmit}>
          <DialogTitle>
            {selectedLead ? 'Edit Lead' : 'Add New Lead'}
          </DialogTitle>
          <DialogContent>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField
                  autoFocus
                  margin="dense"
                  name="first_name"
                  label="First Name"
                  fullWidth
                  variant="outlined"
                  defaultValue={selectedLead?.first_name || ''}
                  required
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  margin="dense"
                  name="last_name"
                  label="Last Name"
                  fullWidth
                  variant="outlined"
                  defaultValue={selectedLead?.last_name || ''}
                  required
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  margin="dense"
                  name="phone"
                  label="Phone"
                  fullWidth
                  variant="outlined"
                  defaultValue={selectedLead?.phone || ''}
                  required
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  margin="dense"
                  name="email"
                  label="Email"
                  type="email"
                  fullWidth
                  variant="outlined"
                  defaultValue={selectedLead?.email || ''}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  margin="dense"
                  name="property_address"
                  label="Property Address"
                  fullWidth
                  variant="outlined"
                  defaultValue={selectedLead?.property_address || ''}
                  required
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth margin="dense" variant="outlined">
                  <InputLabel>Property Type</InputLabel>
                  <Select
                    name="property_type"
                    label="Property Type"
                    defaultValue={selectedLead?.property_type || PropertyType.FIX_FLIP}
                    required
                  >
                    <MenuItem value={PropertyType.FIX_FLIP}>Fix & Flip</MenuItem>
                    <MenuItem value={PropertyType.RENTAL}>Rental</MenuItem>
                    <MenuItem value={PropertyType.VACANT_LAND}>Vacant Land</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth margin="dense" variant="outlined">
                  <InputLabel>Campaign</InputLabel>
                  <Select
                    name="campaign_id"
                    label="Campaign"
                    defaultValue={selectedLead?.campaign_id || ''}
                  >
                    {campaigns?.map((campaign) => (
                      <MenuItem key={campaign.id} value={campaign.id}>
                        {campaign.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  margin="dense"
                  name="property_value"
                  label="Property Value"
                  type="number"
                  fullWidth
                  variant="outlined"
                  defaultValue={selectedLead?.property_value || ''}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  margin="dense"
                  name="condition"
                  label="Property Condition"
                  fullWidth
                  variant="outlined"
                  defaultValue={selectedLead?.condition || ''}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  margin="dense"
                  name="notes"
                  label="Notes"
                  fullWidth
                  multiline
                  rows={3}
                  variant="outlined"
                  defaultValue={selectedLead?.notes || ''}
                />
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
            <Button type="submit" variant="contained">
              {selectedLead ? 'Update' : 'Add'}
            </Button>
          </DialogActions>
        </form>
      </Dialog>

      {/* Import Dialog */}
      <Dialog open={openImportDialog} onClose={() => setOpenImportDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Import Leads</DialogTitle>
        <DialogContent>
          <FormControl fullWidth margin="dense" variant="outlined">
            <InputLabel>Select Campaign</InputLabel>
            <Select
              id="import-campaign-select"
              label="Select Campaign"
              required
            >
              {campaigns?.map((campaign) => (
                <MenuItem key={campaign.id} value={campaign.id}>
                  {campaign.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          
          <Box
            {...getRootProps()}
            sx={{
              border: '2px dashed #ccc',
              borderRadius: 2,
              p: 3,
              mt: 2,
              textAlign: 'center',
              cursor: 'pointer',
              backgroundColor: isDragActive ? '#f5f5f5' : 'transparent',
            }}
          >
            <input {...getInputProps()} />
            <UploadIcon sx={{ fontSize: 48, color: '#ccc', mb: 1 }} />
            <Typography variant="body1">
              {isDragActive
                ? 'Drop the file here...'
                : 'Drag & drop a CSV or Excel file here, or click to select'}
            </Typography>
            <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
              Supported formats: .csv, .xlsx
            </Typography>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenImportDialog(false)}>Cancel</Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteConfirmOpen} onClose={() => setDeleteConfirmOpen(false)}>
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete {leadToDelete?.first_name} {leadToDelete?.last_name}? 
            This will also delete all associated conversations and messages. This action cannot be undone.
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

export default Leads;
